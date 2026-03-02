"""Baseline: Vanilla developer without NorthStar.

Simulates what a typical developer using Cursor/Copilot (but no
prioritization engine) would likely do -- often picking tasks by
recency, familiarity, or what feels easiest.
"""

from __future__ import annotations

# Rankings a developer might produce without strategic prioritization.
# Common anti-patterns: picking easy/fun tasks first, ignoring blockers,
# undervaluing debt repayment.
VANILLA_RANKINGS: dict[str, list[str]] = {
    # Case 01: Developer starts with landing page (visible, fun) instead of auth
    "E-commerce MVP Launch": [
        "task-ecom-03",  # landing page (visible, fun)
        "task-ecom-04",  # SEO (quick win feeling)
        "task-ecom-05",  # analytics (interesting)
        "task-ecom-01",  # auth (complex, postponed)
        "task-ecom-02",  # payments (scary, avoided)
    ],
    # Case 02: Developer builds the dashboard first (fun UI work)
    "Binance Trading Bot Integration": [
        "task-bnc-04",  # dashboard UI (fun to build)
        "task-bnc-02",  # order execution (exciting)
        "task-bnc-01",  # API connection (boring plumbing)
        "task-bnc-05",  # backtesting (complex)
        "task-bnc-03",  # risk management (not fun)
    ],
    # Case 03: Developer picks the new shiny feature over bug fixes
    "SaaS Conflicting Goals": [
        "task-saas-02",  # premium analytics (new feature, exciting)
        "task-saas-03",  # referral program (growth hack)
        "task-saas-01",  # onboarding (tedious redesign)
        "task-saas-04",  # pricing page (seems minor)
        "task-saas-05",  # churn bug (boring fix)
    ],
    # Case 04: Developer chases new features, ignores tech debt
    "Technical Debt vs New Features": [
        "task-debt-03",  # real-time collab (headline feature)
        "task-debt-04",  # search (user-facing)
        "task-debt-05",  # file sharing (tangible)
        "task-debt-02",  # CI fix (boring infrastructure)
        "task-debt-01",  # DB refactor (painful, large)
    ],
    # Case 05: Developer keeps working on pre-pivot tasks
    "Mid-Sprint Pivot (B2C to B2B)": [
        "task-pivot-03",  # social login (was in progress)
        "task-pivot-05",  # gamification (almost done before pivot)
        "task-pivot-01",  # SSO (new, unfamiliar)
        "task-pivot-02",  # RBAC (new requirement)
        "task-pivot-04",  # audit logs (compliance, boring)
    ],
}

# Estimated PDS scores when following vanilla ordering.
# Higher values indicate more priority debt accumulated due to poor ordering.
VANILLA_PDS: dict[str, float] = {
    "E-commerce MVP Launch": 2800.0,
    "Binance Trading Bot Integration": 3500.0,
    "SaaS Conflicting Goals": 3200.0,
    "Technical Debt vs New Features": 4100.0,
    "Mid-Sprint Pivot (B2C to B2B)": 4500.0,
}
