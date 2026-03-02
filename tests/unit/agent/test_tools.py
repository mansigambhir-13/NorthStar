"""Tests for Strands agent tool definitions.

These tests verify the tool functions work correctly with mocked engine state
by injecting a real StateManager (with in-memory SQLite) and NullLLMClient.

The tools are async, so we await them directly in the async test context.
We call the underlying tool function (via .__wrapped__ or direct call) —
not through the Strands decorator harness — so we can test in-process.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from northstar.agent.tools import (
    ALL_TOOLS,
    set_engine_state,
)
from northstar.analysis.models import (
    CodebaseProfile,
    Goal,
    GoalSet,
    GoalStatus,
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)
from northstar.config import NorthStarConfig
from northstar.integrations.llm import NullLLMClient
from northstar.state.manager import StateManager

# ── Import the raw async functions (before Strands wrapping) ──────────
# Strands @tool wraps the function; we need the underlying coroutine for tests.
from northstar.agent import tools as _tools_mod


async def _call_get_goals():
    return await _tools_mod.get_goals.__wrapped__()


async def _call_get_tasks(status_filter="all"):
    return await _tools_mod.get_tasks.__wrapped__(status_filter=status_filter)


async def _call_rank_tasks():
    return await _tools_mod.rank_tasks.__wrapped__()


async def _call_calculate_pds():
    return await _tools_mod.calculate_pds.__wrapped__()


async def _call_analyze_gaps():
    return await _tools_mod.analyze_gaps.__wrapped__()


async def _call_check_drift(current_task_id="", session_minutes=0.0):
    return await _tools_mod.check_drift.__wrapped__(
        current_task_id=current_task_id, session_minutes=session_minutes
    )


async def _call_update_task_status(task_id, new_status):
    return await _tools_mod.update_task_status.__wrapped__(
        task_id=task_id, new_status=new_status
    )


async def _call_get_pds_history(limit=10):
    return await _tools_mod.get_pds_history.__wrapped__(limit=limit)


@pytest.fixture()
async def setup_tools(tmp_path: Path):
    """Set up a StateManager with sample data and inject into tool state."""
    db_path = tmp_path / "state.db"
    ctx_path = tmp_path / "context.json"
    config = NorthStarConfig(project_root=str(tmp_path), project_name="test-project")
    llm = NullLLMClient()

    sm = StateManager(db_path=db_path, context_path=ctx_path)
    await sm.__aenter__()

    # Create sample context with goals
    goal = Goal(
        id="g1",
        title="Ship MVP",
        description="Deliver the minimum viable product",
        priority=1,
        status=GoalStatus.ACTIVE,
    )
    context = StrategicContext(
        project_name="test-project",
        project_root=str(tmp_path),
        codebase=CodebaseProfile(root_path=str(tmp_path), total_files=5, total_loc=500),
        goals=GoalSet(goals=[goal]),
        tasks=[],
    )
    await sm.save_context(context)

    # Create sample tasks
    now = datetime.now(tz=timezone.utc)
    tasks = [
        Task(
            id="t1",
            title="Implement auth",
            goal_id="g1",
            goal_alignment=0.9,
            impact=85,
            urgency=UrgencyLevel.DEADLINE_48H,
            effort_hours=4.0,
            source=TaskSource.MANUAL,
            created_at=now,
            updated_at=now,
        ),
        Task(
            id="t2",
            title="Write README",
            goal_id="g1",
            goal_alignment=0.3,
            impact=30,
            urgency=UrgencyLevel.NORMAL,
            effort_hours=1.0,
            source=TaskSource.MANUAL,
            created_at=now,
            updated_at=now,
        ),
        Task(
            id="t3",
            title="Fix login bug",
            status=TaskStatus.IN_PROGRESS,
            goal_id="g1",
            goal_alignment=0.7,
            impact=60,
            urgency=UrgencyLevel.NORMAL,
            effort_hours=2.0,
            source=TaskSource.MANUAL,
            created_at=now,
            updated_at=now,
        ),
    ]
    for t in tasks:
        await sm.save_task(t)

    set_engine_state(config=config, state_manager=sm, llm_client=llm)

    yield sm

    await sm.__aexit__(None, None, None)


class TestToolRegistry:
    def test_all_tools_has_entries(self) -> None:
        assert len(ALL_TOOLS) >= 7

    def test_tools_are_callable(self) -> None:
        for tool_fn in ALL_TOOLS:
            assert callable(tool_fn)


class TestGetGoals:
    async def test_returns_goals(self, setup_tools) -> None:
        result = await _call_get_goals()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Ship MVP"
        assert data[0]["id"] == "g1"


class TestGetTasks:
    async def test_returns_all_tasks(self, setup_tools) -> None:
        result = await _call_get_tasks()
        data = json.loads(result)
        assert len(data) == 3

    async def test_filter_by_status(self, setup_tools) -> None:
        result = await _call_get_tasks(status_filter="in_progress")
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["title"] == "Fix login bug"


class TestRankTasks:
    async def test_returns_ranked_list(self, setup_tools) -> None:
        result = await _call_rank_tasks()
        data = json.loads(result)
        assert "ranked_tasks" in data
        assert data["total"] == 3
        # First task should have highest leverage
        scores = [t["leverage_score"] for t in data["ranked_tasks"]]
        assert scores == sorted(scores, reverse=True)


class TestCalculatePds:
    async def test_returns_pds(self, setup_tools) -> None:
        result = await _call_calculate_pds()
        data = json.loads(result)
        assert "score" in data
        assert "severity" in data
        assert data["severity"] in ("green", "yellow", "orange", "red")


class TestAnalyzeGaps:
    async def test_returns_gap_reports(self, setup_tools) -> None:
        result = await _call_analyze_gaps()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "goal" in data[0]
        assert "coverage" in data[0]


class TestCheckDrift:
    async def test_drift_with_active_task(self, setup_tools) -> None:
        result = await _call_check_drift(session_minutes=60.0)
        data = json.loads(result)
        assert "status" in data

    async def test_no_active_task(self, setup_tools) -> None:
        # Update all tasks to pending
        sm = setup_tools
        await sm.update_task_status("t3", TaskStatus.PENDING)
        result = await _call_check_drift(session_minutes=10.0)
        data = json.loads(result)
        assert data["status"] == "no_active_task"


class TestUpdateTaskStatus:
    async def test_update_status(self, setup_tools) -> None:
        result = await _call_update_task_status(task_id="t1", new_status="in_progress")
        data = json.loads(result)
        assert data["success"] is True

    async def test_invalid_status(self, setup_tools) -> None:
        result = await _call_update_task_status(task_id="t1", new_status="invalid")
        data = json.loads(result)
        assert "error" in data


class TestGetPdsHistory:
    async def test_empty_history(self, setup_tools) -> None:
        result = await _call_get_pds_history()
        data = json.loads(result)
        assert isinstance(data, list)

    async def test_after_calculation(self, setup_tools) -> None:
        # First calculate PDS to populate history
        await _call_calculate_pds()
        result = await _call_get_pds_history()
        data = json.loads(result)
        assert len(data) >= 1
