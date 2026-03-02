"""Tests for session and weekly report generators."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from northstar.integrations.llm import NullLLMClient
from northstar.reporting.debt_report import SessionReportGenerator, WeeklyReportGenerator


class TestSessionReportGenerator:
    """Test SessionReportGenerator."""

    async def test_generate_returns_dict_with_keys(self) -> None:
        """generate returns a dict with 'markdown' and 'path' keys."""
        gen = SessionReportGenerator()
        result = await gen.generate(session_id="test-session-001")
        assert isinstance(result, dict)
        assert "markdown" in result
        assert "path" in result

    async def test_markdown_is_well_formed(self) -> None:
        """Markdown output contains expected sections."""
        gen = SessionReportGenerator()
        result = await gen.generate(session_id="test-session-002")
        md = result["markdown"]
        assert "# Session Report" in md
        assert "Session ID:" in md
        assert "Duration:" in md
        assert "Tasks Started" in md
        assert "Tasks Completed" in md
        assert "Decisions Made" in md
        assert "Drift Alerts" in md

    async def test_path_contains_session_id(self) -> None:
        """Output path contains the session ID prefix."""
        gen = SessionReportGenerator()
        result = await gen.generate(session_id="abc12345-6789-0000-0000-000000000000")
        assert "abc12345" in result["path"]

    async def test_path_is_markdown_file(self) -> None:
        """Output path ends with .md."""
        gen = SessionReportGenerator()
        result = await gen.generate(session_id="test-session")
        assert result["path"].endswith(".md")

    async def test_with_null_llm_client(self) -> None:
        """Report generation works with NullLLMClient."""
        llm = NullLLMClient(default_response="Focus on high-leverage tasks.")
        gen = SessionReportGenerator(llm_client=llm)
        result = await gen.generate(session_id="test-session")
        assert "Focus on high-leverage tasks" in result["markdown"]

    async def test_without_session_id(self) -> None:
        """Report generation works without a session_id."""
        gen = SessionReportGenerator()
        result = await gen.generate()
        assert "# Session Report" in result["markdown"]

    async def test_contains_pds_section(self) -> None:
        """Report contains PDS change information."""
        gen = SessionReportGenerator()
        result = await gen.generate(session_id="test")
        md = result["markdown"]
        assert "PDS" in md


class TestWeeklyReportGenerator:
    """Test WeeklyReportGenerator."""

    async def test_generate_returns_dict_with_keys(self) -> None:
        """generate returns a dict with 'markdown' and 'path' keys."""
        gen = WeeklyReportGenerator()
        result = await gen.generate()
        assert isinstance(result, dict)
        assert "markdown" in result
        assert "path" in result

    async def test_markdown_is_well_formed(self) -> None:
        """Markdown output contains expected sections."""
        gen = WeeklyReportGenerator()
        result = await gen.generate()
        md = result["markdown"]
        assert "# Weekly Report" in md
        assert "Period:" in md
        assert "Priority Debt Score Trend" in md
        assert "Top Accomplishments" in md
        assert "Debt Contributors" in md
        assert "Recommendations" in md

    async def test_custom_date_range(self) -> None:
        """Custom date range is reflected in the report."""
        gen = WeeklyReportGenerator()
        start = datetime(2025, 6, 1)
        end = datetime(2025, 6, 7)
        result = await gen.generate(start_date=start, end_date=end)
        md = result["markdown"]
        assert "2025-06-01" in md
        assert "2025-06-07" in md

    async def test_path_contains_date(self) -> None:
        """Output path contains the start date."""
        gen = WeeklyReportGenerator()
        start = datetime(2025, 3, 15)
        end = datetime(2025, 3, 22)
        result = await gen.generate(start_date=start, end_date=end)
        assert "2025-03-15" in result["path"]

    async def test_path_is_markdown_file(self) -> None:
        """Output path ends with .md."""
        gen = WeeklyReportGenerator()
        result = await gen.generate()
        assert result["path"].endswith(".md")

    async def test_with_null_llm_client(self) -> None:
        """Report generation works with NullLLMClient."""
        llm = NullLLMClient(default_response="Reduce context switching.")
        gen = WeeklyReportGenerator(llm_client=llm)
        result = await gen.generate()
        assert "Reduce context switching" in result["markdown"]

    async def test_default_date_range(self) -> None:
        """Default date range is 7 days ending today."""
        gen = WeeklyReportGenerator()
        result = await gen.generate()
        md = result["markdown"]
        # Should contain today's date in the period line
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in md

    async def test_contains_northstar_footer(self) -> None:
        """Report contains the NorthStar footer."""
        gen = WeeklyReportGenerator()
        result = await gen.generate()
        assert "NorthStar Priority Debt Engine" in result["markdown"]
