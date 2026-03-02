"""Case 05: Mid-sprint pivot scenario.

Scenario: Goals change mid-sprint -- the company pivots from B2C to B2B.
Some tasks become irrelevant, new tasks appear, and the ranker must
correctly re-prioritize the entire backlog.
"""

from __future__ import annotations

CASE_NAME: str = "Mid-Sprint Pivot (B2C to B2B)"

GOALS: list[dict] = [
    {
        "id": "goal-pivot-01",
        "title": "Launch B2B enterprise offering",
        "priority": 1,
        "description": (
            "Pivot from consumer to enterprise. Need SSO, team management, "
            "audit logs, and SLA-grade infrastructure within 2 weeks."
        ),
    },
    {
        "id": "goal-pivot-02",
        "title": "Close first enterprise deal",
        "priority": 1,
        "description": (
            "Acme Corp wants a demo in 5 days. Their requirements: SSO, "
            "role-based access, data export, and 99.9% uptime SLA."
        ),
    },
]

TASKS: list[dict] = [
    {
        "id": "task-pivot-01",
        "title": "Implement SSO (SAML/OIDC)",
        "goal_alignment": 0.95,
        "impact": 95,
        "urgency": "blocking",
        "effort_hours": 12.0,
        "blocks": ["task-pivot-02", "task-pivot-04"],
        "description": (
            "Enterprise SSO is the #1 requirement from Acme Corp. "
            "Blocks team management and the demo."
        ),
    },
    {
        "id": "task-pivot-02",
        "title": "Build team management and RBAC",
        "goal_alignment": 0.90,
        "impact": 85,
        "urgency": "deadline_48h",
        "effort_hours": 10.0,
        "blocks": [],
        "description": (
            "Admin panel for user roles, team invites, permissions. "
            "Requires SSO to be done first."
        ),
    },
    {
        "id": "task-pivot-03",
        "title": "Add consumer social login (Google/Apple)",
        "goal_alignment": 0.10,
        "impact": 15,
        "urgency": "normal",
        "effort_hours": 6.0,
        "blocks": [],
        "description": (
            "Was top priority before pivot. Now nearly irrelevant for "
            "B2B. Should rank very low."
        ),
    },
    {
        "id": "task-pivot-04",
        "title": "Build audit logging",
        "goal_alignment": 0.85,
        "impact": 80,
        "urgency": "deadline_1w",
        "effort_hours": 8.0,
        "blocks": [],
        "description": (
            "Enterprise compliance requirement. Track all data access "
            "and admin actions. Needs SSO for user identity."
        ),
    },
    {
        "id": "task-pivot-05",
        "title": "Consumer gamification features",
        "goal_alignment": 0.05,
        "impact": 10,
        "urgency": "normal",
        "effort_hours": 20.0,
        "blocks": [],
        "description": (
            "Points, badges, leaderboards for consumer engagement. "
            "Completely irrelevant after B2B pivot."
        ),
    },
]

# Expert order: SSO (blocking + highest alignment), RBAC (deadline + high),
# audit logging, then the two now-irrelevant consumer tasks last.
EXPERT_RANKING: list[str] = [
    "task-pivot-01",
    "task-pivot-02",
    "task-pivot-04",
    "task-pivot-03",
    "task-pivot-05",
]

EXPECTED_PDS_RANGE: tuple[float, float] = (300.0, 1800.0)

DRIFT_SCENARIOS: list[dict] = [
    {
        "current_task_id": "task-pivot-05",
        "session_minutes": 30,
        "should_alert": True,
        "reason": "Working on consumer gamification after B2B pivot.",
    },
    {
        "current_task_id": "task-pivot-01",
        "session_minutes": 90,
        "should_alert": False,
        "reason": "SSO is the top-priority blocking task.",
    },
    {
        "current_task_id": "task-pivot-03",
        "session_minutes": 45,
        "should_alert": True,
        "reason": "Consumer social login is nearly irrelevant post-pivot.",
    },
    {
        "current_task_id": "task-pivot-02",
        "session_minutes": 25,
        "should_alert": False,
        "reason": "RBAC is the second-highest priority with a deadline.",
    },
]
