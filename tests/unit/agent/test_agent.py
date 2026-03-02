"""Tests for the NorthStarAgent class.

These tests verify the agent lifecycle, setup, and teardown — without
actually invoking the Strands model (which would require an API key).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from northstar.agent.agent import NorthStarAgent
from northstar.agent.prompts import NORTHSTAR_AGENT_SYSTEM_PROMPT
from northstar.agent.tools import ALL_TOOLS
from northstar.config import NorthStarConfig
from northstar.exceptions import NorthStarError


class TestNorthStarAgentInit:
    def test_defaults(self) -> None:
        agent = NorthStarAgent()
        assert agent.project_root == Path(".").resolve()
        assert agent.model_id is None
        assert agent._agent is None

    def test_custom_root(self, tmp_path: Path) -> None:
        agent = NorthStarAgent(project_root=tmp_path)
        assert agent.project_root == tmp_path.resolve()

    def test_custom_model(self) -> None:
        agent = NorthStarAgent(model_id="claude-haiku-4-5-20251001")
        assert agent.model_id == "claude-haiku-4-5-20251001"


class TestNorthStarAgentLifecycle:
    async def test_setup_creates_state_manager(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        agent = NorthStarAgent(project_root=tmp_path)

        # Mock Strands to avoid needing API key
        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = MagicMock()
            await agent._setup()

            assert agent._state_manager is not None
            assert agent._llm_client is not None
            assert agent._config is not None
            assert agent._agent is not None

            await agent._teardown()

            assert agent._state_manager is None
            assert agent._agent is None

    async def test_context_manager(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = MagicMock()

            async with NorthStarAgent(project_root=tmp_path) as agent:
                assert agent._agent is not None

            # After exiting, resources should be cleaned up
            assert agent._agent is None

    async def test_ensure_ready_raises_when_not_setup(self) -> None:
        agent = NorthStarAgent()
        with pytest.raises(NorthStarError, match="not initialised"):
            agent._ensure_ready()


class TestNorthStarAgentMethods:
    async def test_analyze_calls_agent(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        mock_agent = MagicMock()
        mock_agent.return_value = "Analysis complete: PDS is 450 (green)"

        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = mock_agent

            async with NorthStarAgent(project_root=tmp_path) as agent:
                result = await agent.analyze()

            assert "Analysis complete" in result
            mock_agent.assert_called_once()

    async def test_quick_check_calls_agent(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        mock_agent = MagicMock()
        mock_agent.return_value = "PDS: 200 (green). Top: Implement auth."

        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = mock_agent

            async with NorthStarAgent(project_root=tmp_path) as agent:
                result = await agent.quick_check()

            assert "PDS" in result

    async def test_drift_check_calls_agent(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        mock_agent = MagicMock()
        mock_agent.return_value = "No drift detected."

        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = mock_agent

            async with NorthStarAgent(project_root=tmp_path) as agent:
                result = await agent.drift_check()

            assert "drift" in result.lower()

    async def test_chat_calls_agent_with_message(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        mock_agent = MagicMock()
        mock_agent.return_value = "Task X is ranked #1 because..."

        with patch("northstar.agent.agent.NorthStarAgent._build_agent") as mock_build:
            mock_build.return_value = mock_agent

            async with NorthStarAgent(project_root=tmp_path) as agent:
                result = await agent.chat("Why is task X ranked higher?")

            mock_agent.assert_called_once_with("Why is task X ranked higher?")
            assert "ranked" in result.lower()


class TestBuildAgent:
    def test_build_agent_uses_all_tools(self, tmp_path: Path) -> None:
        """Verify the agent is configured with all NorthStar tools."""
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()

        agent = NorthStarAgent(project_root=tmp_path)
        agent._config = NorthStarConfig(project_root=str(tmp_path))

        # We can't call _build_agent without an API key, but we can verify
        # that ALL_TOOLS has the expected count
        assert len(ALL_TOOLS) == 8
        tool_names = {fn.__name__ for fn in ALL_TOOLS}
        expected = {
            "get_goals",
            "get_tasks",
            "rank_tasks",
            "calculate_pds",
            "analyze_gaps",
            "check_drift",
            "update_task_status",
            "get_pds_history",
        }
        assert tool_names == expected
