"""Tests for drift alert display and formatting."""

from __future__ import annotations

from datetime import datetime

from northstar.analysis.models import DriftAlert
from northstar.detection.alerting import display_drift_alert, format_drift_alert


def _make_alert(
    severity: str = "high",
    current_title: str = "Current Task",
    current_leverage: float = 1000.0,
    top_title: str = "Top Task",
    top_leverage: float = 9000.0,
    drift_ratio: float = 0.11,
    session_minutes: float = 45.0,
) -> DriftAlert:
    """Create a test DriftAlert."""
    return DriftAlert(
        id="alert-001",
        severity=severity,
        current_task_id="ct-1",
        current_task_title=current_title,
        current_leverage=current_leverage,
        top_task_id="tt-1",
        top_task_title=top_title,
        top_leverage=top_leverage,
        drift_ratio=drift_ratio,
        session_minutes=session_minutes,
        message=f"[{severity.upper()} DRIFT] Working on low-leverage task",
        created_at=datetime(2025, 6, 1, 12, 0, 0),
    )


class TestDisplayDriftAlert:
    """Test Rich panel rendering of drift alerts."""

    def test_display_returns_string(self) -> None:
        """display_drift_alert returns a non-empty string."""
        alert = _make_alert()
        result = display_drift_alert(alert)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_display_contains_severity(self) -> None:
        """Output contains the severity level."""
        alert = _make_alert(severity="high")
        result = display_drift_alert(alert)
        assert "HIGH" in result

    def test_display_contains_task_names(self) -> None:
        """Output contains current and top task titles."""
        alert = _make_alert(current_title="Fix Bug", top_title="Ship Feature")
        result = display_drift_alert(alert)
        assert "Fix Bug" in result
        assert "Ship Feature" in result

    def test_display_contains_leverage_scores(self) -> None:
        """Output contains leverage scores."""
        alert = _make_alert(current_leverage=1500, top_leverage=8000)
        result = display_drift_alert(alert)
        assert "1500" in result
        assert "8000" in result

    def test_display_contains_session_time(self) -> None:
        """Output contains session time."""
        alert = _make_alert(session_minutes=60)
        result = display_drift_alert(alert)
        assert "60" in result

    def test_display_contains_drift_alert_title(self) -> None:
        """Output contains 'Drift Alert' title."""
        alert = _make_alert()
        result = display_drift_alert(alert)
        assert "Drift Alert" in result

    def test_display_medium_severity(self) -> None:
        """Medium severity alert renders correctly."""
        alert = _make_alert(severity="medium")
        result = display_drift_alert(alert)
        assert "MEDIUM" in result

    def test_display_low_severity(self) -> None:
        """Low severity alert renders correctly."""
        alert = _make_alert(severity="low")
        result = display_drift_alert(alert)
        assert "LOW" in result


class TestFormatDriftAlert:
    """Test JSON-serializable format of drift alerts."""

    def test_format_returns_dict(self) -> None:
        """format_drift_alert returns a dictionary."""
        alert = _make_alert()
        result = format_drift_alert(alert)
        assert isinstance(result, dict)

    def test_format_contains_severity(self) -> None:
        """Formatted dict contains severity field."""
        alert = _make_alert(severity="medium")
        result = format_drift_alert(alert)
        assert result["severity"] == "medium"

    def test_format_contains_current_task(self) -> None:
        """Formatted dict contains current_task nested object."""
        alert = _make_alert(current_title="My Task", current_leverage=2000)
        result = format_drift_alert(alert)
        assert result["current_task"]["title"] == "My Task"
        assert result["current_task"]["leverage"] == 2000

    def test_format_contains_top_task(self) -> None:
        """Formatted dict contains top_task nested object."""
        alert = _make_alert(top_title="Best Task", top_leverage=9000)
        result = format_drift_alert(alert)
        assert result["top_task"]["title"] == "Best Task"
        assert result["top_task"]["leverage"] == 9000

    def test_format_contains_drift_ratio(self) -> None:
        """Formatted dict contains drift_ratio."""
        alert = _make_alert(drift_ratio=0.25)
        result = format_drift_alert(alert)
        assert result["drift_ratio"] == 0.25

    def test_format_contains_session_minutes(self) -> None:
        """Formatted dict contains session_minutes."""
        alert = _make_alert(session_minutes=90)
        result = format_drift_alert(alert)
        assert result["session_minutes"] == 90

    def test_format_contains_message(self) -> None:
        """Formatted dict contains message."""
        alert = _make_alert()
        result = format_drift_alert(alert)
        assert "DRIFT" in result["message"]

    def test_format_contains_created_at(self) -> None:
        """Formatted dict contains created_at as ISO string."""
        alert = _make_alert()
        result = format_drift_alert(alert)
        assert "created_at" in result
        assert isinstance(result["created_at"], str)

    def test_format_snoozed_until_none(self) -> None:
        """snoozed_until is None when not set."""
        alert = _make_alert()
        result = format_drift_alert(alert)
        assert result["snoozed_until"] is None

    def test_format_id_present(self) -> None:
        """Alert ID is present in formatted output."""
        alert = _make_alert()
        result = format_drift_alert(alert)
        assert result["id"] == "alert-001"
