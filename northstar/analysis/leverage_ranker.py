"""Leverage-based task ranking engine.

Computes a normalized leverage score for each task based on goal alignment,
impact, urgency, dependency unlock potential, and effort -- then returns a
PriorityStack sorted highest-leverage-first.
"""

from __future__ import annotations

import logging
from typing import Any

from northstar.analysis.models import (
    GoalSet,
    PriorityStack,
    Task,
    TaskStatus,
    UrgencyLevel,
)
from northstar.config import ScoringConfig

logger = logging.getLogger(__name__)


class LeverageRanker:
    """Rank tasks by leverage score and return a PriorityStack."""

    def __init__(self, config: ScoringConfig, llm_client: Any = None) -> None:
        self.config = config
        self.llm_client = llm_client

    # ── Urgency multiplier lookup ────────────────────────────────────

    def _urgency_multiplier(self, urgency: UrgencyLevel) -> float:
        return {
            UrgencyLevel.BLOCKING: self.config.blocking_multiplier,
            UrgencyLevel.DEADLINE_48H: self.config.deadline_48h_multiplier,
            UrgencyLevel.DEADLINE_1W: self.config.deadline_1w_multiplier,
            UrgencyLevel.NORMAL: self.config.no_deadline_multiplier,
        }.get(urgency, self.config.no_deadline_multiplier)

    # ── Raw score computation ────────────────────────────────────────

    def _raw_score(self, task: Task) -> float:
        """Compute the raw leverage score for a single task.

        Formula:
            raw = (goal_alignment * (impact / 100) * urgency_mult * dep_unlock)
                  / max(effort_hours, config.min_effort)
        """
        alignment = max(task.goal_alignment, 0.0)
        impact_frac = max(min(task.impact, 100), 0) / 100.0
        urgency_mult = self._urgency_multiplier(task.urgency)
        dep_unlock = 1.0 + (self.config.dependency_unlock_factor * len(task.blocks))
        effort = max(task.effort_hours, self.config.min_effort)

        return (alignment * impact_frac * urgency_mult * dep_unlock) / effort

    # ── LLM-assisted alignment estimation ────────────────────────────

    async def _estimate_alignment_with_llm(
        self, tasks: list[Task], goals: GoalSet
    ) -> None:
        """Use LLM to estimate goal_alignment for tasks that have alignment==0."""
        if self.llm_client is None:
            return

        zero_alignment = [t for t in tasks if t.goal_alignment == 0.0]
        if not zero_alignment:
            return

        goal_descriptions = "\n".join(
            f"- {g.id}: {g.title} ({g.description})" for g in goals.active_goals
        )

        for task in zero_alignment:
            prompt = (
                f"Given these project goals:\n{goal_descriptions}\n\n"
                f"Rate the alignment of this task to the goals on a 0.0-1.0 scale:\n"
                f"Task: {task.title}\nDescription: {task.description}\n\n"
                f"Respond with ONLY a JSON object: {{\"alignment\": <float>}}"
            )
            try:
                result = await self.llm_client.query(prompt, parse_json=True)
                if isinstance(result, dict) and "alignment" in result:
                    task.goal_alignment = max(0.0, min(1.0, float(result["alignment"])))
            except Exception:
                logger.warning("LLM alignment estimation failed for task %s", task.id)

    # ── Main ranking entry point ─────────────────────────────────────

    async def rank(self, tasks: list[Task], goals: GoalSet) -> PriorityStack:
        """Score and rank all tasks, returning a PriorityStack (descending)."""
        if not tasks:
            return PriorityStack(tasks=[])

        # Optionally fill in missing alignment via LLM
        await self._estimate_alignment_with_llm(tasks, goals)

        # Compute raw scores
        raw_scores: list[tuple[Task, float]] = []
        for task in tasks:
            raw = self._raw_score(task)
            raw_scores.append((task, raw))

        max_raw = max(score for _, score in raw_scores)

        # Normalize to 0-10000 scale
        for task, raw in raw_scores:
            if max_raw > 0:
                normalized = (raw / max_raw) * self.config.max_score
            else:
                normalized = 0.0
            task.leverage_score = min(normalized, self.config.max_score)
            task.reasoning = (
                f"alignment={task.goal_alignment:.2f} "
                f"impact={task.impact} "
                f"urgency={task.urgency.value} "
                f"blocks={len(task.blocks)} "
                f"effort={task.effort_hours}h "
                f"raw={raw:.4f} "
                f"score={task.leverage_score:.0f}"
            )

        # Sort descending by leverage_score
        ranked = sorted(tasks, key=lambda t: t.leverage_score, reverse=True)
        return PriorityStack(tasks=ranked)
