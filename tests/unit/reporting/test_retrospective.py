"""Tests for the RetrospectiveGenerator."""

from __future__ import annotations

from datetime import datetime

import pytest

from northstar.integrations.llm import NullLLMClient
from northstar.reporting.retrospective import RetrospectiveGenerator


class TestRetrospectiveGenerator:
    """Test RetrospectiveGenerator."""

    async def test_generate_returns_dict_with_keys(self) -> None:
        """generate returns a dict with 'markdown' and 'path' keys."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        assert isinstance(result, dict)
        assert "markdown" in result
        assert "path" in result

    async def test_markdown_is_well_formed(self) -> None:
        """Markdown output contains expected sections."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        md = result["markdown"]
        assert "# Retrospective" in md
        assert "Predicted vs Actual" in md
        assert "Leverage Accuracy" in md
        assert "What Went Well" in md
        assert "What Could Improve" in md
        assert "Key Insights" in md

    async def test_custom_date_range(self) -> None:
        """Custom date range is reflected in the report."""
        gen = RetrospectiveGenerator()
        start = datetime(2025, 5, 1)
        end = datetime(2025, 5, 31)
        result = await gen.generate(start_date=start, end_date=end)
        md = result["markdown"]
        assert "2025-05-01" in md
        assert "2025-05-31" in md

    async def test_path_contains_dates(self) -> None:
        """Output path contains start and end dates."""
        gen = RetrospectiveGenerator()
        start = datetime(2025, 4, 1)
        end = datetime(2025, 4, 7)
        result = await gen.generate(start_date=start, end_date=end)
        assert "2025-04-01" in result["path"]
        assert "2025-04-07" in result["path"]

    async def test_path_is_markdown_file(self) -> None:
        """Output path ends with .md."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        assert result["path"].endswith(".md")

    async def test_with_null_llm_client(self) -> None:
        """Report generation works with NullLLMClient."""
        llm = NullLLMClient(default_response="Improve task estimation accuracy.")
        gen = RetrospectiveGenerator(llm_client=llm)
        result = await gen.generate()
        assert "Improve task estimation accuracy" in result["markdown"]

    async def test_without_llm_client(self) -> None:
        """Report generation works without an LLM client."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        assert "LLM analysis not available" in result["markdown"]

    async def test_accuracy_section_present(self) -> None:
        """Report contains accuracy ratio section."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        md = result["markdown"]
        assert "Accuracy ratio:" in md

    async def test_default_date_range(self) -> None:
        """Default date range ends with today's date."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert today in result["markdown"]

    async def test_contains_northstar_footer(self) -> None:
        """Report contains the NorthStar footer."""
        gen = RetrospectiveGenerator()
        result = await gen.generate()
        assert "NorthStar Priority Debt Engine" in result["markdown"]
