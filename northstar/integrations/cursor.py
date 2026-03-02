"""Cursor IDE integration — generates/updates .cursorrules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from northstar.analysis.models import GoalSet, PriorityDebtScore, PriorityStack

START_MARKER = "# --- NorthStar Priority Context (auto-generated) ---"
END_MARKER = "# --- End NorthStar Priority Context ---"


class CursorIntegration:
    """Manages .cursorrules file with NorthStar priority context."""

    def __init__(self, project_root: str | Path = ".") -> None:
        self.project_root = Path(project_root)
        self.cursorrules_path = self.project_root / ".cursorrules"

    def update_cursorrules(
        self,
        pds: PriorityDebtScore | None = None,
        stack: PriorityStack | None = None,
        goals: GoalSet | None = None,
    ) -> None:
        """Update .cursorrules with NorthStar section between markers."""
        northstar_section = self._build_section(pds, stack, goals)
        if self.cursorrules_path.exists():
            content = self.cursorrules_path.read_text()
            if START_MARKER in content and END_MARKER in content:
                before = content[: content.index(START_MARKER)]
                after = content[content.index(END_MARKER) + len(END_MARKER) :]
                new_content = before + northstar_section + after
            else:
                new_content = content.rstrip() + "\n\n" + northstar_section + "\n"
        else:
            new_content = northstar_section + "\n"

        self.cursorrules_path.write_text(new_content)

    def _build_section(
        self,
        pds: PriorityDebtScore | None,
        stack: PriorityStack | None,
        goals: GoalSet | None,
    ) -> str:
        lines = [START_MARKER, ""]

        if pds:
            severity_emoji = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}.get(
                pds.severity, "⚪"
            )
            lines.append(f"Priority Debt Score: {pds.score:.0f} {severity_emoji} ({pds.severity.upper()})")
            lines.append("")

        if goals and goals.primary:
            lines.append(f"Primary Goal: {goals.primary.title}")
            if goals.primary.description:
                lines.append(f"  {goals.primary.description}")
            lines.append("")

        if stack and stack.tasks:
            lines.append("Top 5 Priority Tasks:")
            for i, task in enumerate(stack.tasks[:5], 1):
                lines.append(f"  {i}. [{task.leverage_score:.0f}] {task.title}")
            lines.append("")

        lines.append("When working on this project, prioritize tasks in the order listed above.")
        lines.append("If you find yourself working on something not in this list, consider")
        lines.append("whether it truly serves the primary goal.")
        lines.append("")
        lines.append(END_MARKER)
        return "\n".join(lines)

    def read_current_context(self) -> dict[str, Any]:
        """Read current NorthStar section from .cursorrules."""
        if not self.cursorrules_path.exists():
            return {"exists": False}

        content = self.cursorrules_path.read_text()
        if START_MARKER not in content:
            return {"exists": True, "northstar_section": False}

        section = content[
            content.index(START_MARKER) : content.index(END_MARKER) + len(END_MARKER)
        ]
        return {"exists": True, "northstar_section": True, "content": section}
