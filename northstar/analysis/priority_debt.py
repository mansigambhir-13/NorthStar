"""Priority Debt Score (PDS) calculator.

Measures the accumulated cost of leaving high-leverage tasks undone.
The longer a high-alignment, high-leverage task sits in PENDING/IN_PROGRESS,
the more priority debt accrues -- exponentially.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from northstar.analysis.models import (
    DebtContributor,
    PriorityDebtScore,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)

# Exponential growth rate for days-undone penalty
_DECAY_RATE = 0.1


class PriorityDebtCalculator:
    """Calculate the Priority Debt Score for a task set."""

    def __init__(self, llm_client: Any = None) -> None:
        self.llm_client = llm_client

    # ── Core calculation ─────────────────────────────────────────────

    async def calculate(
        self,
        tasks: list[Task],
        now: datetime | None = None,
    ) -> PriorityDebtScore:
        """Compute the PDS across all tasks.

        Formula
        -------
        PDS = sum_undone(alignment_i * (leverage_i / 10000) * e^(0.1 * days_undone_i))
              - sum_done(alignment_j * (leverage_j / 10000))

        The result is multiplied by 1000 and clamped to [0, 10000].
        """
        if not tasks:
            return PriorityDebtScore(
                score=0.0,
                severity="green",
                top_contributors=[],
                diagnosis="No tasks to evaluate.",
                recommendations=[],
            )

        if now is None:
            now = datetime.now(tz=timezone.utc)

        # Make now offset-aware if naive
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        undone_sum = 0.0
        done_sum = 0.0
        contributors: list[DebtContributor] = []

        for task in tasks:
            alignment = max(task.goal_alignment, 0.0)
            leverage_frac = max(task.leverage_score, 0.0) / 10000.0

            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                created = task.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                days_undone = max((now - created).total_seconds() / 86400.0, 0.0)
                debt = alignment * leverage_frac * math.exp(_DECAY_RATE * days_undone)
                undone_sum += debt

                contributors.append(
                    DebtContributor(
                        task_id=task.id,
                        task_title=task.title,
                        leverage_score=task.leverage_score,
                        days_undone=round(days_undone, 2),
                        debt_contribution=round(debt, 4),
                        remediation=f"Complete '{task.title}' to reduce debt by {debt:.2f} units.",
                    )
                )

            elif task.status == TaskStatus.COMPLETED:
                done_sum += alignment * leverage_frac

        raw_score = (undone_sum - done_sum) * 1000.0
        clamped = max(0.0, min(raw_score, 10000.0))

        severity = PriorityDebtScore.severity_for_score(clamped)

        # Top contributors sorted by debt_contribution descending
        top_contributors = sorted(
            contributors, key=lambda c: c.debt_contribution, reverse=True
        )[:3]

        recommendations = self._build_recommendations(top_contributors, severity)
        diagnosis = await self._build_diagnosis(clamped, severity, top_contributors)

        return PriorityDebtScore(
            score=round(clamped, 2),
            severity=severity,
            top_contributors=top_contributors,
            diagnosis=diagnosis,
            recommendations=recommendations,
        )

    # ── Recommendations ──────────────────────────────────────────────

    @staticmethod
    def _build_recommendations(
        top: list[DebtContributor], severity: str
    ) -> list[str]:
        recs: list[str] = []
        if severity in ("orange", "red"):
            recs.append("Immediately prioritize top-leverage undone tasks.")
        if severity == "red":
            recs.append("Consider pausing lower-priority work to reduce debt.")
        for c in top:
            recs.append(f"Complete '{c.task_title}' (debt contribution: {c.debt_contribution:.2f}).")
        if not recs:
            recs.append("Priority debt is low. Keep up the good work!")
        return recs

    # ── LLM-assisted diagnosis ───────────────────────────────────────

    async def _build_diagnosis(
        self,
        score: float,
        severity: str,
        top: list[DebtContributor],
    ) -> str:
        if self.llm_client is None:
            return (
                f"Priority Debt Score: {score:.0f} ({severity}). "
                f"Top contributors: {', '.join(c.task_title for c in top) or 'none'}."
            )

        contributor_text = "\n".join(
            f"- {c.task_title}: leverage={c.leverage_score:.0f}, "
            f"days_undone={c.days_undone:.1f}, debt={c.debt_contribution:.2f}"
            for c in top
        )
        prompt = (
            f"Diagnose this priority debt situation:\n"
            f"Score: {score:.0f} / 10000 (severity: {severity})\n"
            f"Top contributors:\n{contributor_text}\n\n"
            f"Provide a brief, actionable diagnosis (2-3 sentences)."
        )
        try:
            return await self.llm_client.query(prompt)
        except Exception:
            logger.warning("LLM diagnosis failed, using default.")
            return f"Priority Debt Score: {score:.0f} ({severity})."
