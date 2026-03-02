"""Tests for Cursor IDE integration."""

from pathlib import Path

from northstar.analysis.models import (
    Goal,
    GoalSet,
    PriorityDebtScore,
    PriorityStack,
    Task,
)
from northstar.integrations.cursor import CursorIntegration, START_MARKER, END_MARKER


class TestCursorIntegration:
    def test_generates_cursorrules(self, tmp_path: Path) -> None:
        cursor = CursorIntegration(project_root=tmp_path)
        pds = PriorityDebtScore(score=1500, severity="yellow")
        stack = PriorityStack(
            tasks=[
                Task(id="t1", title="Build auth", leverage_score=9000),
                Task(id="t2", title="Add payments", leverage_score=7000),
            ]
        )
        goals = GoalSet(goals=[Goal(id="g1", title="Launch MVP", priority=1)])

        cursor.update_cursorrules(pds=pds, stack=stack, goals=goals)

        rules_path = tmp_path / ".cursorrules"
        assert rules_path.exists()
        content = rules_path.read_text()
        assert START_MARKER in content
        assert END_MARKER in content
        assert "1500" in content
        assert "Launch MVP" in content
        assert "Build auth" in content
        assert "Add payments" in content

    def test_append_does_not_overwrite_existing(self, tmp_path: Path) -> None:
        rules_path = tmp_path / ".cursorrules"
        rules_path.write_text("# Existing rules\nAlways use TypeScript.\n")

        cursor = CursorIntegration(project_root=tmp_path)
        pds = PriorityDebtScore(score=100, severity="green")
        cursor.update_cursorrules(pds=pds)

        content = rules_path.read_text()
        assert "Existing rules" in content
        assert "Always use TypeScript" in content
        assert START_MARKER in content

    def test_update_replaces_existing_section(self, tmp_path: Path) -> None:
        cursor = CursorIntegration(project_root=tmp_path)

        pds1 = PriorityDebtScore(score=100, severity="green")
        cursor.update_cursorrules(pds=pds1)

        pds2 = PriorityDebtScore(score=5000, severity="red")
        cursor.update_cursorrules(pds=pds2)

        content = (tmp_path / ".cursorrules").read_text()
        assert content.count(START_MARKER) == 1
        assert "5000" in content
        # Old score should not be present as main score
        assert "100 " not in content.split(START_MARKER)[1].split("5000")[0]

    def test_read_current_context_no_file(self, tmp_path: Path) -> None:
        cursor = CursorIntegration(project_root=tmp_path)
        result = cursor.read_current_context()
        assert result["exists"] is False

    def test_read_current_context_with_section(self, tmp_path: Path) -> None:
        cursor = CursorIntegration(project_root=tmp_path)
        pds = PriorityDebtScore(score=2500, severity="orange")
        cursor.update_cursorrules(pds=pds)

        result = cursor.read_current_context()
        assert result["exists"] is True
        assert result["northstar_section"] is True
        assert "2500" in result["content"]
