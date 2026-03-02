"""Case 01: E-commerce MVP launch.

Scenario: A solo developer building an e-commerce MVP. Five tasks compete
for attention. Auth is blocking payments and should rank #1; SEO and
analytics are nice-to-haves that should rank last.
"""

from __future__ import annotations

CASE_NAME: str = "E-commerce MVP Launch"

GOALS: list[dict] = [
    {
        "id": "goal-ecom-01",
        "title": "Launch MVP store",
        "priority": 1,
        "description": (
            "Ship a working e-commerce store where customers can browse "
            "products, create accounts, and complete purchases."
        ),
    },
    {
        "id": "goal-ecom-02",
        "title": "Acquire first 100 customers",
        "priority": 2,
        "description": (
            "Drive initial traffic and conversions through landing page "
            "optimization and basic marketing."
        ),
    },
]

TASKS: list[dict] = [
    {
        "id": "task-ecom-01",
        "title": "Implement user authentication",
        "goal_alignment": 0.95,
        "impact": 95,
        "urgency": "blocking",
        "effort_hours": 8.0,
        "blocks": ["task-ecom-02", "task-ecom-05"],
        "description": (
            "Build signup/login with email+password. Required before "
            "checkout can work. Blocks payments and analytics."
        ),
    },
    {
        "id": "task-ecom-02",
        "title": "Integrate Stripe payments",
        "goal_alignment": 0.90,
        "impact": 90,
        "urgency": "deadline_48h",
        "effort_hours": 12.0,
        "blocks": [],
        "description": (
            "Connect Stripe checkout flow. Cannot start until auth is done. "
            "Demo to investor in 48 hours."
        ),
    },
    {
        "id": "task-ecom-03",
        "title": "Build landing page",
        "goal_alignment": 0.70,
        "impact": 60,
        "urgency": "deadline_1w",
        "effort_hours": 4.0,
        "blocks": [],
        "description": (
            "Create a hero section, product showcase, and CTA. Needed for "
            "marketing launch next week."
        ),
    },
    {
        "id": "task-ecom-04",
        "title": "Set up SEO metadata",
        "goal_alignment": 0.40,
        "impact": 30,
        "urgency": "normal",
        "effort_hours": 2.0,
        "blocks": [],
        "description": (
            "Add meta tags, Open Graph, sitemap. Low urgency but quick win "
            "for organic traffic later."
        ),
    },
    {
        "id": "task-ecom-05",
        "title": "Add basic analytics tracking",
        "goal_alignment": 0.50,
        "impact": 40,
        "urgency": "normal",
        "effort_hours": 3.0,
        "blocks": [],
        "description": (
            "Integrate Google Analytics and basic event tracking. Requires "
            "auth to track user journeys."
        ),
    },
]

# Expert-determined optimal order: auth first (blocking + highest leverage),
# then payments (deadline + high impact), landing page, analytics, SEO last.
EXPERT_RANKING: list[str] = [
    "task-ecom-01",
    "task-ecom-02",
    "task-ecom-03",
    "task-ecom-05",
    "task-ecom-04",
]

# Expected PDS range when tasks are pending: moderate debt because auth
# is blocking and has been undone.
EXPECTED_PDS_RANGE: tuple[float, float] = (200.0, 1500.0)

DRIFT_SCENARIOS: list[dict] = [
    {
        "current_task_id": "task-ecom-04",
        "session_minutes": 45,
        "should_alert": True,
        "reason": "Working on SEO when auth is blocking payments.",
    },
    {
        "current_task_id": "task-ecom-01",
        "session_minutes": 60,
        "should_alert": False,
        "reason": "Working on the top-priority task.",
    },
    {
        "current_task_id": "task-ecom-05",
        "session_minutes": 30,
        "should_alert": True,
        "reason": "Analytics is low leverage while auth is still undone.",
    },
    {
        "current_task_id": "task-ecom-03",
        "session_minutes": 20,
        "should_alert": False,
        "reason": "Landing page is reasonable mid-priority, short session.",
    },
]
