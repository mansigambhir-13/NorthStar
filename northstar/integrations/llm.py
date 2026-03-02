"""LLM client with retry, caching, and offline fallback."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from northstar.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """Async Claude API client with exponential backoff retry and hash-based caching."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        max_retries: int = 3,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._client: Any = None

    async def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic

                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise LLMError("ANTHROPIC_API_KEY environment variable is not set")
                self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                raise LLMError("anthropic package is not installed")
        return self._client

    def _cache_key(self, prompt: str, system: str = "") -> str:
        content = f"{self.model}:{self.temperature}:{system}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cached(self, key: str) -> Any | None:
        if not self.cache_enabled or key not in self._cache:
            return None
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.cache_ttl:
            del self._cache[key]
            return None
        return value

    def _set_cached(self, key: str, value: Any) -> None:
        if self.cache_enabled:
            self._cache[key] = (time.time(), value)

    async def query(self, prompt: str, system: str = "", parse_json: bool = False) -> Any:
        """Send a prompt to Claude and return the response text (or parsed JSON)."""
        cache_key = self._cache_key(prompt, system)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                messages = [{"role": "user", "content": prompt}]
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": messages,
                }
                if system:
                    kwargs["system"] = system

                response = await client.messages.create(**kwargs)
                text = response.content[0].text

                if parse_json:
                    text = text.strip()
                    if text.startswith("```"):
                        lines = text.split("\n")
                        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
                    result = json.loads(text)
                else:
                    result = text

                self._set_cached(cache_key, result)
                return result

            except json.JSONDecodeError as e:
                raise LLMError(f"Failed to parse LLM response as JSON: {e}") from e
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"LLM request failed (attempt {attempt + 1}), retrying in {wait}s: {e}")
                    import asyncio

                    await asyncio.sleep(wait)

        raise LLMError(f"LLM request failed after {self.max_retries} attempts: {last_error}")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


class NullLLMClient:
    """Offline/testing LLM client that returns sensible defaults."""

    def __init__(self, default_response: str = "", default_json: Any = None) -> None:
        self.default_response = default_response
        self.default_json = default_json or {}
        self.calls: list[dict[str, Any]] = []

    async def query(self, prompt: str, system: str = "", parse_json: bool = False) -> Any:
        self.calls.append({"prompt": prompt, "system": system, "parse_json": parse_json})
        if parse_json:
            return self.default_json
        return self.default_response

    async def close(self) -> None:
        pass
