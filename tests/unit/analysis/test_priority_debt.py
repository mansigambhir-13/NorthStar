"""Tests for the PriorityDebtCalculator."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from northstar.analysis.models import (
    Task,
    TaskStatus,
    UrgencyLevel,
)
from northstar.analysis.priority_debt import PriorityDebtCalculator
from northstar.integrations.llm import NullLLMClient


# ── Helpers ──────────────────────────────────────────────────────────

_NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)


def _task(
    *,
    id: str = "t1",
    status: TaskStatus = TaskStatus.PENDING,
    alignment: float = 0.8,
    leverage: float = 5000.0,
    created_days_ago: int = 10,
) -> Task:
    return Task(
        id=id,
        title=f"Task {id}",
        goal_id="goal-1",
        goal_alignment=alignment,
        leverage_score=leverage,
        impact=50,
        urgency=UrgencyLevel.NORMAL,
        effort_hours=2.0,
        status=status,
        created_at=_NOW - timedelta(days=created_days_ago),
        updated_at=_NOW - timedelta(days=created_days_ago),
    )


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_completed_is_green() -> None:
    """All tasks completed should result in very low (near-zero) score, severity=green."""
    calc = PriorityDebtCalculator(llm_client=None)
    tasks = [
        _task(id="a", status=TaskStatus.COMPLETED, alignment=0.9, leverage=8000.0),
        _task(id="b", status=TaskStatus.COMPLETED, alignment=0.7, leverage=6000.0),
    ]
    result = await calc.calculate(tasks, now=_NOW)

    # Score should be 0 (clamped from negative)
    assert result.score == 0.0
    assert result.severity == "green"


@pytest.mark.asyncio
async def test_all_undone_high_leverage() -> None:
    """All high-leverage pending tasks should produce a high score (red)."""
    calc = PriorityDebtCalculator(llm_client=None)
    tasks = [
        _task(id="a", status=TaskStatus.PENDING, alignment=0.95, leverage=9000.0, created_days_ago=30),
        _task(id="b", status=TaskStatus.PENDING, alignment=0.9, leverage=8500.0, created_days_ago=25),
        _task(id="c", status=TaskStatus.IN_PROGRESS, alignment=0.85, leverage=8000.0, created_days_ago=20),
    ]
    result = await calc.calculate(tasks, now=_NOW)

    assert result.severity == "red"
    assert result.score >= 5000


@pytest.mark.asyncio
async def test_time_decay() -> None:
    """Older undone tasks produce a higher score than newer identical ones."""
    calc = PriorityDebtCalculator(llm_client=None)

    old_tasks = [_task(id="old", created_days_ago=60, alignment=0.8, leverage=7000.0)]
    new_tasks = [_task(id="new", created_days_ago=1, alignment=0.8, leverage=7000.0)]

    old_result = await calc.calculate(old_tasks, now=_NOW)
    new_result = await calc.calculate(new_tasks, now=_NOW)

    assert old_result.score > new_result.score, (
        f"Old ({old_result.score}) should exceed new ({new_result.score})"
    )


@pytest.mark.asyncio
async def test_severity_boundaries() -> None:
    """Verify severity thresholds: <500=green, <2000=yellow, <5000=orange, >=5000=red."""
    from northstar.analysis.models import PriorityDebtScore

    assert PriorityDebtScore.severity_for_score(0) == "green"
    assert PriorityDebtScore.severity_for_score(499) == "green"
    assert PriorityDebtScore.severity_for_score(500) == "yellow"
    assert PriorityDebtScore.severity_for_score(1999) == "yellow"
    assert PriorityDebtScore.severity_for_score(2000) == "orange"
    assert PriorityDebtScore.severity_for_score(4999) == "orange"
    assert PriorityDebtScore.severity_for_score(5000) == "red"
    assert PriorityDebtScore.severity_for_score(10000) == "red"


@pytest.mark.asyncio
async def test_empty_tasks() -> None:
    """Empty task list returns score=0, severity=green."""
    calc = PriorityDebtCalculator(llm_client=None)
    result = await calc.calculate([], now=_NOW)

    assert result.score == 0.0
    assert result.severity == "green"
    assert result.top_contributors == []


@pytest.mark.asyncio
async def test_top_contributors() -> None:
    """Top 3 contributors should be returned, sorted by debt contribution."""
    calc = PriorityDebtCalculator(llm_client=NullLLMClient())

    tasks = [
        _task(id="low", alignment=0.2, leverage=1000.0, created_days_ago=5),
        _task(id="med", alignment=0.5, leverage=5000.0, created_days_ago=10),
        _task(id="high", alignment=0.9, leverage=9000.0, created_days_ago=20),
        _task(id="highest", alignment=0.95, leverage=9500.0, created_days_ago=30),
    ]

    result = await calc.calculate(tasks, now=_NOW)

    assert len(result.top_contributors) == 3
    # Should be sorted descending by debt_contribution
    contribs = [c.debt_contribution for c in result.top_contributors]
    assert contribs == sorted(contribs, reverse=True), (
        f"Contributors not sorted: {contribs}"
    )
    # The highest contributor should be 'highest' task
    assert result.top_contributors[0].task_id == "highest"
