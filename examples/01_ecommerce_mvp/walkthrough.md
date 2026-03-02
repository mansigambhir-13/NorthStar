# Example 01: E-Commerce MVP

This walkthrough demonstrates NorthStar's core value proposition: surfacing the
highest-leverage work and detecting when you drift away from it.

## Scenario

You are building an e-commerce MVP. Your primary goal is to ship to your first
10 users. You have seven tasks competing for your attention, ranging from
critical blockers (authentication) to nice-to-haves (SEO optimization).

## Step 1 -- Initialize

```bash
northstar init --goals input.yaml --no-interactive
```

NorthStar ingests the two goals and seven tasks, scans the codebase for context,
and persists everything under `.northstar/`.

## Step 2 -- Run Analysis

```bash
northstar analyze
```

NorthStar computes a leverage score for every task using the formula:

```
raw = (goal_alignment * (impact / 100) * urgency_multiplier * dep_unlock)
      / max(effort_hours, min_effort)
```

Scores are then normalized to a 0--10000 scale.

## Step 3 -- View the Priority Stack

```bash
northstar status
```

Expected output (approximate scores):

```
Priority Stack
==============================================================
 #  Task                         Leverage   Urgency     Effort
--------------------------------------------------------------
 1  Build user authentication      10000    blocking      4 h
 2  Stripe payment integration      1432    deadline_1w   8 h
 3  Shopping cart                   1359    deadline_1w   5 h
 4  Product catalog page             663    normal        6 h
 5  Admin dashboard                   80    normal       10 h
 6  Email notification system         125   normal        4 h
 7  SEO optimization                   89   normal        3 h
--------------------------------------------------------------
Priority Debt Score: 342 (green)
```

### Why authentication ranks number 1

Authentication earns the maximum score because of three compounding factors:

| Factor              | Value | Effect                              |
|---------------------|-------|-------------------------------------|
| Goal alignment      | 0.95  | Nearly perfect alignment with g1    |
| Urgency             | blocking | 3x multiplier (highest tier)     |
| Dependency unlock   | 3 tasks | 1 + 0.5 * 3 = 2.5x multiplier    |
| Effort              | 4 h   | Moderate -- does not dilute score   |

Combined raw score: `0.95 * 0.90 * 3.0 * 2.5 / 4 = 1.603`

No other task comes close. The blocking urgency and the fact that three
downstream tasks are waiting on it create enormous leverage.

### Why SEO ranks last

SEO has low alignment (0.20), low impact (20), no urgency multiplier (1.0x),
and unblocks nothing (dep_unlock = 1.0):

Raw score: `0.20 * 0.20 * 1.0 * 1.0 / 3 = 0.0133`

This is less than 1% of authentication's raw score. NorthStar correctly
identifies SEO as a distraction during the MVP phase.

## Step 4 -- Priority Debt in Action

Suppose you ignore the priority stack and start working on SEO optimization
instead of authentication. After a day passes with authentication still
undone, run:

```bash
northstar status
```

The Priority Debt Score climbs because high-leverage tasks are accumulating
time-based penalties:

```
PDS = alignment * (leverage / 10000) * e^(0.1 * days_undone)
```

For authentication after 1 day undone:

```
debt = 0.95 * 1.0 * e^(0.1 * 1) = 0.95 * 1.105 = 1.05
```

The exponential term means debt accelerates. After 7 days it would be:

```
debt = 0.95 * 1.0 * e^(0.7) = 0.95 * 2.014 = 1.91
```

The PDS severity escalates from green to yellow to orange as days pass
without completing the top-leverage work.

## Step 5 -- Drift Detection

Start a session working on the admin dashboard (ranked #5):

```bash
northstar check
```

After 45 minutes on a low-leverage task, NorthStar fires a **medium** drift
alert:

```
DRIFT ALERT (medium)
You've spent 45 min on "Admin dashboard" (leverage: 80)
Top priority: "Build user authentication" (leverage: 10000)
Drift ratio: 0.008

Recommendation: Switch to "Build user authentication"
[continue / switch / snooze 15min]
```

The drift ratio (0.008) indicates you are working on something that delivers
less than 1% of the leverage of the top-ranked task. This is a clear signal
to switch.

## Key Takeaways

1. **Leverage scoring is multiplicative.** Blocking urgency, dependency
   unlocks, and high alignment compound to create massive score differences.

2. **Priority Debt grows exponentially.** Ignoring high-leverage work does
   not just delay it -- the cost accelerates over time.

3. **Drift detection is ratio-based.** It compares what you are working on
   against what you should be working on, not just absolute scores.

4. **Low-alignment tasks are deprioritized automatically.** SEO and admin
   dashboards are legitimate work, but NorthStar correctly identifies them
   as premature during the MVP phase.
