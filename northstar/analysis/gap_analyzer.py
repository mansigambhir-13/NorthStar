"""Goal-to-work gap analyzer.

Identifies coverage gaps between strategic goals and allocated tasks,
detects orphan tasks, and classifies severity of under-investment.
"""

from __future__ import annotations

import logging
from typing import Any

from northstar.analysis.models import (
    GapReport,
    Goal,
    GoalSet,
    GoalStatus,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Default estimated effort when no tasks exist for a goal
_DEFAULT_NEEDED_EFFORT = 10.0


class GapAnalyzer:
    """Analyze coverage gaps between goals and task effort."""

    def __init__(self, llm_client: Any = None) -> None:
        self.llm_client = llm_client

    # ── Severity classification ──────────────────────────────────────

    @staticmethod
    def _severity_for_coverage(coverage: float) -> str:
        if coverage < 0.25:
            return "critical"
        if coverage < 0.5:
            return "high"
        if coverage < 0.75:
            return "medium"
        return "low"

    # ── Per-goal analysis ────────────────────────────────────────────

    def _analyze_goal(self, goal: Goal, tasks: list[Task]) -> GapReport:
        """Analyze a single goal against its associated tasks."""
        goal_tasks = [t for t in tasks if t.goal_id == goal.id]

        if not goal_tasks:
            return GapReport(
                goal_id=goal.id,
                goal_title=goal.title,
                coverage=0.0,
                allocated_effort=0.0,
                needed_effort=_DEFAULT_NEEDED_EFFORT,
                severity="critical",
                orphan_tasks=[],
                recommendations=[
                    f"No tasks allocated to goal '{goal.title}'. "
                    f"Create tasks to make progress.",
                ],
            )

        total_effort = sum(t.effort_hours for t in goal_tasks)
        completed_effort = sum(
            t.effort_hours
            for t in goal_tasks
            if t.status in (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS)
        )

        coverage = completed_effort / total_effort if total_effort > 0 else 0.0
        coverage = max(0.0, min(1.0, coverage))

        severity = self._severity_for_coverage(coverage)

        recommendations: list[str] = []
        if severity == "critical":
            recommendations.append(
                f"Goal '{goal.title}' has critical coverage gap ({coverage:.0%}). "
                f"Prioritize immediately."
            )
        elif severity == "high":
            recommendations.append(
                f"Goal '{goal.title}' needs more effort ({coverage:.0%} covered)."
            )

        return GapReport(
            goal_id=goal.id,
            goal_title=goal.title,
            coverage=round(coverage, 4),
            allocated_effort=round(total_effort, 2),
            needed_effort=round(total_effort, 2),
            severity=severity,
            orphan_tasks=[],  # Orphans are collected separately
            recommendations=recommendations,
        )

    # ── Orphan detection ─────────────────────────────────────────────

    @staticmethod
    def _find_orphan_tasks(tasks: list[Task], goals: GoalSet) -> list[str]:
        """Find tasks with no goal_id or a goal_id not matching any active goal."""
        active_goal_ids = {g.id for g in goals.active_goals}
        orphans: list[str] = []
        for task in tasks:
            if task.goal_id is None or task.goal_id not in active_goal_ids:
                orphans.append(task.id)
        return orphans

    # ── Main entry point ─────────────────────────────────────────────

    async def analyze(
        self, tasks: list[Task], goals: GoalSet
    ) -> list[GapReport]:
        """Analyze coverage gaps for all active goals.

        Returns one GapReport per active goal, plus a synthetic report
        for orphan tasks (if any).
        """
        reports: list[GapReport] = []

        for goal in goals.active_goals:
            report = self._analyze_goal(goal, tasks)
            reports.append(report)

        # Detect orphan tasks
        orphans = self._find_orphan_tasks(tasks, goals)
        if orphans:
            # Attach orphans to a synthetic "Unaligned" report
            orphan_report = GapReport(
                goal_id="_orphan",
                goal_title="Unaligned Tasks",
                coverage=0.0,
                allocated_effort=sum(
                    t.effort_hours for t in tasks if t.id in orphans
                ),
                needed_effort=0.0,
                severity="high",
                orphan_tasks=orphans,
                recommendations=[
                    f"{len(orphans)} task(s) have no matching active goal. "
                    f"Consider aligning them or removing them."
                ],
            )
            reports.append(orphan_report)

        return reports
