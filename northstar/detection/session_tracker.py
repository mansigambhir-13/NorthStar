"""Session tracking for development work sessions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from northstar.analysis.models import DecisionEvent, DecisionType, SessionSummary

logger = logging.getLogger(__name__)


class SessionTracker:
    """Tracks development sessions including task starts, completions, and switches.

    Maintains in-memory tracking state and optionally delegates persistence
    to a StateManager if one is provided.
    """

    def __init__(self, state_manager: Any = None) -> None:
        self.state_manager = state_manager
        # In-memory session tracking: session_id -> session data
        self._sessions: dict[str, dict[str, Any]] = {}

    async def start_session(self) -> str:
        """Start a new development session.

        Returns the session_id (uuid4).
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        self._sessions[session_id] = {
            "start_time": now,
            "end_time": None,
            "tasks_started": [],
            "tasks_completed": [],
            "task_switches": [],
            "decisions": [],
        }

        if self.state_manager is not None:
            try:
                await self.state_manager.save_session_start(session_id, now)
            except Exception as exc:
                logger.warning("Failed to persist session start: %s", exc)

        logger.info("Session started: %s", session_id)
        return session_id

    async def end_session(self, session_id: str) -> SessionSummary:
        """End a session and return a summary.

        Raises KeyError if session_id is not found.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        now = datetime.utcnow()
        session["end_time"] = now

        start_time: datetime = session["start_time"]
        duration_minutes = (now - start_time).total_seconds() / 60.0

        summary = SessionSummary(
            session_id=session_id,
            start_time=start_time,
            end_time=now,
            duration_minutes=duration_minutes,
            tasks_started=list(session["tasks_started"]),
            tasks_completed=list(session["tasks_completed"]),
            drift_alerts=0,
            decisions=list(session["decisions"]),
        )

        if self.state_manager is not None:
            try:
                await self.state_manager.save_session_end(
                    session_id=session_id,
                    end_time=now,
                    duration_minutes=duration_minutes,
                    tasks_started=summary.tasks_started,
                    tasks_completed=summary.tasks_completed,
                    drift_alerts=summary.drift_alerts,
                )
            except Exception as exc:
                logger.warning("Failed to persist session end: %s", exc)

        logger.info("Session ended: %s (%.1f minutes)", session_id, duration_minutes)
        return summary

    async def record_task_start(self, session_id: str, task_id: str) -> None:
        """Record that a task was started within a session."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if task_id not in session["tasks_started"]:
            session["tasks_started"].append(task_id)

        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_STARTED,
            task_id=task_id,
        )
        session["decisions"].append(event)

        if self.state_manager is not None:
            try:
                await self.state_manager.log_decision(event)
            except Exception as exc:
                logger.warning("Failed to persist task start event: %s", exc)

    async def record_task_complete(self, session_id: str, task_id: str) -> None:
        """Record that a task was completed within a session."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        if task_id not in session["tasks_completed"]:
            session["tasks_completed"].append(task_id)

        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_COMPLETED,
            task_id=task_id,
        )
        session["decisions"].append(event)

        if self.state_manager is not None:
            try:
                await self.state_manager.log_decision(event)
            except Exception as exc:
                logger.warning("Failed to persist task complete event: %s", exc)

    async def record_task_switch(
        self, session_id: str, from_task_id: str, to_task_id: str
    ) -> None:
        """Record a task switch within a session."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        session["task_switches"].append(
            {"from": from_task_id, "to": to_task_id, "time": datetime.utcnow()}
        )

        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_SWITCHED,
            from_task_id=from_task_id,
            to_task_id=to_task_id,
        )
        session["decisions"].append(event)

        if self.state_manager is not None:
            try:
                await self.state_manager.log_decision(event)
            except Exception as exc:
                logger.warning("Failed to persist task switch event: %s", exc)

    def get_session_duration(self, session_id: str) -> float:
        """Get the duration of a session in minutes.

        Returns elapsed time from start until now (if still running)
        or until end_time (if ended).

        Raises KeyError if session_id is not found.
        """
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")

        session = self._sessions[session_id]
        start_time: datetime = session["start_time"]
        end_time: datetime | None = session["end_time"]

        if end_time is not None:
            return (end_time - start_time).total_seconds() / 60.0
        return (datetime.utcnow() - start_time).total_seconds() / 60.0
