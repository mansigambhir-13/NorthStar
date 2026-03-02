"""Tests for the SessionTracker."""

from __future__ import annotations

import pytest

from northstar.detection.session_tracker import SessionTracker


class TestSessionLifecycle:
    """Test session start/end lifecycle."""

    async def test_start_session_returns_uuid(self) -> None:
        """start_session returns a valid UUID string."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID4 format: 8-4-4-4-12

    async def test_end_session_returns_summary(self) -> None:
        """end_session returns a SessionSummary with correct session_id."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        summary = await tracker.end_session(session_id)
        assert summary.session_id == session_id
        assert summary.start_time is not None
        assert summary.end_time is not None
        assert summary.duration_minutes >= 0

    async def test_end_unknown_session_raises(self) -> None:
        """Ending an unknown session raises KeyError."""
        tracker = SessionTracker()
        with pytest.raises(KeyError, match="Session not found"):
            await tracker.end_session("nonexistent-id")

    async def test_multiple_sessions(self) -> None:
        """Multiple sessions can coexist."""
        tracker = SessionTracker()
        s1 = await tracker.start_session()
        s2 = await tracker.start_session()
        assert s1 != s2

        summary1 = await tracker.end_session(s1)
        summary2 = await tracker.end_session(s2)
        assert summary1.session_id == s1
        assert summary2.session_id == s2


class TestTaskRecording:
    """Test task start/complete/switch recording."""

    async def test_record_task_start(self) -> None:
        """Recording a task start adds it to the session."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        await tracker.record_task_start(session_id, "task-1")

        summary = await tracker.end_session(session_id)
        assert "task-1" in summary.tasks_started

    async def test_record_task_complete(self) -> None:
        """Recording a task completion adds it to the session."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        await tracker.record_task_complete(session_id, "task-1")

        summary = await tracker.end_session(session_id)
        assert "task-1" in summary.tasks_completed

    async def test_record_task_switch(self) -> None:
        """Recording a task switch creates a decision event."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        await tracker.record_task_switch(session_id, "task-1", "task-2")

        summary = await tracker.end_session(session_id)
        assert len(summary.decisions) == 1
        assert summary.decisions[0].from_task_id == "task-1"
        assert summary.decisions[0].to_task_id == "task-2"

    async def test_record_on_unknown_session_raises(self) -> None:
        """Recording on an unknown session raises KeyError."""
        tracker = SessionTracker()
        with pytest.raises(KeyError, match="Session not found"):
            await tracker.record_task_start("nonexistent", "task-1")

    async def test_duplicate_task_start_not_added_twice(self) -> None:
        """Starting the same task twice only records it once in tasks_started."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        await tracker.record_task_start(session_id, "task-1")
        await tracker.record_task_start(session_id, "task-1")

        summary = await tracker.end_session(session_id)
        assert summary.tasks_started.count("task-1") == 1

    async def test_multiple_tasks_in_session(self) -> None:
        """Multiple tasks can be started and completed in a session."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()

        await tracker.record_task_start(session_id, "task-1")
        await tracker.record_task_start(session_id, "task-2")
        await tracker.record_task_complete(session_id, "task-1")

        summary = await tracker.end_session(session_id)
        assert set(summary.tasks_started) == {"task-1", "task-2"}
        assert summary.tasks_completed == ["task-1"]


class TestDurationCalculation:
    """Test session duration calculation."""

    async def test_duration_positive(self) -> None:
        """Duration is positive for an active session."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        duration = tracker.get_session_duration(session_id)
        assert duration >= 0

    async def test_duration_after_end(self) -> None:
        """Duration is fixed after session ends."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        await tracker.end_session(session_id)
        duration = tracker.get_session_duration(session_id)
        assert duration >= 0

    async def test_duration_unknown_session_raises(self) -> None:
        """Getting duration for unknown session raises KeyError."""
        tracker = SessionTracker()
        with pytest.raises(KeyError, match="Session not found"):
            tracker.get_session_duration("nonexistent")

    async def test_summary_duration_matches(self) -> None:
        """Summary duration matches get_session_duration."""
        tracker = SessionTracker()
        session_id = await tracker.start_session()
        summary = await tracker.end_session(session_id)
        duration = tracker.get_session_duration(session_id)
        # They should be very close (within a second)
        assert abs(summary.duration_minutes - duration) < 0.1
