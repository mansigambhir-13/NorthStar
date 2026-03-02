"""Strands tool definitions that wrap NorthStar's existing engines.

Each tool exposes a deterministic engine operation (ranking, scoring, gap
analysis, drift detection) as a callable that the Strands agent can invoke
during its reasoning loop.

All tools are async — Strands' ConcurrentToolExecutor handles awaiting them.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from strands import tool

logger = logging.getLogger(__name__)

# ── Shared engine state (set by NorthStarAgent before the loop runs) ─────

_state: dict[str, Any] = {}


def set_engine_state(
    *,
    config: Any = None,
    state_manager: Any = None,
    llm_client: Any = None,
) -> None:
    """Inject shared engine dependencies so tools can access them."""
    _state["config"] = config
    _state["state_manager"] = state_manager
    _state["llm_client"] = llm_client


def _sm() -> Any:
    return _state.get("state_manager")


def _llm() -> Any:
    return _state.get("llm_client")


def _cfg() -> Any:
    return _state.get("config")


# ── Tools ────────────────────────────────────────────────────────────────


@tool
async def get_goals() -> str:
    """Retrieve all project goals from the NorthStar state store.

    Returns a JSON array of goals with id, title, priority, status, and
    deadline fields.  Use this to understand what the project is trying to
    achieve before ranking tasks.
    """
    sm = _sm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})
    ctx = await sm.load_context()
    if ctx is None:
        return json.dumps({"error": "No context found. Run 'northstar init' first."})
    goals = [
        {
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "priority": g.priority,
            "status": g.status.value,
            "deadline": g.deadline,
        }
        for g in ctx.goals.goals
    ]
    return json.dumps(goals, indent=2)


@tool
async def get_tasks(status_filter: str = "all") -> str:
    """Retrieve tasks from the NorthStar state store.

    Args:
        status_filter: Filter by status — "all", "pending", "in_progress",
                       or "completed".  Defaults to "all".

    Returns a JSON array of tasks with id, title, status, leverage_score,
    goal_id, goal_alignment, impact, urgency, and effort_hours.
    """
    sm = _sm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})
    tasks = await sm.get_tasks()
    if status_filter != "all":
        tasks = [t for t in tasks if t.status.value == status_filter]
    result = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "leverage_score": round(t.leverage_score, 1),
            "goal_id": t.goal_id,
            "goal_alignment": round(t.goal_alignment, 2),
            "impact": t.impact,
            "urgency": t.urgency.value,
            "effort_hours": t.effort_hours,
        }
        for t in sorted(tasks, key=lambda t: t.leverage_score, reverse=True)
    ]
    return json.dumps(result, indent=2)


@tool
async def rank_tasks() -> str:
    """Rank all tasks by leverage score using the LeverageRanker engine.

    Computes: (goal_alignment * impact * urgency_mult * dep_unlock) / effort
    normalised to 0-10,000.  Returns the top-10 tasks with their scores and
    reasoning breakdown.
    """
    sm = _sm()
    llm = _llm()
    cfg = _cfg()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    from northstar.analysis.leverage_ranker import LeverageRanker

    ctx = await sm.load_context()
    if ctx is None:
        return json.dumps({"error": "No context. Run 'northstar init' first."})

    tasks = await sm.get_tasks()
    ranker = LeverageRanker(config=cfg.scoring, llm_client=llm)
    stack = await ranker.rank(tasks, ctx.goals)

    # Persist updated scores
    for task in stack.tasks:
        await sm.save_task(task)

    top = [
        {
            "rank": i,
            "title": t.title,
            "leverage_score": round(t.leverage_score, 1),
            "reasoning": t.reasoning,
        }
        for i, t in enumerate(stack.tasks[:10], 1)
    ]
    return json.dumps({"ranked_tasks": top, "total": len(stack.tasks)}, indent=2)


@tool
async def calculate_pds() -> str:
    """Calculate the Priority Debt Score (PDS) for the current task set.

    PDS measures accumulated cost of undone high-leverage work on a 0-10,000
    scale.  Severity bands: green (<500), yellow (500-2000), orange (2000-5000),
    red (>=5000).

    Returns PDS score, severity, top debt contributors, and recommendations.
    """
    sm = _sm()
    llm = _llm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    from northstar.analysis.priority_debt import PriorityDebtCalculator

    tasks = await sm.get_tasks()
    calc = PriorityDebtCalculator(llm_client=llm)
    pds = await calc.calculate(tasks)
    await sm.save_pds(pds)

    return json.dumps(
        {
            "score": round(pds.score, 2),
            "severity": pds.severity,
            "diagnosis": pds.diagnosis,
            "top_contributors": [
                {
                    "task": c.task_title,
                    "leverage": round(c.leverage_score, 1),
                    "days_undone": c.days_undone,
                    "debt": round(c.debt_contribution, 2),
                }
                for c in pds.top_contributors
            ],
            "recommendations": pds.recommendations,
        },
        indent=2,
    )


@tool
async def analyze_gaps() -> str:
    """Analyze goal-to-task coverage gaps.

    Identifies goals with insufficient task allocation, detects orphan tasks
    (tasks not linked to any active goal), and classifies severity of
    under-investment.

    Returns a list of gap reports per goal plus orphan task info.
    """
    sm = _sm()
    llm = _llm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    from northstar.analysis.gap_analyzer import GapAnalyzer

    ctx = await sm.load_context()
    if ctx is None:
        return json.dumps({"error": "No context. Run 'northstar init' first."})

    tasks = await sm.get_tasks()
    analyzer = GapAnalyzer(llm_client=llm)
    gaps = await analyzer.analyze(tasks, ctx.goals)

    return json.dumps(
        [
            {
                "goal": g.goal_title,
                "coverage": f"{g.coverage:.0%}",
                "severity": g.severity,
                "allocated_effort": g.allocated_effort,
                "orphan_tasks": g.orphan_tasks,
                "recommendations": g.recommendations,
            }
            for g in gaps
        ],
        indent=2,
    )


@tool
async def check_drift(current_task_id: str = "", session_minutes: float = 0.0) -> str:
    """Check if the developer is drifting from high-leverage work.

    Args:
        current_task_id: ID of the task currently being worked on.
                         If empty, uses the first in-progress task.
        session_minutes: How many minutes the developer has been on this task.

    Returns drift analysis: severity, ratio, and recommendation.
    """
    sm = _sm()
    cfg = _cfg()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    from northstar.analysis.leverage_ranker import LeverageRanker
    from northstar.analysis.models import TaskStatus
    from northstar.detection.drift_monitor import DriftMonitor

    ctx = await sm.load_context()
    if ctx is None:
        return json.dumps({"error": "No context. Run 'northstar init' first."})

    tasks = await sm.get_tasks()

    # Find current task
    current = None
    if current_task_id:
        current = next((t for t in tasks if t.id == current_task_id), None)
    if current is None:
        current = next(
            (t for t in tasks if t.status == TaskStatus.IN_PROGRESS), None
        )
    if current is None:
        return json.dumps({"status": "no_active_task", "message": "No task is currently in progress."})

    # Build priority stack
    llm = _llm()
    ranker = LeverageRanker(config=cfg.scoring, llm_client=llm)
    stack = await ranker.rank(tasks, ctx.goals)

    monitor = DriftMonitor(config=cfg.drift, state_manager=sm)
    alert = await monitor.check_drift(current, stack, session_minutes)

    if alert is None:
        return json.dumps(
            {
                "status": "aligned",
                "message": f"You're on '{current.title}' — well aligned with priorities.",
                "current_leverage": round(current.leverage_score, 1),
            }
        )

    return json.dumps(
        {
            "status": "drift_detected",
            "severity": alert.severity,
            "drift_ratio": round(alert.drift_ratio, 2),
            "current_task": alert.current_task_title,
            "current_leverage": round(alert.current_leverage, 1),
            "top_task": alert.top_task_title,
            "top_leverage": round(alert.top_leverage, 1),
            "message": alert.message,
        },
        indent=2,
    )


@tool
async def update_task_status(task_id: str, new_status: str) -> str:
    """Update a task's status.

    Args:
        task_id: The ID of the task to update.
        new_status: New status — "pending", "in_progress", "completed",
                    "deferred", or "cancelled".

    Returns confirmation or error.
    """
    sm = _sm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    from northstar.analysis.models import TaskStatus

    valid = {"pending", "in_progress", "completed", "deferred", "cancelled"}
    if new_status not in valid:
        return json.dumps({"error": f"Invalid status '{new_status}'. Must be one of: {sorted(valid)}"})

    status_enum = TaskStatus(new_status)
    await sm.update_task_status(task_id, status_enum)
    return json.dumps({"success": True, "task_id": task_id, "new_status": new_status})


@tool
async def get_pds_history(limit: int = 10) -> str:
    """Get the history of Priority Debt Score calculations.

    Args:
        limit: Maximum number of records to return (default 10).

    Returns a JSON array of PDS records with score, severity, and timestamp.
    """
    sm = _sm()
    if sm is None:
        return json.dumps({"error": "State manager not initialized"})

    history = await sm.get_pds_history()
    history = history[:limit]
    return json.dumps(
        [
            {
                "score": round(h.score, 2),
                "severity": h.severity,
                "calculated_at": h.calculated_at.isoformat() if hasattr(h.calculated_at, "isoformat") else str(h.calculated_at),
            }
            for h in history
        ],
        indent=2,
    )


# ── Tool registry for the agent ──────────────────────────────────────────

ALL_TOOLS = [
    get_goals,
    get_tasks,
    rank_tasks,
    calculate_pds,
    analyze_gaps,
    check_drift,
    update_task_status,
    get_pds_history,
]
