"""Tests for agent system prompts."""

from northstar.agent.prompts import (
    DRIFT_CHECK_PROMPT,
    FULL_ANALYSIS_PROMPT,
    NORTHSTAR_AGENT_SYSTEM_PROMPT,
    QUICK_CHECK_PROMPT,
)


class TestPrompts:
    def test_system_prompt_not_empty(self) -> None:
        assert len(NORTHSTAR_AGENT_SYSTEM_PROMPT) > 100

    def test_system_prompt_mentions_priority_debt(self) -> None:
        assert "Priority Debt" in NORTHSTAR_AGENT_SYSTEM_PROMPT

    def test_system_prompt_mentions_severity_bands(self) -> None:
        assert "Green" in NORTHSTAR_AGENT_SYSTEM_PROMPT
        assert "Red" in NORTHSTAR_AGENT_SYSTEM_PROMPT

    def test_full_analysis_prompt(self) -> None:
        assert "analysis" in FULL_ANALYSIS_PROMPT.lower()

    def test_quick_check_prompt(self) -> None:
        assert "quick" in QUICK_CHECK_PROMPT.lower()

    def test_drift_check_prompt(self) -> None:
        assert "drift" in DRIFT_CHECK_PROMPT.lower()
