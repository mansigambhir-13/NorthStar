"""Report generators for session and weekly priority debt reports."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from northstar.analysis.models import (
    PriorityDebtScore,
)
from northstar.reporting.templates import SESSION_REPORT_TEMPLATE, WEEKLY_REPORT_TEMPLATE

logger = logging.getLogger(__name__)


def _ascii_bar(value: float, max_value: float = 10000, width: int = 30) -> str:
    """Generate an ASCII bar representation of a value."""
    if max_value <= 0:
        return "[" + " " * width + "]"
    filled = int((value / max_value) * width)
    filled = max(0, min(filled, width))
    return "[" + "#" * filled + " " * (width - filled) + "]"


def _format_task_list(task_ids: list[str]) -> str:
    """Format a list of task IDs as a markdown bullet list."""
    if not task_ids:
        return "- None"
    return "\n".join(f"- {tid}" for tid in task_ids)


class SessionReportGenerator:
    """Generates session summary reports with decisions, drift alerts, and PDS change."""

    def __init__(self, state_manager: Any = None, llm_client: Any = None) -> None:
        self.state_manager = state_manager
        self.llm_client = llm_client

    async def generate(self, session_id: str | None = None) -> dict[str, str]:
        """Generate a session report.

        If state_manager is available and session_id is provided,
        loads data from persistence. Otherwise uses sensible defaults.

        Returns dict with 'markdown' and 'path' keys.
        """
        # Gather session data
        session_data = await self._gather_session_data(session_id)

        # Build decisions section
        decisions_section = self._format_decisions(session_data.get("decisions", []))

        # Build drift alerts section
        drift_section = self._format_drift_alerts(session_data.get("drift_alerts_list", []))

        # Get LLM insights if available
        llm_insights = await self._get_llm_insights(session_data)

        # Format the report
        pds_start = session_data.get("pds_start", 0.0)
        pds_end = session_data.get("pds_end", 0.0)

        markdown = SESSION_REPORT_TEMPLATE.format(
            session_id=session_data.get("session_id", session_id or "unknown"),
            date=session_data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
            duration_minutes=session_data.get("duration_minutes", 0.0),
            tasks_started_count=len(session_data.get("tasks_started", [])),
            tasks_completed_count=len(session_data.get("tasks_completed", [])),
            drift_alerts_count=session_data.get("drift_alerts", 0),
            pds_start=pds_start,
            pds_end=pds_end,
            pds_change=pds_end - pds_start,
            tasks_started_section=_format_task_list(session_data.get("tasks_started", [])),
            tasks_completed_section=_format_task_list(session_data.get("tasks_completed", [])),
            decisions_section=decisions_section,
            drift_alerts_section=drift_section,
            llm_insights=llm_insights,
        )

        # Determine output path
        date_str = session_data.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        sid = session_data.get("session_id", session_id or "unknown")
        path = f".northstar/reports/session-{date_str}-{sid[:8]}.md"

        return {"markdown": markdown, "path": path}

    async def _gather_session_data(self, session_id: str | None) -> dict[str, Any]:
        """Gather session data from state_manager or return defaults."""
        data: dict[str, Any] = {
            "session_id": session_id or "unknown",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "duration_minutes": 0.0,
            "tasks_started": [],
            "tasks_completed": [],
            "drift_alerts": 0,
            "drift_alerts_list": [],
            "pds_start": 0.0,
            "pds_end": 0.0,
            "decisions": [],
        }

        if self.state_manager is None or session_id is None:
            return data

        try:
            # Try to get decisions from state_manager
            decisions = await self.state_manager.get_decisions(limit=100)
            data["decisions"] = decisions

            # Get latest PDS
            pds = await self.state_manager.get_latest_pds()
            if pds is not None:
                data["pds_end"] = pds.score
        except Exception as exc:
            logger.warning("Failed to gather session data: %s", exc)

        return data

    def _format_decisions(self, decisions: list[Any]) -> str:
        """Format decision events as markdown."""
        if not decisions:
            return "- No decisions recorded"
        lines = []
        for d in decisions:
            event_type = d.event_type.value if hasattr(d, "event_type") else str(d)
            reason = d.reason if hasattr(d, "reason") else ""
            lines.append(f"- **{event_type}**: {reason}")
        return "\n".join(lines)

    def _format_drift_alerts(self, alerts: list[Any]) -> str:
        """Format drift alerts as markdown."""
        if not alerts:
            return "- No drift alerts during this session"
        lines = []
        for a in alerts:
            severity = a.get("severity", "unknown") if isinstance(a, dict) else getattr(a, "severity", "unknown")
            message = a.get("message", "") if isinstance(a, dict) else getattr(a, "message", "")
            lines.append(f"- [{severity.upper()}] {message}")
        return "\n".join(lines)

    async def _get_llm_insights(self, session_data: dict[str, Any]) -> str:
        """Get LLM-generated insights for the session."""
        if self.llm_client is None:
            return "LLM insights not available (no LLM client configured)."

        try:
            prompt = (
                f"Analyze this development session and provide brief insights:\n"
                f"- Duration: {session_data.get('duration_minutes', 0):.0f} minutes\n"
                f"- Tasks started: {len(session_data.get('tasks_started', []))}\n"
                f"- Tasks completed: {len(session_data.get('tasks_completed', []))}\n"
                f"- Drift alerts: {session_data.get('drift_alerts', 0)}\n"
                f"Provide 2-3 concise recommendations."
            )
            return await self.llm_client.query(prompt)
        except Exception as exc:
            logger.warning("LLM insights failed: %s", exc)
            return "LLM insights unavailable."


class WeeklyReportGenerator:
    """Generates weekly priority debt reports with PDS trends and recommendations."""

    def __init__(self, state_manager: Any = None, llm_client: Any = None) -> None:
        self.state_manager = state_manager
        self.llm_client = llm_client

    async def generate(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, str]:
        """Generate a weekly report.

        Returns dict with 'markdown' and 'path' keys.
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # Gather data
        weekly_data = await self._gather_weekly_data(start_date, end_date)

        # Build PDS trend
        pds_trend = self._format_pds_trend(weekly_data.get("pds_history", []))

        # Build accomplishments
        accomplishments = self._format_accomplishments(
            weekly_data.get("completed_tasks", [])
        )

        # Build debt contributors
        debt_section = self._format_debt_contributors(
            weekly_data.get("debt_contributors", [])
        )

        # Build sessions section
        sessions_section = self._format_sessions(weekly_data.get("sessions", []))

        # Build recommendations
        recommendations = await self._get_recommendations(weekly_data)

        # LLM insights
        llm_insights = await self._get_llm_insights(weekly_data)

        markdown = WEEKLY_REPORT_TEMPLATE.format(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            session_count=weekly_data.get("session_count", 0),
            total_minutes=weekly_data.get("total_minutes", 0.0),
            pds_trend=pds_trend,
            accomplishments_section=accomplishments,
            debt_contributors_section=debt_section,
            sessions_section=sessions_section,
            recommendations_section=recommendations,
            llm_insights=llm_insights,
        )

        path = f".northstar/reports/weekly-{start_date.strftime('%Y-%m-%d')}.md"

        return {"markdown": markdown, "path": path}

    async def _gather_weekly_data(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Gather weekly data from state_manager or return defaults."""
        data: dict[str, Any] = {
            "session_count": 0,
            "total_minutes": 0.0,
            "pds_history": [],
            "completed_tasks": [],
            "debt_contributors": [],
            "sessions": [],
        }

        if self.state_manager is None:
            return data

        try:
            pds_history = await self.state_manager.get_pds_history(
                start=start_date, end=end_date
            )
            data["pds_history"] = pds_history

            if pds_history:
                latest = pds_history[-1]
                data["debt_contributors"] = latest.top_contributors
        except Exception as exc:
            logger.warning("Failed to gather weekly data: %s", exc)

        return data

    def _format_pds_trend(self, pds_history: list[PriorityDebtScore]) -> str:
        """Format PDS history as ASCII bar chart."""
        if not pds_history:
            return "No PDS data available for this period."

        lines = []
        for pds in pds_history:
            date_str = pds.calculated_at.strftime("%m-%d")
            bar = _ascii_bar(pds.score)
            lines.append(f"  {date_str} {bar} {pds.score:.0f} ({pds.severity})")
        return "\n".join(lines)

    def _format_accomplishments(self, completed_tasks: list[Any]) -> str:
        """Format completed tasks as accomplishments."""
        if not completed_tasks:
            return "- No tasks completed this period"
        lines = []
        for task in completed_tasks:
            title = task.title if hasattr(task, "title") else str(task)
            lines.append(f"- {title}")
        return "\n".join(lines)

    def _format_debt_contributors(self, contributors: list[Any]) -> str:
        """Format debt contributors as a markdown table."""
        if not contributors:
            return "No significant debt contributors."
        lines = [
            "| Task | Leverage | Days Undone | Debt |",
            "|------|----------|-------------|------|",
        ]
        for c in contributors:
            title = c.task_title if hasattr(c, "task_title") else str(c)
            leverage = c.leverage_score if hasattr(c, "leverage_score") else 0
            days = c.days_undone if hasattr(c, "days_undone") else 0
            debt = c.debt_contribution if hasattr(c, "debt_contribution") else 0
            lines.append(f"| {title} | {leverage:.0f} | {days:.1f} | {debt:.0f} |")
        return "\n".join(lines)

    def _format_sessions(self, sessions: list[Any]) -> str:
        """Format session summaries."""
        if not sessions:
            return "- No sessions recorded this period"
        lines = []
        for s in sessions:
            sid = s.session_id if hasattr(s, "session_id") else str(s)
            duration = s.duration_minutes if hasattr(s, "duration_minutes") else 0
            lines.append(f"- Session {sid[:8]}: {duration:.0f} minutes")
        return "\n".join(lines)

    async def _get_recommendations(self, weekly_data: dict[str, Any]) -> str:
        """Generate recommendations based on weekly data."""
        recommendations = []
        pds_history = weekly_data.get("pds_history", [])

        if pds_history:
            latest = pds_history[-1]
            if latest.score > 5000:
                recommendations.append(
                    "- CRITICAL: PDS is very high. Focus exclusively on top-leverage tasks."
                )
            elif latest.score > 2000:
                recommendations.append(
                    "- WARNING: PDS is elevated. Review task priorities and address debt contributors."
                )

            if latest.recommendations:
                for rec in latest.recommendations:
                    recommendations.append(f"- {rec}")

        if not recommendations:
            recommendations.append("- PDS is healthy. Continue current work patterns.")

        return "\n".join(recommendations)

    async def _get_llm_insights(self, weekly_data: dict[str, Any]) -> str:
        """Get LLM-generated weekly insights."""
        if self.llm_client is None:
            return "LLM insights not available (no LLM client configured)."

        try:
            prompt = (
                f"Analyze this weekly development summary and provide insights:\n"
                f"- Sessions: {weekly_data.get('session_count', 0)}\n"
                f"- Total time: {weekly_data.get('total_minutes', 0):.0f} minutes\n"
                f"- PDS snapshots: {len(weekly_data.get('pds_history', []))}\n"
                f"Provide 3-5 actionable recommendations."
            )
            return await self.llm_client.query(prompt)
        except Exception as exc:
            logger.warning("LLM weekly insights failed: %s", exc)
            return "LLM insights unavailable."
