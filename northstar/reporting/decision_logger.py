"""Decision event logger for tracking all priority decisions."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from northstar.analysis.models import (
    DecisionEvent,
    DecisionType,
    DriftAlert,
    Task,
)

logger = logging.getLogger(__name__)


class DecisionLogger:
    """Logs priority decision events and optionally persists them.

    Each log method creates a DecisionEvent with the appropriate
    DecisionType and metadata, then delegates to state_manager
    if one is available.
    """

    def __init__(self, state_manager: Any = None) -> None:
        self.state_manager = state_manager
        self._events: list[DecisionEvent] = []

    async def _persist(self, event: DecisionEvent) -> None:
        """Store event in memory and optionally persist to state_manager."""
        self._events.append(event)
        if self.state_manager is not None:
            try:
                await self.state_manager.log_decision(event)
            except Exception as exc:
                logger.warning("Failed to persist decision event: %s", exc)

    async def log_task_started(self, task: Task) -> DecisionEvent:
        """Log that a task was started."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_STARTED,
            task_id=task.id,
            task_title=task.title,
            leverage_score=task.leverage_score,
            reason=f"Started working on '{task.title}'",
        )
        await self._persist(event)
        return event

    async def log_task_completed(self, task: Task) -> DecisionEvent:
        """Log that a task was completed."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_COMPLETED,
            task_id=task.id,
            task_title=task.title,
            leverage_score=task.leverage_score,
            reason=f"Completed '{task.title}'",
        )
        await self._persist(event)
        return event

    async def log_task_switched(
        self, from_task: Task, to_task: Task, reason: str
    ) -> DecisionEvent:
        """Log a task switch from one task to another."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.TASK_SWITCHED,
            task_id=to_task.id,
            task_title=to_task.title,
            from_task_id=from_task.id,
            to_task_id=to_task.id,
            leverage_score=to_task.leverage_score,
            reason=reason,
            metadata={
                "from_task_title": from_task.title,
                "from_leverage": from_task.leverage_score,
                "to_leverage": to_task.leverage_score,
            },
        )
        await self._persist(event)
        return event

    async def log_drift_alert(self, alert: DriftAlert) -> DecisionEvent:
        """Log that a drift alert was triggered."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.DRIFT_ALERT,
            task_id=alert.current_task_id,
            task_title=alert.current_task_title,
            leverage_score=alert.current_leverage,
            reason=alert.message,
            metadata={
                "alert_id": alert.id,
                "severity": alert.severity,
                "drift_ratio": alert.drift_ratio,
                "top_task_id": alert.top_task_id,
                "top_task_title": alert.top_task_title,
                "session_minutes": alert.session_minutes,
            },
        )
        await self._persist(event)
        return event

    async def log_rerank(
        self, tasks_before: list[Task], tasks_after: list[Task]
    ) -> DecisionEvent:
        """Log a reranking of the priority stack."""
        before_ids = [t.id for t in tasks_before]
        after_ids = [t.id for t in tasks_after]

        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.RERANK,
            reason="Priority stack reranked",
            metadata={
                "before_order": before_ids,
                "after_order": after_ids,
                "tasks_count": len(tasks_after),
            },
        )
        await self._persist(event)
        return event

    async def log_manual_override(self, task: Task, reason: str) -> DecisionEvent:
        """Log a manual override of task priority."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.MANUAL_OVERRIDE,
            task_id=task.id,
            task_title=task.title,
            leverage_score=task.leverage_score,
            reason=reason,
        )
        await self._persist(event)
        return event

    async def log_goal_updated(self, goal_id: str, changes: str) -> DecisionEvent:
        """Log that a goal was updated."""
        event = DecisionEvent(
            id=str(uuid.uuid4()),
            event_type=DecisionType.GOAL_UPDATED,
            reason=changes,
            metadata={"goal_id": goal_id},
        )
        await self._persist(event)
        return event

    @property
    def events(self) -> list[DecisionEvent]:
        """Return all logged events (in-memory)."""
        return list(self._events)
