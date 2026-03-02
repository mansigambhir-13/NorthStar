"""Baseline: Human expert panel rankings.

Represents the gold-standard prioritization from a panel of experienced
engineering leads. NorthStar aims to match or exceed this quality
automatically.
"""

from __future__ import annotations

# Expert-determined optimal rankings for each test case.
# These match the EXPERT_RANKING in each case file and serve as the
# ground truth for Kendall's tau computation.
EXPERT_RANKINGS: dict[str, list[str]] = {
    "E-commerce MVP Launch": [
        "task-ecom-01",  # auth (blocking, highest leverage)
        "task-ecom-02",  # payments (deadline, high impact)
        "task-ecom-03",  # landing page (marketing deadline)
        "task-ecom-05",  # analytics (moderate value)
        "task-ecom-04",  # SEO (low urgency nice-to-have)
    ],
    "Binance Trading Bot Integration": [
        "task-bnc-01",  # API connection (blocks everything)
        "task-bnc-03",  # risk management (safety-critical)
        "task-bnc-02",  # order execution (core functionality)
        "task-bnc-05",  # backtesting (validation before live)
        "task-bnc-04",  # dashboard UI (nice-to-have)
    ],
    "SaaS Conflicting Goals": [
        "task-saas-05",  # churn bug fix (blocking, low effort, high impact)
        "task-saas-04",  # pricing page (deadline, quick win)
        "task-saas-01",  # onboarding (unlocks referral)
        "task-saas-03",  # referral program (growth)
        "task-saas-02",  # premium analytics (high effort)
    ],
    "Technical Debt vs New Features": [
        "task-debt-01",  # DB refactor (blocks 2 features)
        "task-debt-02",  # CI fix (blocks file sharing, deadline)
        "task-debt-03",  # real-time collab (headline feature)
        "task-debt-04",  # search (second feature)
        "task-debt-05",  # file sharing (lower priority)
    ],
    "Mid-Sprint Pivot (B2C to B2B)": [
        "task-pivot-01",  # SSO (blocks RBAC + audit)
        "task-pivot-02",  # RBAC (deadline, high alignment)
        "task-pivot-04",  # audit logging (enterprise requirement)
        "task-pivot-03",  # social login (now low-value)
        "task-pivot-05",  # gamification (irrelevant)
    ],
}

# PDS scores with perfect (expert) prioritization.
# When you work on the right things in the right order, PDS stays near zero.
EXPERT_PDS: dict[str, float] = {
    "E-commerce MVP Launch": 50.0,
    "Binance Trading Bot Integration": 75.0,
    "SaaS Conflicting Goals": 60.0,
    "Technical Debt vs New Features": 80.0,
    "Mid-Sprint Pivot (B2C to B2B)": 45.0,
}
