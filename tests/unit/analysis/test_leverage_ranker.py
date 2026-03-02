"""Tests for the LeverageRanker analysis engine."""

from __future__ import annotations

from datetime import datetime

import pytest

from northstar.analysis.leverage_ranker import LeverageRanker
from northstar.analysis.models import (
    Goal,
    GoalSet,
    GoalStatus,
    PriorityStack,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)
from northstar.config import ScoringConfig
from northstar.integrations.llm import NullLLMClient


# ── Helpers ──────────────────────────────────────────────────────────


def _config() -> ScoringConfig:
    return ScoringConfig()


def _goals() -> GoalSet:
    return GoalSet(
        goals=[
            Goal(
                id="goal-1",
                title="Launch MVP",
                description="Ship MVP",
                priority=1,
                status=GoalStatus.ACTIVE,
            ),
        ]
    )


def _task(
    *,
    id: str = "t1",
    alignment: float = 0.8,
    impact: int = 80,
    urgency: UrgencyLevel = UrgencyLevel.NORMAL,
    effort: float = 2.0,
    blocks: list[str] | None = None,
    goal_id: str = "goal-1",
) -> Task:
    return Task(
        id=id,
        title=f"Task {id}",
        goal_id=goal_id,
        goal_alignment=alignment,
        impact=impact,
        urgency=urgency,
        effort_hours=effort,
        blocks=blocks or [],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


# ── Tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deterministic_scoring() -> None:
    """Same inputs produce identical scores across multiple runs."""
    ranker = LeverageRanker(config=_config(), llm_client=NullLLMClient())
    tasks = [
        _task(id="a", alignment=0.9, impact=85, urgency=UrgencyLevel.BLOCKING, effort=4.0, blocks=["b"]),
        _task(id="b", alignment=0.6, impact=50, urgency=UrgencyLevel.NORMAL, effort=2.0),
    ]
    goals = _goals()

    results: list[PriorityStack] = []
    for _ in range(3):
        # Create fresh copies each run so scores are re-computed
        fresh = [t.model_copy(deep=True) for t in tasks]
        stack = await ranker.rank(fresh, goals)
        results.append(stack)

    for i in range(1, len(results)):
        assert len(results[i].tasks) == len(results[0].tasks)
        for t0, ti in zip(results[0].tasks, results[i].tasks):
            assert t0.leverage_score == ti.leverage_score, (
                f"Run 0 vs {i}: {t0.leverage_score} != {ti.leverage_score}"
            )


@pytest.mark.asyncio
async def test_zero_effort_floor() -> None:
    """Tasks with effort=0 should use config.min_effort, not crash."""
    ranker = LeverageRanker(config=_config(), llm_client=None)
    task = _task(effort=0.0, alignment=0.5, impact=50)
    stack = await ranker.rank([task], _goals())

    assert len(stack.tasks) == 1
    assert stack.tasks[0].leverage_score > 0
    # Should not raise ZeroDivisionError


@pytest.mark.asyncio
async def test_blocking_vs_nonblocking() -> None:
    """A blocking task scores higher than an otherwise-identical non-blocking task."""
    ranker = LeverageRanker(config=_config(), llm_client=None)
    blocking = _task(id="blocking", urgency=UrgencyLevel.BLOCKING)
    normal = _task(id="normal", urgency=UrgencyLevel.NORMAL)

    stack = await ranker.rank([blocking, normal], _goals())

    # Blocking should be ranked first
    assert stack.tasks[0].id == "blocking"
    assert stack.tasks[0].leverage_score > stack.tasks[1].leverage_score


@pytest.mark.asyncio
async def test_ranking_order_ecommerce_scenario() -> None:
    """E-commerce scenario: auth (blocking, high alignment) > landing page > CI/CD."""
    ranker = LeverageRanker(config=_config(), llm_client=None)
    auth = _task(
        id="auth",
        alignment=0.9,
        impact=85,
        urgency=UrgencyLevel.BLOCKING,
        effort=4.0,
        blocks=["landing", "cicd"],
    )
    landing = _task(
        id="landing",
        alignment=0.6,
        impact=50,
        urgency=UrgencyLevel.NORMAL,
        effort=2.0,
    )
    cicd = _task(
        id="cicd",
        alignment=0.4,
        impact=30,
        urgency=UrgencyLevel.NORMAL,
        effort=3.0,
    )

    stack = await ranker.rank([cicd, landing, auth], _goals())

    ids = [t.id for t in stack.tasks]
    assert ids == ["auth", "landing", "cicd"], f"Unexpected order: {ids}"


@pytest.mark.asyncio
async def test_max_min_boundary() -> None:
    """All scores must fall within 0-10000."""
    ranker = LeverageRanker(config=_config(), llm_client=None)
    tasks = [
        _task(id="max", alignment=1.0, impact=100, urgency=UrgencyLevel.BLOCKING, effort=0.0, blocks=["a", "b", "c"]),
        _task(id="min", alignment=0.0, impact=1, urgency=UrgencyLevel.NORMAL, effort=100.0),
    ]
    stack = await ranker.rank(tasks, _goals())

    for t in stack.tasks:
        assert 0 <= t.leverage_score <= 10000, (
            f"Score {t.leverage_score} out of bounds for task {t.id}"
        )

    # The highest should be exactly 10000 (normalized max)
    assert stack.tasks[0].leverage_score == 10000.0


@pytest.mark.asyncio
async def test_empty_tasks() -> None:
    """Empty task list returns an empty PriorityStack."""
    ranker = LeverageRanker(config=_config(), llm_client=None)
    stack = await ranker.rank([], _goals())

    assert stack.tasks == []
    assert stack.top is None
    assert stack.top_n == []
    assert stack.top_n_average() == 0.0
