"""NorthStarAgent — Strands-powered agentic priority strategist.

Wraps the deterministic NorthStar engines with an LLM reasoning loop that
can dynamically decide which tools to call, in which order, and how to
synthesize the results into actionable recommendations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from northstar.agent.prompts import (
    DRIFT_CHECK_PROMPT,
    FULL_ANALYSIS_PROMPT,
    NORTHSTAR_AGENT_SYSTEM_PROMPT,
    QUICK_CHECK_PROMPT,
)
from northstar.agent.tools import ALL_TOOLS, set_engine_state
from northstar.config import NorthStarConfig
from northstar.exceptions import AgentError, NorthStarError

logger = logging.getLogger(__name__)

# Validate strands availability at import time with helpful message
_STRANDS_AVAILABLE = False
_STRANDS_IMPORT_ERROR: str | None = None
try:
    from strands import Agent as _StrandsAgent  # noqa: F401
    from strands.models.anthropic import AnthropicModel as _AnthropicModel  # noqa: F401

    _STRANDS_AVAILABLE = True
except ImportError as _exc:
    _STRANDS_IMPORT_ERROR = (
        f"Strands Agents SDK not installed: {_exc}. "
        "Install with: pip install 'strands-agents[anthropic]>=0.1.0'"
    )


class NorthStarAgent:
    """Agentic wrapper around NorthStar's priority engines.

    Uses AWS Strands Agents SDK to create a model-driven agent that reasons
    about task prioritisation using NorthStar's deterministic tools.

    Usage::

        agent = NorthStarAgent(project_root=".")
        async with agent:
            result = await agent.analyze()
            print(result)
    """

    def __init__(
        self,
        project_root: str | Path | None = None,
        model_id: str | None = None,
        fallback: bool = False,
    ) -> None:
        self.project_root = Path(project_root or ".").resolve()
        self.northstar_dir = self.project_root / ".northstar"
        self.model_id = model_id
        self.fallback = fallback
        self._config: NorthStarConfig | None = None
        self._state_manager: Any = None
        self._llm_client: Any = None
        self._agent: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def __aenter__(self) -> "NorthStarAgent":
        await self._setup()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._teardown()

    async def _setup(self) -> None:
        """Initialise config, state manager, LLM client, and Strands agent."""
        # Config
        config_path = self.northstar_dir / "config.yaml"
        self._config = NorthStarConfig.load(config_path)
        self._config.project_root = str(self.project_root)
        if not self._config.project_name:
            self._config.project_name = self.project_root.name

        # State manager
        from northstar.state.manager import StateManager

        db_path = self.northstar_dir / "state.db"
        context_path = self.northstar_dir / "context.json"
        self._state_manager = StateManager(db_path=db_path, context_path=context_path)
        await self._state_manager.__aenter__()

        # Determine which LLM backend to use
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        groq_key = os.environ.get("GROQ_API_KEY")
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        self._use_compatible_api = bool(groq_key or openrouter_key) and not anthropic_key

        # NorthStar LLM client (for deterministic engine calls + agent chat)
        if not self.fallback and anthropic_key:
            from northstar.integrations.llm import LLMClient

            self._llm_client = LLMClient(
                model=self._config.llm.model,
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens,
                cache_enabled=self._config.llm.cache_enabled,
                cache_ttl=self._config.llm.cache_ttl_seconds,
            )
        elif not self.fallback and groq_key:
            from northstar.integrations.llm import OpenAICompatibleClient

            self._llm_client = OpenAICompatibleClient(
                endpoint="https://api.groq.com/openai/v1/chat/completions",
                api_key=groq_key,
                model="llama-3.3-70b-versatile",
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens,
                cache_enabled=self._config.llm.cache_enabled,
                cache_ttl=self._config.llm.cache_ttl_seconds,
            )
            logger.info("Using Groq LLM backend")
        elif not self.fallback and openrouter_key:
            from northstar.integrations.llm import OpenAICompatibleClient

            self._llm_client = OpenAICompatibleClient(
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                api_key=openrouter_key,
                model="anthropic/claude-sonnet-4",
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens,
                cache_enabled=self._config.llm.cache_enabled,
                cache_ttl=self._config.llm.cache_ttl_seconds,
            )
            logger.info("Using OpenRouter LLM backend")
        else:
            from northstar.integrations.llm import NullLLMClient

            self._llm_client = NullLLMClient()
            if self.fallback:
                logger.info("Agent running in fallback mode (NullLLMClient)")

        # Inject dependencies into tool functions
        set_engine_state(
            config=self._config,
            state_manager=self._state_manager,
            llm_client=self._llm_client,
        )

        # Build agent:
        # 1. If Groq/OpenRouter key → use direct LLM chat (no Strands needed)
        # 2. If Anthropic key + Strands → use Strands agent
        # 3. Otherwise → fallback
        if self.fallback:
            logger.info("Skipping agent build (fallback mode)")
            self._agent = self._fallback_agent
        elif self._use_compatible_api:
            logger.info("Using OpenAI-compatible agent (direct LLM)")
            self._agent = self._openrouter_agent
        elif not _STRANDS_AVAILABLE:
            logger.warning("Strands SDK unavailable, using fallback: %s", _STRANDS_IMPORT_ERROR)
            self._agent = self._fallback_agent
        else:
            try:
                self._agent = self._build_agent()
            except Exception as e:
                logger.error("Failed to build Strands agent, falling back: %s", e)
                self._agent = self._fallback_agent

    def _build_agent(self) -> Any:
        """Create the Strands Agent instance."""
        from strands import Agent
        from strands.models.anthropic import AnthropicModel

        model_id = self.model_id or self._config.llm.model or "claude-sonnet-4-20250514"

        model = AnthropicModel(
            client_args={"api_key": os.environ.get("ANTHROPIC_API_KEY", "")},
            model_id=model_id,
            max_tokens=4096,
        )

        return Agent(
            model=model,
            system_prompt=NORTHSTAR_AGENT_SYSTEM_PROMPT,
            tools=ALL_TOOLS,
        )

    async def _openrouter_agent(self, prompt: str) -> str:
        """Agent backed by OpenRouter — direct LLM chat with system prompt."""
        return await self._llm_client.query(
            prompt=prompt,
            system=NORTHSTAR_AGENT_SYSTEM_PROMPT,
        )

    @staticmethod
    async def _fallback_agent(prompt: str) -> str:
        """Fallback when no LLM backend is available."""
        return (
            "[NorthStar fallback mode] Agent is running without an LLM backend. "
            "Deterministic engines are available via CLI commands "
            "(northstar analyze, northstar check, etc.). "
            f"Your query: {prompt[:200]}"
        )

    async def _teardown(self) -> None:
        """Clean up resources."""
        if self._state_manager is not None:
            await self._state_manager.__aexit__(None, None, None)
            self._state_manager = None
        if self._llm_client is not None:
            await self._llm_client.close()
            self._llm_client = None
        self._agent = None

    # ── Public methods ────────────────────────────────────────────────

    async def _call_agent(self, prompt: str) -> str:
        """Call the agent (handles both sync Strands and async OpenRouter/fallback)."""
        import asyncio
        import inspect

        result = self._agent(prompt)
        if inspect.isawaitable(result):
            return str(await result)
        return str(result)

    async def analyze(self) -> str:
        """Run a full agentic priority analysis."""
        self._ensure_ready()
        try:
            return await self._call_agent(FULL_ANALYSIS_PROMPT)
        except Exception as e:
            logger.error("Agent analyze failed: %s", e)
            raise AgentError(f"Analysis failed: {e}") from e

    async def quick_check(self) -> str:
        """Quick priority check — PDS and top recommendation."""
        self._ensure_ready()
        try:
            return await self._call_agent(QUICK_CHECK_PROMPT)
        except Exception as e:
            logger.error("Agent quick_check failed: %s", e)
            raise AgentError(f"Quick check failed: {e}") from e

    async def drift_check(self) -> str:
        """Check for drift from high-leverage work."""
        self._ensure_ready()
        try:
            return await self._call_agent(DRIFT_CHECK_PROMPT)
        except Exception as e:
            logger.error("Agent drift_check failed: %s", e)
            raise AgentError(f"Drift check failed: {e}") from e

    async def chat(self, message: str) -> str:
        """Send an arbitrary message to the agent and get a response."""
        self._ensure_ready()
        try:
            return await self._call_agent(message)
        except Exception as e:
            logger.error("Agent chat failed: %s", e)
            raise AgentError(f"Chat failed: {e}") from e

    # ── Helpers ───────────────────────────────────────────────────────

    def _ensure_ready(self) -> None:
        if self._agent is None:
            raise NorthStarError(
                "Agent not initialised. Use 'async with NorthStarAgent() as agent:'."
            )
