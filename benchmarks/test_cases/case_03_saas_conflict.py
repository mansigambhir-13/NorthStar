"""Case 03: SaaS product with conflicting goals.

Scenario: A SaaS startup has two competing goals -- grow the user base
vs. monetize existing users. Tasks serving different goals compete,
and the ranker must balance under ambiguity.
"""

from __future__ import annotations

CASE_NAME: str = "SaaS Conflicting Goals"

GOALS: list[dict] = [
    {
        "id": "goal-saas-01",
        "title": "Grow user base to 10K MAU",
        "priority": 1,
        "description": (
            "Acquire new users through improved onboarding, free-tier "
            "features, and viral loops. Focus on top-of-funnel."
        ),
    },
    {
        "id": "goal-saas-02",
        "title": "Increase MRR to $50K",
        "priority": 1,
        "description": (
            "Monetize existing users through premium features, pricing "
            "page optimization, and reducing churn."
        ),
    },
]

TASKS: list[dict] = [
    {
        "id": "task-saas-01",
        "title": "Revamp onboarding flow",
        "goal_alignment": 0.90,
        "impact": 80,
        "urgency": "deadline_1w",
        "effort_hours": 10.0,
        "blocks": ["task-saas-03"],
        "description": (
            "Redesign the first-time user experience to reduce drop-off. "
            "Directly impacts user growth."
        ),
    },
    {
        "id": "task-saas-02",
        "title": "Build premium feature: advanced analytics",
        "goal_alignment": 0.85,
        "impact": 75,
        "urgency": "deadline_1w",
        "effort_hours": 20.0,
        "blocks": [],
        "description": (
            "The most-requested paid feature. Expected to drive 30% of "
            "new premium subscriptions."
        ),
    },
    {
        "id": "task-saas-03",
        "title": "Implement referral program",
        "goal_alignment": 0.80,
        "impact": 70,
        "urgency": "normal",
        "effort_hours": 8.0,
        "blocks": [],
        "description": (
            "Viral growth loop: invite friends, both get extended trial. "
            "Needs onboarding revamp first."
        ),
    },
    {
        "id": "task-saas-04",
        "title": "Optimize pricing page",
        "goal_alignment": 0.75,
        "impact": 65,
        "urgency": "deadline_48h",
        "effort_hours": 4.0,
        "blocks": [],
        "description": (
            "A/B test pricing tiers. Quick win for conversion rate. "
            "Investor demo requires updated pricing page in 48h."
        ),
    },
    {
        "id": "task-saas-05",
        "title": "Fix churn: broken email notifications",
        "goal_alignment": 0.70,
        "impact": 85,
        "urgency": "blocking",
        "effort_hours": 3.0,
        "blocks": [],
        "description": (
            "Email notifications have been broken for 2 weeks. Users "
            "are churning because they miss critical alerts."
        ),
    },
]

# Expert order: fix churn first (blocking bug, high impact, low effort),
# then pricing page (deadline + quick), onboarding (unlocks referral),
# referral program, premium analytics last (high effort).
EXPERT_RANKING: list[str] = [
    "task-saas-05",
    "task-saas-04",
    "task-saas-01",
    "task-saas-03",
    "task-saas-02",
]

EXPECTED_PDS_RANGE: tuple[float, float] = (500.0, 2500.0)

DRIFT_SCENARIOS: list[dict] = [
    {
        "current_task_id": "task-saas-02",
        "session_minutes": 120,
        "should_alert": True,
        "reason": "Spending 2 hours on premium analytics while churn bug is unfixed.",
    },
    {
        "current_task_id": "task-saas-05",
        "session_minutes": 30,
        "should_alert": False,
        "reason": "Fixing the highest-leverage blocking bug.",
    },
    {
        "current_task_id": "task-saas-03",
        "session_minutes": 60,
        "should_alert": True,
        "reason": "Referral program before onboarding is done (blocked).",
    },
    {
        "current_task_id": "task-saas-04",
        "session_minutes": 15,
        "should_alert": False,
        "reason": "Pricing page is high-priority quick win with deadline.",
    },
]
