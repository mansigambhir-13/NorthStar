"""Tests for the GapAnalyzer."""

from __future__ import annotations

from datetime import datetime

import pytest

from northstar.analysis.gap_analyzer import GapAnalyzer
from northstar.analysis.models import (
    Goal,
    GoalSet,
    GoalStatus,
    Task,
    TaskStatus,
    UrgencyLevel,
)
from northstar.integrations.llm import NullLLMClient


# ── Helpers ──────────────────────────────────────────────────────────


def _goal(id: str = "goal-1", title: str = "Launch MVP") -> Goal:
    return Goal(
        id=id,
        title=title,
        priority=1,
        status=GoalStatus.ACTIVE,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


def _task(
    *,
    id: str = "t1",
    goal_id: str | None = "goal-1",
    status: TaskStatus = TaskStatus.PENDING,
    effort: float = 4.0,
) -> Task:
    return Task(
        id=id,
        title=f"Task {id}",
        goal_id=goal_id,
        goal_alignment=0.8,
        impact=50,
        urgency=UrgencyLevel.NORMAL,
        effort_hours=effort,
        status=status,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coverage_calculation() -> None:
    """Partially-done tasks yield correct coverage ratio."""
    analyzer = GapAnalyzer(llm_client=None)
    goals = GoalSet(goals=[_goal()])

    tasks = [
        _task(id="done", status=TaskStatus.COMPLETED, effort=3.0),
        _task(id="wip", status=TaskStatus.IN_PROGRESS, effort=2.0),
        _task(id="pending", status=TaskStatus.PENDING, effort=5.0),
    ]

    reports = await analyzer.analyze(tasks, goals)

    # Find the goal-1 report (not the orphan report)
    goal_report = next(r for r in reports if r.goal_id == "goal-1")

    # coverage = (3+2) / (3+2+5) = 5/10 = 0.5
    assert goal_report.coverage == 0.5
    # 0.5 is NOT < 0.5, so it falls through to < 0.75 -> medium
    assert goal_report.severity == "medium"


@pytest.mark.asyncio
async def test_orphan_detection() -> None:
    """Tasks with no goal_id are detected as orphans."""
    analyzer = GapAnalyzer(llm_client=None)
    goals = GoalSet(goals=[_goal()])

    tasks = [
        _task(id="aligned", goal_id="goal-1"),
        _task(id="orphan-1", goal_id=None),
        _task(id="orphan-2", goal_id="nonexistent-goal"),
    ]

    reports = await analyzer.analyze(tasks, goals)

    orphan_report = next(r for r in reports if r.goal_id == "_orphan")
    assert "orphan-1" in orphan_report.orphan_tasks
    assert "orphan-2" in orphan_report.orphan_tasks
    assert len(orphan_report.orphan_tasks) == 2


@pytest.mark.asyncio
async def test_severity_classification() -> None:
    """Coverage thresholds map to correct severity levels."""
    analyzer = GapAnalyzer(llm_client=None)

    # coverage=0 -> critical (no completed tasks, all pending)
    goals_0 = GoalSet(goals=[_goal(id="g0")])
    tasks_0 = [_task(id="t0", goal_id="g0", status=TaskStatus.PENDING, effort=10.0)]
    reports_0 = await analyzer.analyze(tasks_0, goals_0)
    r0 = next(r for r in reports_0 if r.goal_id == "g0")
    assert r0.coverage == 0.0
    assert r0.severity == "critical"

    # coverage=0.3 -> high (3 done, 7 pending)
    goals_h = GoalSet(goals=[_goal(id="gh")])
    tasks_h = [
        _task(id="th-done", goal_id="gh", status=TaskStatus.COMPLETED, effort=3.0),
        _task(id="th-pend", goal_id="gh", status=TaskStatus.PENDING, effort=7.0),
    ]
    reports_h = await analyzer.analyze(tasks_h, goals_h)
    rh = next(r for r in reports_h if r.goal_id == "gh")
    assert rh.coverage == 0.3
    assert rh.severity == "high"

    # coverage=0.6 -> medium
    goals_m = GoalSet(goals=[_goal(id="gm")])
    tasks_m = [
        _task(id="tm-done", goal_id="gm", status=TaskStatus.COMPLETED, effort=6.0),
        _task(id="tm-pend", goal_id="gm", status=TaskStatus.PENDING, effort=4.0),
    ]
    reports_m = await analyzer.analyze(tasks_m, goals_m)
    rm = next(r for r in reports_m if r.goal_id == "gm")
    assert rm.coverage == 0.6
    assert rm.severity == "medium"

    # coverage=0.9 -> low
    goals_l = GoalSet(goals=[_goal(id="gl")])
    tasks_l = [
        _task(id="tl-done", goal_id="gl", status=TaskStatus.COMPLETED, effort=9.0),
        _task(id="tl-pend", goal_id="gl", status=TaskStatus.PENDING, effort=1.0),
    ]
    reports_l = await analyzer.analyze(tasks_l, goals_l)
    rl = next(r for r in reports_l if r.goal_id == "gl")
    assert rl.coverage == 0.9
    assert rl.severity == "low"


@pytest.mark.asyncio
async def test_no_tasks_for_goal() -> None:
    """A goal with zero associated tasks has coverage=0, severity=critical."""
    analyzer = GapAnalyzer(llm_client=NullLLMClient())
    goals = GoalSet(goals=[_goal(id="empty-goal", title="Lonely Goal")])

    reports = await analyzer.analyze([], goals)

    goal_report = next(r for r in reports if r.goal_id == "empty-goal")
    assert goal_report.coverage == 0.0
    assert goal_report.severity == "critical"
    assert goal_report.needed_effort == 10.0  # default
