"""Tests for the DriftMonitor detection engine."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from northstar.analysis.models import PriorityStack, Task
from northstar.config import DriftConfig
from northstar.detection.drift_monitor import DriftMonitor


def _make_task(task_id: str = "t1", title: str = "Test Task", leverage: float = 1000.0, file_path: str | None = None) -> Task:
    """Helper to create a Task with a specific leverage score."""
    return Task(
        id=task_id,
        title=title,
        leverage_score=leverage,
        file_path=file_path,
    )


def _make_stack(*leverages: float) -> PriorityStack:
    """Helper to create a PriorityStack from leverage scores."""
    tasks = [
        _make_task(task_id=f"t{i}", title=f"Task {i}", leverage=lev)
        for i, lev in enumerate(leverages, start=1)
    ]
    return PriorityStack(tasks=tasks)


class TestDriftMonitorThresholds:
    """Test threshold boundary conditions for drift detection."""

    @pytest.fixture
    def config(self) -> DriftConfig:
        return DriftConfig(
            high_ratio=0.3,
            high_minutes=30,
            medium_ratio=0.6,
            medium_minutes=45,
            low_ratio=0.8,
            low_minutes=60,
            snooze_minutes=15,
        )

    @pytest.fixture
    def monitor(self, config: DriftConfig) -> DriftMonitor:
        return DriftMonitor(config=config)

    async def test_high_severity_just_below_threshold(self, monitor: DriftMonitor) -> None:
        """Ratio just below 0.3 with sufficient time triggers high alert."""
        # top_n_average(3) for [9000, 6000, 3000] = 6000
        # current leverage = 1500 -> ratio = 1500/6000 = 0.25 < 0.3
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=1500)
        alert = await monitor.check_drift(current, stack, session_minutes=31)
        assert alert is not None
        assert alert.severity == "high"

    async def test_high_severity_at_threshold_no_alert(self, monitor: DriftMonitor) -> None:
        """Ratio exactly at 0.3 should NOT trigger high (must be strictly less)."""
        # top_n_average = 6000, leverage = 1800 -> ratio = 0.3 exactly
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=1800)
        alert = await monitor.check_drift(current, stack, session_minutes=31)
        # ratio = 0.3 is NOT < 0.3, so high should not trigger
        # But ratio 0.3 IS < 0.6, and 31 < 45, so medium won't trigger either
        # ratio 0.3 IS < 0.8, and 31 < 60, so low won't trigger either
        assert alert is None

    async def test_high_severity_insufficient_time(self, monitor: DriftMonitor) -> None:
        """Low ratio but insufficient time should not trigger high alert."""
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=1000)
        alert = await monitor.check_drift(current, stack, session_minutes=29)
        # ratio = 1000/6000 = 0.167 < 0.3, but 29 < 30 minutes
        assert alert is None

    async def test_medium_severity(self, monitor: DriftMonitor) -> None:
        """Ratio below 0.6 with enough time triggers medium alert."""
        stack = _make_stack(9000, 6000, 3000)
        # ratio = 3000/6000 = 0.5 < 0.6
        current = _make_task(leverage=3000)
        alert = await monitor.check_drift(current, stack, session_minutes=45)
        assert alert is not None
        assert alert.severity == "medium"

    async def test_medium_severity_insufficient_time(self, monitor: DriftMonitor) -> None:
        """Medium ratio but insufficient time should not trigger."""
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=3000)
        alert = await monitor.check_drift(current, stack, session_minutes=44)
        assert alert is None

    async def test_low_severity(self, monitor: DriftMonitor) -> None:
        """Ratio below 0.8 with enough time triggers low alert."""
        stack = _make_stack(9000, 6000, 3000)
        # ratio = 4500/6000 = 0.75 < 0.8
        current = _make_task(leverage=4500)
        alert = await monitor.check_drift(current, stack, session_minutes=60)
        assert alert is not None
        assert alert.severity == "low"

    async def test_low_severity_insufficient_time(self, monitor: DriftMonitor) -> None:
        """Low ratio but insufficient time for low alert."""
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=4500)
        alert = await monitor.check_drift(current, stack, session_minutes=59)
        assert alert is None

    async def test_no_alert_when_aligned(self, monitor: DriftMonitor) -> None:
        """No alert when current task leverage is close to top-N average."""
        stack = _make_stack(9000, 6000, 3000)
        # ratio = 6000/6000 = 1.0 >= 0.8
        current = _make_task(leverage=6000)
        alert = await monitor.check_drift(current, stack, session_minutes=120)
        assert alert is None

    async def test_no_alert_above_low_ratio(self, monitor: DriftMonitor) -> None:
        """No alert when ratio is above the low threshold."""
        stack = _make_stack(9000, 6000, 3000)
        # ratio = 5000/6000 = 0.833 >= 0.8
        current = _make_task(leverage=5000)
        alert = await monitor.check_drift(current, stack, session_minutes=120)
        assert alert is None


class TestDriftMonitorEdgeCases:
    """Test edge cases for drift detection."""

    async def test_empty_stack_returns_none(self) -> None:
        """Empty priority stack should never trigger an alert."""
        monitor = DriftMonitor()
        stack = PriorityStack(tasks=[])
        current = _make_task(leverage=100)
        alert = await monitor.check_drift(current, stack, session_minutes=60)
        # top_n_average(3) = 0, so drift_ratio = 1.0 (no drift)
        assert alert is None

    async def test_no_current_task_returns_none(self) -> None:
        """No current task should return None."""
        monitor = DriftMonitor()
        stack = _make_stack(9000, 6000, 3000)
        alert = await monitor.check_drift(None, stack, session_minutes=60)
        assert alert is None

    async def test_zero_leverage_current_task(self) -> None:
        """Current task with zero leverage score."""
        monitor = DriftMonitor()
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(leverage=0)
        # leverage = 0, top_avg > 0, but both need to be > 0 for ratio calc
        # so ratio = 1.0
        alert = await monitor.check_drift(current, stack, session_minutes=60)
        assert alert is None

    async def test_alert_contains_correct_data(self) -> None:
        """Verify alert contains all expected fields."""
        config = DriftConfig(high_ratio=0.3, high_minutes=30)
        monitor = DriftMonitor(config=config)
        stack = _make_stack(9000, 6000, 3000)
        current = _make_task(task_id="current-1", title="My Task", leverage=1000)
        alert = await monitor.check_drift(current, stack, session_minutes=31)

        assert alert is not None
        assert alert.current_task_id == "current-1"
        assert alert.current_task_title == "My Task"
        assert alert.current_leverage == 1000
        assert alert.top_task_id == "t1"
        assert alert.top_leverage == 9000
        assert alert.session_minutes == 31
        assert alert.drift_ratio == pytest.approx(1000 / 6000, rel=1e-3)
        assert "My Task" in alert.message
        assert "HIGH" in alert.message


class TestSnooze:
    """Test snooze functionality."""

    def test_snooze_suppresses_alert(self) -> None:
        """Snoozed alert returns True for is_snoozed."""
        monitor = DriftMonitor()
        monitor.snooze("alert-1", minutes=15)
        assert monitor.is_snoozed("alert-1") is True

    def test_unsnoozed_alert_not_snoozed(self) -> None:
        """Non-snoozed alert returns False."""
        monitor = DriftMonitor()
        assert monitor.is_snoozed("alert-1") is False

    def test_expired_snooze(self) -> None:
        """Expired snooze should return False."""
        monitor = DriftMonitor()
        # Manually set an expired snooze
        monitor._snoozed["alert-1"] = datetime.utcnow() - timedelta(minutes=1)
        assert monitor.is_snoozed("alert-1") is False

    def test_snooze_uses_default_minutes(self) -> None:
        """Snooze without explicit minutes uses config default."""
        config = DriftConfig(snooze_minutes=20)
        monitor = DriftMonitor(config=config)
        before = datetime.utcnow()
        monitor.snooze("alert-1")
        after = datetime.utcnow()
        expiry = monitor._snoozed["alert-1"]
        # expiry should be ~20 minutes from now
        assert expiry >= before + timedelta(minutes=20)
        assert expiry <= after + timedelta(minutes=20, seconds=1)


class TestFileToTaskInference:
    """Test file-to-task inference."""

    def test_exact_match(self) -> None:
        """Exact file_path match returns the correct task."""
        tasks = [
            _make_task(task_id="t1", file_path="src/auth.py"),
            _make_task(task_id="t2", file_path="src/models.py"),
        ]
        result = DriftMonitor.infer_task_from_file("src/auth.py", tasks)
        assert result is not None
        assert result.id == "t1"

    def test_partial_match(self) -> None:
        """Partial file_path match (substring) works as fallback."""
        tasks = [
            _make_task(task_id="t1", file_path="src/auth"),
        ]
        result = DriftMonitor.infer_task_from_file("src/auth/login.py", tasks)
        assert result is not None
        assert result.id == "t1"

    def test_no_match(self) -> None:
        """No match returns None."""
        tasks = [
            _make_task(task_id="t1", file_path="src/auth.py"),
        ]
        result = DriftMonitor.infer_task_from_file("src/payments.py", tasks)
        assert result is None

    def test_empty_file_path(self) -> None:
        """Empty file_path returns None."""
        tasks = [_make_task(task_id="t1", file_path="src/auth.py")]
        result = DriftMonitor.infer_task_from_file("", tasks)
        assert result is None

    def test_tasks_without_file_paths(self) -> None:
        """Tasks without file_path set should not match."""
        tasks = [_make_task(task_id="t1", file_path=None)]
        result = DriftMonitor.infer_task_from_file("src/auth.py", tasks)
        assert result is None
