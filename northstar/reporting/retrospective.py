"""Retrospective report generator — compares predicted leverage vs actual outcomes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from northstar.analysis.models import DecisionType
from northstar.reporting.templates import RETROSPECTIVE_TEMPLATE

logger = logging.getLogger(__name__)


class RetrospectiveGenerator:
    """Generates retrospective reports comparing predicted leverage with actual outcomes.

    Analyzes completed tasks to determine whether leverage predictions
    were accurate and identifies patterns for improvement.
    """

    def __init__(self, state_manager: Any = None, llm_client: Any = None) -> None:
        self.state_manager = state_manager
        self.llm_client = llm_client

    async def generate(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, str]:
        """Generate a retrospective report.

        Returns dict with 'markdown' and 'path' keys.
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # Gather data
        retro_data = await self._gather_retro_data(start_date, end_date)

        # Build sections
        predicted_vs_actual = self._format_predicted_vs_actual(
            retro_data.get("task_predictions", [])
        )
        avg_predicted = retro_data.get("avg_predicted_leverage", 0.0)
        avg_actual = retro_data.get("avg_actual_outcome", 0.0)
        accuracy = avg_actual / avg_predicted if avg_predicted > 0 else 0.0

        went_well = self._format_went_well(retro_data)
        could_improve = self._format_could_improve(retro_data)
        key_insights = self._format_key_insights(retro_data)
        llm_analysis = await self._get_llm_analysis(retro_data)

        markdown = RETROSPECTIVE_TEMPLATE.format(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            predicted_vs_actual_section=predicted_vs_actual,
            avg_predicted_leverage=avg_predicted,
            avg_actual_outcome=avg_actual,
            accuracy_ratio=accuracy,
            went_well_section=went_well,
            could_improve_section=could_improve,
            key_insights_section=key_insights,
            llm_analysis=llm_analysis,
        )

        path = f".northstar/reports/retro-{start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}.md"

        return {"markdown": markdown, "path": path}

    async def _gather_retro_data(
        self, start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        """Gather retrospective data from state_manager or return defaults."""
        data: dict[str, Any] = {
            "task_predictions": [],
            "avg_predicted_leverage": 0.0,
            "avg_actual_outcome": 0.0,
            "completed_count": 0,
            "drift_alert_count": 0,
            "task_switches": 0,
            "decisions": [],
        }

        if self.state_manager is None:
            return data

        try:
            # Get decisions for the period
            decisions = await self.state_manager.get_decisions(
                limit=500, start=start_date, end=end_date
            )
            data["decisions"] = decisions

            # Count events by type
            completed = [
                d for d in decisions if d.event_type == DecisionType.TASK_COMPLETED
            ]
            drift_alerts = [
                d for d in decisions if d.event_type == DecisionType.DRIFT_ALERT
            ]
            switches = [
                d for d in decisions if d.event_type == DecisionType.TASK_SWITCHED
            ]

            data["completed_count"] = len(completed)
            data["drift_alert_count"] = len(drift_alerts)
            data["task_switches"] = len(switches)

            # Calculate leverage averages from completed tasks
            leverage_scores = [
                d.leverage_score for d in completed if d.leverage_score is not None
            ]
            if leverage_scores:
                data["avg_predicted_leverage"] = sum(leverage_scores) / len(
                    leverage_scores
                )
                # Actual outcome approximated by leverage score for now
                data["avg_actual_outcome"] = data["avg_predicted_leverage"]

            # Build task prediction comparison data
            data["task_predictions"] = [
                {
                    "task_id": d.task_id,
                    "task_title": d.task_title,
                    "predicted_leverage": d.leverage_score or 0,
                    "actual_outcome": d.leverage_score or 0,
                }
                for d in completed
            ]

        except Exception as exc:
            logger.warning("Failed to gather retro data: %s", exc)

        return data

    def _format_predicted_vs_actual(self, task_predictions: list[dict[str, Any]]) -> str:
        """Format predicted vs actual comparison table."""
        if not task_predictions:
            return "No completed tasks to compare."

        lines = [
            "| Task | Predicted | Actual | Delta |",
            "|------|-----------|--------|-------|",
        ]
        for tp in task_predictions:
            title = tp.get("task_title", "Unknown")
            predicted = tp.get("predicted_leverage", 0)
            actual = tp.get("actual_outcome", 0)
            delta = actual - predicted
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"| {title} | {predicted:.0f} | {actual:.0f} | {sign}{delta:.0f} |"
            )
        return "\n".join(lines)

    def _format_went_well(self, retro_data: dict[str, Any]) -> str:
        """Identify things that went well."""
        items = []
        completed = retro_data.get("completed_count", 0)
        if completed > 0:
            items.append(f"- Completed {completed} task(s)")

        drift_alerts = retro_data.get("drift_alert_count", 0)
        if drift_alerts == 0:
            items.append("- No drift alerts — stayed focused on high-leverage work")

        if not items:
            items.append("- Review period data for positive patterns")
        return "\n".join(items)

    def _format_could_improve(self, retro_data: dict[str, Any]) -> str:
        """Identify areas for improvement."""
        items = []
        drift_alerts = retro_data.get("drift_alert_count", 0)
        if drift_alerts > 0:
            items.append(
                f"- Received {drift_alerts} drift alert(s) — consider improving task alignment"
            )

        switches = retro_data.get("task_switches", 0)
        if switches > 3:
            items.append(
                f"- {switches} task switches — try to reduce context switching"
            )

        if not items:
            items.append("- No significant issues identified")
        return "\n".join(items)

    def _format_key_insights(self, retro_data: dict[str, Any]) -> str:
        """Extract key insights from the data."""
        insights = []
        avg_predicted = retro_data.get("avg_predicted_leverage", 0)
        if avg_predicted > 5000:
            insights.append("- Working on high-leverage tasks consistently")
        elif avg_predicted > 0:
            insights.append(
                "- Average leverage below 5000 — may be spending time on lower-priority work"
            )

        if not insights:
            insights.append("- Insufficient data for insights — continue tracking")
        return "\n".join(insights)

    async def _get_llm_analysis(self, retro_data: dict[str, Any]) -> str:
        """Get LLM-generated retrospective analysis."""
        if self.llm_client is None:
            return "LLM analysis not available (no LLM client configured)."

        try:
            prompt = (
                f"Analyze this development retrospective:\n"
                f"- Tasks completed: {retro_data.get('completed_count', 0)}\n"
                f"- Drift alerts: {retro_data.get('drift_alert_count', 0)}\n"
                f"- Task switches: {retro_data.get('task_switches', 0)}\n"
                f"- Avg predicted leverage: {retro_data.get('avg_predicted_leverage', 0):.0f}\n"
                f"Provide a brief retrospective analysis with actionable improvements."
            )
            return await self.llm_client.query(prompt)
        except Exception as exc:
            logger.warning("LLM retro analysis failed: %s", exc)
            return "LLM analysis unavailable."
