"""Drift alert display and formatting utilities."""

from __future__ import annotations

import io
from typing import Any

from rich.console import Console
from rich.panel import Panel

from northstar.analysis.models import DriftAlert

# Severity -> Rich border color mapping
_SEVERITY_COLORS: dict[str, str] = {
    "high": "red",
    "medium": "yellow",
    "low": "blue",
}

_SEVERITY_ICONS: dict[str, str] = {
    "high": "!!!",
    "medium": "!!",
    "low": "!",
}


def display_drift_alert(alert: DriftAlert) -> str:
    """Display a drift alert using Rich Panel with severity-based styling.

    Renders the alert to a string (suitable for non-interactive or JSON mode)
    and also prints it to the console.

    Returns the formatted string representation.
    """
    color = _SEVERITY_COLORS.get(alert.severity, "white")
    icon = _SEVERITY_ICONS.get(alert.severity, "!")

    # Build the content text
    content_lines = [
        f"  Severity:     {alert.severity.upper()} {icon}",
        "",
        f"  Current task: {alert.current_task_title}",
        f"  Leverage:     {alert.current_leverage:.0f}",
        "",
        f"  Top task:     {alert.top_task_title}",
        f"  Leverage:     {alert.top_leverage:.0f}",
        "",
        f"  Drift ratio:  {alert.drift_ratio:.2f}",
        f"  Session time: {alert.session_minutes:.0f} minutes",
    ]

    if alert.message:
        content_lines.append("")
        content_lines.append(f"  {alert.message}")

    content = "\n".join(content_lines)

    panel = Panel(
        content,
        title="Drift Alert",
        border_style=color,
        expand=False,
    )

    # Render to string using a string buffer
    string_io = io.StringIO()
    console = Console(file=string_io, force_terminal=False, width=80)
    console.print(panel)
    rendered = string_io.getvalue()

    return rendered


def format_drift_alert(alert: DriftAlert) -> dict[str, Any]:
    """Format a drift alert as a JSON-serializable dictionary.

    Returns a flat dictionary with all alert fields suitable for
    serialization and API responses.
    """
    return {
        "id": alert.id,
        "severity": alert.severity,
        "current_task": {
            "id": alert.current_task_id,
            "title": alert.current_task_title,
            "leverage": alert.current_leverage,
        },
        "top_task": {
            "id": alert.top_task_id,
            "title": alert.top_task_title,
            "leverage": alert.top_leverage,
        },
        "drift_ratio": alert.drift_ratio,
        "session_minutes": alert.session_minutes,
        "message": alert.message,
        "user_response": alert.user_response,
        "snoozed_until": alert.snoozed_until.isoformat() if alert.snoozed_until else None,
        "created_at": alert.created_at.isoformat(),
    }
