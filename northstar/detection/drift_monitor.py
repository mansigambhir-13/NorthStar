"""Drift detection monitor — detects when current work drifts from highest-leverage tasks."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from northstar.analysis.models import DriftAlert, PriorityStack, Task
from northstar.config import DriftConfig

logger = logging.getLogger(__name__)


class DriftMonitor:
    """Monitors whether the developer is working on high-leverage tasks.

    Compares the current task's leverage score against the top-N average
    from the priority stack and fires alerts when the ratio drops below
    configured thresholds for a sustained period.
    """

    def __init__(self, config: DriftConfig | None = None, state_manager: Any = None) -> None:
        self.config = config or DriftConfig()
        self.state_manager = state_manager
        self._snoozed: dict[str, datetime] = {}  # alert_id -> expiry time

    async def check_drift(
        self,
        current_task: Task | None,
        priority_stack: PriorityStack,
        session_minutes: float,
    ) -> DriftAlert | None:
        """Check if current work has drifted from highest-leverage tasks.

        Returns a DriftAlert if drift is detected, or None if aligned.
        """
        if current_task is None:
            return None

        top_avg = priority_stack.top_n_average(3)

        # Calculate drift ratio
        if top_avg > 0 and current_task.leverage_score > 0:
            drift_ratio = current_task.leverage_score / top_avg
        else:
            drift_ratio = 1.0

        # Determine severity based on thresholds
        severity = self._evaluate_severity(drift_ratio, session_minutes)
        if severity is None:
            return None

        top_task = priority_stack.top

        alert_id = str(uuid.uuid4())
        alert = DriftAlert(
            id=alert_id,
            severity=severity,
            current_task_id=current_task.id,
            current_task_title=current_task.title,
            current_leverage=current_task.leverage_score,
            top_task_id=top_task.id if top_task else None,
            top_task_title=top_task.title if top_task else "",
            top_leverage=top_task.leverage_score if top_task else 0.0,
            drift_ratio=drift_ratio,
            session_minutes=session_minutes,
            message=self._build_message(severity, current_task, top_task, drift_ratio, session_minutes),
        )

        # Check if this alert should be suppressed due to snooze
        if self.is_snoozed(alert_id):
            return None

        # Persist if state_manager is available
        if self.state_manager is not None:
            try:
                await self.state_manager.save_drift_alert(alert)
            except Exception as exc:
                logger.warning("Failed to persist drift alert: %s", exc)

        return alert

    def _evaluate_severity(self, drift_ratio: float, session_minutes: float) -> str | None:
        """Evaluate severity level based on ratio and time thresholds.

        Returns severity string or None if no alert warranted.
        """
        if drift_ratio < self.config.high_ratio and session_minutes >= self.config.high_minutes:
            return "high"
        if drift_ratio < self.config.medium_ratio and session_minutes >= self.config.medium_minutes:
            return "medium"
        if drift_ratio < self.config.low_ratio and session_minutes >= self.config.low_minutes:
            return "low"
        return None

    def _build_message(
        self,
        severity: str,
        current_task: Task,
        top_task: Task | None,
        drift_ratio: float,
        session_minutes: float,
    ) -> str:
        """Build a human-readable drift alert message."""
        severity_label = severity.upper()
        ratio_pct = f"{drift_ratio:.0%}"
        top_title = top_task.title if top_task else "unknown"
        top_leverage = f"{top_task.leverage_score:.0f}" if top_task else "N/A"

        return (
            f"[{severity_label} DRIFT] You've been working on '{current_task.title}' "
            f"(leverage: {current_task.leverage_score:.0f}) for {session_minutes:.0f} minutes. "
            f"This is at {ratio_pct} of top-task leverage. "
            f"Consider switching to '{top_title}' (leverage: {top_leverage})."
        )

    def is_snoozed(self, alert_id: str) -> bool:
        """Check whether an alert is currently snoozed."""
        if alert_id not in self._snoozed:
            return False
        if datetime.utcnow() >= self._snoozed[alert_id]:
            del self._snoozed[alert_id]
            return False
        return True

    def snooze(self, alert_id: str, minutes: int | None = None) -> None:
        """Snooze an alert for the given number of minutes."""
        if minutes is None:
            minutes = self.config.snooze_minutes
        self._snoozed[alert_id] = datetime.utcnow() + timedelta(minutes=minutes)

    @staticmethod
    def infer_task_from_file(file_path: str, tasks: list[Task]) -> Task | None:
        """Infer which task a file belongs to by matching task.file_path.

        Returns the first task whose file_path matches, or None.
        """
        if not file_path:
            return None
        for task in tasks:
            if task.file_path and task.file_path == file_path:
                return task
        # Fallback: partial match (file_path is a substring)
        for task in tasks:
            if task.file_path and task.file_path in file_path:
                return task
        return None
