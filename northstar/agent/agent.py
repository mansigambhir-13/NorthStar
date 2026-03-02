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
from northstar.exceptions import NorthStarError

logger = logging.getLogger(__name__)


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
    ) -> None:
        self.project_root = Path(project_root or ".").resolve()
        self.northstar_dir = self.project_root / ".northstar"
        self.model_id = model_id
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

        # NorthStar LLM client (for deterministic engine calls)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            from northstar.integrations.llm import LLMClient

            self._llm_client = LLMClient(
                model=self._config.llm.model,
                temperature=self._config.llm.temperature,
                max_tokens=self._config.llm.max_tokens,
                cache_enabled=self._config.llm.cache_enabled,
                cache_ttl=self._config.llm.cache_ttl_seconds,
            )
        else:
            from northstar.integrations.llm import NullLLMClient

            self._llm_client = NullLLMClient()

        # Inject dependencies into tool functions
        set_engine_state(
            config=self._config,
            state_manager=self._state_manager,
            llm_client=self._llm_client,
        )

        # Build Strands agent
        self._agent = self._build_agent()

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

    async def analyze(self) -> str:
        """Run a full agentic priority analysis.

        The agent decides which tools to call, synthesises findings, and
        returns a strategic assessment with recommendations.
        """
        self._ensure_ready()
        response = self._agent(FULL_ANALYSIS_PROMPT)
        return str(response)

    async def quick_check(self) -> str:
        """Quick priority check — PDS and top recommendation."""
        self._ensure_ready()
        response = self._agent(QUICK_CHECK_PROMPT)
        return str(response)

    async def drift_check(self) -> str:
        """Check for drift from high-leverage work."""
        self._ensure_ready()
        response = self._agent(DRIFT_CHECK_PROMPT)
        return str(response)

    async def chat(self, message: str) -> str:
        """Send an arbitrary message to the agent and get a response.

        Useful for follow-up questions like "why is task X ranked higher?"
        or "what should I work on next?".
        """
        self._ensure_ready()
        response = self._agent(message)
        return str(response)

    # ── Helpers ───────────────────────────────────────────────────────

    def _ensure_ready(self) -> None:
        if self._agent is None:
            raise NorthStarError(
                "Agent not initialised. Use 'async with NorthStarAgent() as agent:'."
            )
