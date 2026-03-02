# Example 02: Binance Trading Bot Integration

This walkthrough shows how NorthStar handles a safety-critical system where
dependency chains and blocking tasks dominate the priority landscape.

## Scenario

You are building a trading bot that connects to the Binance API. Three goals
compete: API reliability, order execution, and risk management. The system
has hard dependencies -- you cannot execute orders without an API connector,
and you cannot enforce risk limits without an order engine.

## Step 1 -- Initialize and Analyze

```bash
northstar init --goals input.yaml --no-interactive
northstar analyze
```

## Step 2 -- View the Priority Stack

```bash
northstar status
```

Expected output (approximate scores):

```
Priority Stack
==============================================================
 #  Task                         Leverage   Urgency     Effort
--------------------------------------------------------------
 1  Binance API connector          10000    blocking      6 h
 2  Order execution engine          1620    deadline_1w  10 h
 3  Risk limit enforcement          1202    deadline_1w   8 h
 4  WebSocket market data feed      1440    deadline_1w   5 h
 5  Monitoring and alerting          408    normal        8 h
 6  Backtesting framework             71    normal       15 h
 7  Trading UI dashboard              25    normal       20 h
--------------------------------------------------------------
Priority Debt Score: 287 (green)
```

### Why the API connector dominates

The API connector scores maximum leverage because of extreme compounding:

| Factor              | Value   | Effect                               |
|---------------------|---------|--------------------------------------|
| Goal alignment      | 0.95    | Near-perfect alignment with g1       |
| Impact              | 95/100  | Critical infrastructure component    |
| Urgency             | blocking | 3.0x multiplier                     |
| Dependency unlock   | 4 tasks  | 1 + 0.5 * 4 = 3.0x multiplier      |
| Effort              | 6 h     | Moderate effort                      |

Raw score: `0.95 * 0.95 * 3.0 * 3.0 / 6 = 1.354`

This task unlocks four downstream tasks. Until it is done, more than half
the project is blocked.

### Why the UI dashboard ranks last

The dashboard has low alignment (0.30), low impact (25), no urgency
multiplier, and unblocks nothing:

Raw score: `0.30 * 0.25 * 1.0 * 1.0 / 20 = 0.00375`

That is 0.28% of the API connector's score. Building a dashboard before you
have a working trading engine is a classic priority inversion.

## Step 3 -- Dependency Chain Analysis

The tasks form a clear dependency chain:

```
API Connector (t1)
  |--- Order Engine (t2)
  |      |--- Risk Limits (t3)
  |      |--- Backtesting (t5)
  |--- WebSocket Feed (t4)
  |--- Monitoring (t7)
```

NorthStar's leverage formula naturally surfaces this chain. Tasks earlier in
the dependency graph score higher because:

1. They have the `blocking` urgency type (3x multiplier).
2. They unlock more downstream tasks (dependency_unlock_factor = 0.5 per
   blocked task).
3. Both effects multiply together.

## Step 4 -- Priority Debt with Safety Implications

In a trading system, priority debt has real financial consequences. If the
risk limit enforcement task (t3) sits undone for 5 days while you work on
the backtesting framework:

```
debt_t3 = 0.95 * (1202 / 10000) * e^(0.1 * 5)
        = 0.95 * 0.1202 * 1.649
        = 0.188
```

This is a PDS contributor flagged as **high priority** because it directly
relates to risk management. NorthStar's recommendations would include:

```
RECOMMENDATION: Complete "Risk limit enforcement" before running
live trades. Debt contribution: 0.19 units and growing.
```

## Step 5 -- Drift Detection for Safety-Critical Work

If you spend 30 minutes on the trading UI dashboard (leverage: 25) while
the API connector (leverage: 10000) remains undone:

```bash
northstar check
```

```
DRIFT ALERT (high)
You've spent 30 min on "Trading UI dashboard" (leverage: 25)
Top priority: "Binance API connector" (leverage: 10000)
Drift ratio: 0.003

Recommendation: Switch to "Binance API connector"
[continue / switch / snooze 15min]
```

A drift ratio of 0.003 means you are working on something that delivers
0.3% of the leverage of the top task. For a trading bot, this is not just
inefficient -- it is dangerous. You are building a UI for a system that
cannot yet safely execute trades.

## Key Takeaways

1. **Dependency chains create natural leverage gradients.** Tasks at the root
   of a dependency tree always score highest because they multiply the
   unlock factor.

2. **Safety-critical tasks earn high scores organically.** Risk management
   and reliability goals with high alignment and impact naturally surface
   through the scoring formula -- no special "safety" flag is needed.

3. **The UI trap is real.** Dashboards and visualization work feel productive
   but score low because they are end-of-chain, low-alignment, and high-effort.
   NorthStar quantifies this intuition.

4. **Trading bots amplify priority debt.** Unlike a web app where priority
   debt means slower user growth, in a trading system it means unmitigated
   financial risk.
