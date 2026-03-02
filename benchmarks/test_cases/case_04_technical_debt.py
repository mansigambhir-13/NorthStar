"""Case 04: Technical debt vs. new features.

Scenario: A codebase with accumulated tech debt competing against new
feature requests. The ranker must correctly value debt payoff that
unblocks velocity over shiny new features.
"""

from __future__ import annotations

CASE_NAME: str = "Technical Debt vs New Features"

GOALS: list[dict] = [
    {
        "id": "goal-debt-01",
        "title": "Ship v2.0 feature set",
        "priority": 1,
        "description": (
            "Deliver the planned v2.0 features: real-time collaboration, "
            "file sharing, and improved search."
        ),
    },
    {
        "id": "goal-debt-02",
        "title": "Reduce deployment failures by 80%",
        "priority": 2,
        "description": (
            "Stabilize CI/CD pipeline, fix flaky tests, improve monitoring. "
            "Current failure rate is unacceptable."
        ),
    },
]

TASKS: list[dict] = [
    {
        "id": "task-debt-01",
        "title": "Refactor database access layer",
        "goal_alignment": 0.80,
        "impact": 85,
        "urgency": "blocking",
        "effort_hours": 16.0,
        "blocks": ["task-debt-03", "task-debt-04"],
        "description": (
            "Current ORM usage causes N+1 queries and connection pool "
            "exhaustion. Blocks real-time collaboration and search."
        ),
    },
    {
        "id": "task-debt-02",
        "title": "Fix flaky CI tests",
        "goal_alignment": 0.75,
        "impact": 70,
        "urgency": "deadline_48h",
        "effort_hours": 6.0,
        "blocks": ["task-debt-05"],
        "description": (
            "12 flaky tests cause 40% of builds to fail randomly. "
            "Team cannot ship reliably. Deadline: sprint review in 48h."
        ),
    },
    {
        "id": "task-debt-03",
        "title": "Implement real-time collaboration",
        "goal_alignment": 0.90,
        "impact": 80,
        "urgency": "deadline_1w",
        "effort_hours": 24.0,
        "blocks": [],
        "description": (
            "WebSocket-based multi-user editing. The headline v2.0 feature. "
            "Requires database refactor for proper connection handling."
        ),
    },
    {
        "id": "task-debt-04",
        "title": "Build improved search",
        "goal_alignment": 0.85,
        "impact": 75,
        "urgency": "normal",
        "effort_hours": 14.0,
        "blocks": [],
        "description": (
            "Full-text search with filters. Second most-requested feature. "
            "Needs database layer to support efficient queries."
        ),
    },
    {
        "id": "task-debt-05",
        "title": "Add file sharing feature",
        "goal_alignment": 0.70,
        "impact": 60,
        "urgency": "normal",
        "effort_hours": 10.0,
        "blocks": [],
        "description": (
            "Upload and share files in conversations. Needs stable CI "
            "before merging large features."
        ),
    },
]

# Expert order: DB refactor first (blocking 2 features), fix CI (blocking
# file sharing + deadline), real-time collab, search, file sharing last.
EXPERT_RANKING: list[str] = [
    "task-debt-01",
    "task-debt-02",
    "task-debt-03",
    "task-debt-04",
    "task-debt-05",
]

EXPECTED_PDS_RANGE: tuple[float, float] = (400.0, 2200.0)

DRIFT_SCENARIOS: list[dict] = [
    {
        "current_task_id": "task-debt-03",
        "session_minutes": 60,
        "should_alert": True,
        "reason": "Building collab feature while DB layer is still broken.",
    },
    {
        "current_task_id": "task-debt-01",
        "session_minutes": 120,
        "should_alert": False,
        "reason": "DB refactor is the top blocking task, long session is fine.",
    },
    {
        "current_task_id": "task-debt-05",
        "session_minutes": 45,
        "should_alert": True,
        "reason": "File sharing while CI is still broken and DB needs refactor.",
    },
    {
        "current_task_id": "task-debt-02",
        "session_minutes": 30,
        "should_alert": False,
        "reason": "Fixing CI is the second-highest priority.",
    },
]
