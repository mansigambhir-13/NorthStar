"""Case 02: Binance trading bot integration.

Scenario: Building an automated trading bot. API connection is the
foundation (must rank #1), followed by risk management (safety-critical),
then order execution, testing, and UI last.
"""

from __future__ import annotations

CASE_NAME: str = "Binance Trading Bot Integration"

GOALS: list[dict] = [
    {
        "id": "goal-bnc-01",
        "title": "Automated trading execution",
        "priority": 1,
        "description": (
            "Build a bot that connects to Binance API, executes trades "
            "based on signals, and manages risk automatically."
        ),
    },
    {
        "id": "goal-bnc-02",
        "title": "Risk management and safety",
        "priority": 1,
        "description": (
            "Ensure the bot cannot lose more than configured limits. "
            "Implement stop-losses, position sizing, and kill switches."
        ),
    },
]

TASKS: list[dict] = [
    {
        "id": "task-bnc-01",
        "title": "Binance API connection and auth",
        "goal_alignment": 0.95,
        "impact": 95,
        "urgency": "blocking",
        "effort_hours": 6.0,
        "blocks": ["task-bnc-02", "task-bnc-03", "task-bnc-05"],
        "description": (
            "Set up API key management, WebSocket streams, REST client. "
            "Everything else depends on a working connection."
        ),
    },
    {
        "id": "task-bnc-02",
        "title": "Order execution engine",
        "goal_alignment": 0.90,
        "impact": 85,
        "urgency": "deadline_48h",
        "effort_hours": 10.0,
        "blocks": [],
        "description": (
            "Implement market/limit order placement, order status tracking, "
            "and partial fill handling."
        ),
    },
    {
        "id": "task-bnc-03",
        "title": "Risk management module",
        "goal_alignment": 0.95,
        "impact": 95,
        "urgency": "deadline_48h",
        "effort_hours": 8.0,
        "blocks": [],
        "description": (
            "Stop-loss logic, max drawdown limits, position sizing, "
            "emergency kill switch. Safety-critical."
        ),
    },
    {
        "id": "task-bnc-04",
        "title": "Trading dashboard UI",
        "goal_alignment": 0.40,
        "impact": 35,
        "urgency": "normal",
        "effort_hours": 16.0,
        "blocks": [],
        "description": (
            "Web dashboard showing portfolio, open orders, P&L chart. "
            "Nice to have but not needed for bot operation."
        ),
    },
    {
        "id": "task-bnc-05",
        "title": "Backtesting and paper trading",
        "goal_alignment": 0.75,
        "impact": 70,
        "urgency": "deadline_1w",
        "effort_hours": 12.0,
        "blocks": [],
        "description": (
            "Run strategies against historical data. Validate before "
            "going live. Needs API connection for paper trading."
        ),
    },
]

# Expert order: API first (blocker), risk management (safety), order execution,
# backtesting, UI last (low impact, high effort).
EXPERT_RANKING: list[str] = [
    "task-bnc-01",
    "task-bnc-03",
    "task-bnc-02",
    "task-bnc-05",
    "task-bnc-04",
]

EXPECTED_PDS_RANGE: tuple[float, float] = (300.0, 2000.0)

DRIFT_SCENARIOS: list[dict] = [
    {
        "current_task_id": "task-bnc-04",
        "session_minutes": 60,
        "should_alert": True,
        "reason": "Building UI when API connection is not done yet.",
    },
    {
        "current_task_id": "task-bnc-01",
        "session_minutes": 90,
        "should_alert": False,
        "reason": "Working on the top blocking task.",
    },
    {
        "current_task_id": "task-bnc-02",
        "session_minutes": 40,
        "should_alert": True,
        "reason": "Order execution before risk management is risky.",
    },
    {
        "current_task_id": "task-bnc-03",
        "session_minutes": 30,
        "should_alert": False,
        "reason": "Risk management is the second-highest priority.",
    },
]
