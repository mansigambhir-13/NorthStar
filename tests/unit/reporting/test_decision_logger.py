"""Tests for the DecisionLogger."""

from __future__ import annotations

import pytest

from northstar.analysis.models import (
    DecisionType,
    DriftAlert,
    Task,
)
from northstar.reporting.decision_logger import DecisionLogger


def _make_task(task_id: str = "t1", title: str = "Test Task", leverage: float = 5000) -> Task:
    """Create a test Task."""
    return Task(id=task_id, title=title, leverage_score=leverage)


def _make_alert() -> DriftAlert:
    """Create a test DriftAlert."""
    return DriftAlert(
        id="alert-1",
        severity="high",
        current_task_id="ct-1",
        current_task_title="Current Task",
        current_leverage=1000,
        top_task_id="tt-1",
        top_task_title="Top Task",
        top_leverage=9000,
        drift_ratio=0.11,
        session_minutes=45,
        message="Drift detected",
    )


class TestLogTaskStarted:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        task = _make_task()
        event = await logger.log_task_started(task)
        assert event.event_type == DecisionType.TASK_STARTED

    async def test_sets_task_fields(self) -> None:
        logger = DecisionLogger()
        task = _make_task(task_id="t42", title="Build Auth", leverage=8000)
        event = await logger.log_task_started(task)
        assert event.task_id == "t42"
        assert event.task_title == "Build Auth"
        assert event.leverage_score == 8000

    async def test_generates_unique_id(self) -> None:
        logger = DecisionLogger()
        task = _make_task()
        e1 = await logger.log_task_started(task)
        e2 = await logger.log_task_started(task)
        assert e1.id != e2.id


class TestLogTaskCompleted:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        task = _make_task()
        event = await logger.log_task_completed(task)
        assert event.event_type == DecisionType.TASK_COMPLETED

    async def test_sets_task_fields(self) -> None:
        logger = DecisionLogger()
        task = _make_task(task_id="t99", title="Deploy", leverage=7000)
        event = await logger.log_task_completed(task)
        assert event.task_id == "t99"
        assert event.task_title == "Deploy"


class TestLogTaskSwitched:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        from_task = _make_task(task_id="t1", title="Old Task")
        to_task = _make_task(task_id="t2", title="New Task")
        event = await logger.log_task_switched(from_task, to_task, "Higher priority")
        assert event.event_type == DecisionType.TASK_SWITCHED

    async def test_sets_from_to_ids(self) -> None:
        logger = DecisionLogger()
        from_task = _make_task(task_id="t1")
        to_task = _make_task(task_id="t2")
        event = await logger.log_task_switched(from_task, to_task, "Drift alert")
        assert event.from_task_id == "t1"
        assert event.to_task_id == "t2"

    async def test_captures_reason(self) -> None:
        logger = DecisionLogger()
        from_task = _make_task()
        to_task = _make_task(task_id="t2")
        event = await logger.log_task_switched(from_task, to_task, "User decided to switch")
        assert event.reason == "User decided to switch"

    async def test_metadata_contains_leverages(self) -> None:
        logger = DecisionLogger()
        from_task = _make_task(task_id="t1", leverage=2000)
        to_task = _make_task(task_id="t2", leverage=8000)
        event = await logger.log_task_switched(from_task, to_task, "Switch")
        assert event.metadata["from_leverage"] == 2000
        assert event.metadata["to_leverage"] == 8000


class TestLogDriftAlert:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        alert = _make_alert()
        event = await logger.log_drift_alert(alert)
        assert event.event_type == DecisionType.DRIFT_ALERT

    async def test_captures_alert_data(self) -> None:
        logger = DecisionLogger()
        alert = _make_alert()
        event = await logger.log_drift_alert(alert)
        assert event.task_id == "ct-1"
        assert event.metadata["severity"] == "high"
        assert event.metadata["drift_ratio"] == 0.11


class TestLogRerank:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        before = [_make_task(task_id="t1"), _make_task(task_id="t2")]
        after = [_make_task(task_id="t2"), _make_task(task_id="t1")]
        event = await logger.log_rerank(before, after)
        assert event.event_type == DecisionType.RERANK

    async def test_metadata_contains_order(self) -> None:
        logger = DecisionLogger()
        before = [_make_task(task_id="t1"), _make_task(task_id="t2")]
        after = [_make_task(task_id="t2"), _make_task(task_id="t1")]
        event = await logger.log_rerank(before, after)
        assert event.metadata["before_order"] == ["t1", "t2"]
        assert event.metadata["after_order"] == ["t2", "t1"]


class TestLogManualOverride:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        task = _make_task()
        event = await logger.log_manual_override(task, "Manager requested this")
        assert event.event_type == DecisionType.MANUAL_OVERRIDE

    async def test_captures_reason(self) -> None:
        logger = DecisionLogger()
        task = _make_task()
        event = await logger.log_manual_override(task, "Urgent customer request")
        assert event.reason == "Urgent customer request"


class TestLogGoalUpdated:
    async def test_creates_correct_event_type(self) -> None:
        logger = DecisionLogger()
        event = await logger.log_goal_updated("goal-1", "Adjusted deadline")
        assert event.event_type == DecisionType.GOAL_UPDATED

    async def test_captures_goal_id(self) -> None:
        logger = DecisionLogger()
        event = await logger.log_goal_updated("goal-42", "Priority changed")
        assert event.metadata["goal_id"] == "goal-42"
        assert event.reason == "Priority changed"


class TestEventTracking:
    async def test_events_property_returns_all(self) -> None:
        """Events property returns all logged events."""
        logger = DecisionLogger()
        t1 = _make_task(task_id="t1")
        t2 = _make_task(task_id="t2")
        await logger.log_task_started(t1)
        await logger.log_task_completed(t2)
        assert len(logger.events) == 2

    async def test_events_property_returns_copy(self) -> None:
        """Events property returns a copy, not the internal list."""
        logger = DecisionLogger()
        await logger.log_task_started(_make_task())
        events = logger.events
        events.clear()
        assert len(logger.events) == 1
