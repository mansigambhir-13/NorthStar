# Example 03: SaaS Competing Priorities

This walkthrough demonstrates how NorthStar resolves the tension between
competing goals -- user growth versus revenue -- by weighting goal alignment,
impact, and urgency into a single leverage score.

## Scenario

You are building a SaaS product with two goals that pull in different
directions:

- **Goal 1 (priority 1):** User growth -- acquire 1000 users
- **Goal 2 (priority 2):** Revenue -- reach $10K MRR

These goals are not opposed, but they compete for engineering time. The
onboarding flow serves growth. The pricing page serves revenue. Some tasks
(support portal, A/B testing) serve both but with different alignment
strengths.

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
 1  Onboarding flow                10000    deadline_1w   6 h
 2  Pricing page                    6375    deadline_1w   4 h
 3  Billing integration             1913    deadline_1w  10 h
 4  Referral program                 466    normal        8 h
 5  Analytics dashboard              139    normal       12 h
 6  Customer support portal           93    normal       10 h
 7  A/B testing framework             88    normal        8 h
--------------------------------------------------------------
Priority Debt Score: 218 (green)
```

## Step 3 -- Understanding How NorthStar Resolves the Conflict

The onboarding flow ranks #1 despite both goals being active. Here is how
the scoring breaks down:

### Onboarding flow (ranked #1)

| Factor              | Value       | Effect                           |
|---------------------|-------------|----------------------------------|
| Goal alignment      | 0.95        | Near-perfect alignment with g1   |
| Impact              | 90/100      | High impact on user activation   |
| Urgency             | deadline_1w | 1.5x multiplier                 |
| Dependency unlock   | 2 tasks     | 1 + 0.5 * 2 = 2.0x multiplier   |
| Effort              | 6 h         | Moderate effort                  |

Raw score: `0.95 * 0.90 * 1.5 * 2.0 / 6 = 0.4275`

### Pricing page (ranked #2)

| Factor              | Value       | Effect                           |
|---------------------|-------------|----------------------------------|
| Goal alignment      | 0.85        | Strong alignment with g2         |
| Impact              | 80/100      | High conversion impact           |
| Urgency             | deadline_1w | 1.5x multiplier                 |
| Dependency unlock   | 1 task      | 1 + 0.5 * 1 = 1.5x multiplier   |
| Effort              | 4 h         | Low effort                       |

Raw score: `0.85 * 0.80 * 1.5 * 1.5 / 4 = 0.3825`

The onboarding flow wins by 12% even though the pricing page has lower
effort. The difference comes from:

1. **Higher alignment** (0.95 vs 0.85) -- growth is the primary goal.
2. **More dependency unlocks** (2 vs 1) -- onboarding unblocks both the
   referral program and the analytics dashboard.
3. **Higher impact** (90 vs 80) -- user activation drives everything.

## Step 4 -- The "Both Goals" Tasks

Some tasks serve both goals but are scored against their primary alignment.
This is by design:

| Task                    | Primary Goal | Alignment | Leverage |
|-------------------------|-------------|-----------|----------|
| Customer support portal | g1 (growth) | 0.40      | ~93      |
| A/B testing framework   | g1 (growth) | 0.35      | ~88      |

These rank low not because they are unimportant, but because their alignment
to any single goal is moderate. NorthStar's insight: **if a task weakly
serves two goals, it is less valuable than a task that strongly serves one.**

This prevents the common trap of working on "infrastructure" tasks that feel
like they help everything but do not move any specific needle.

## Step 5 -- Priority Debt Across Competing Goals

When goals compete, priority debt reveals which goal is being neglected.
Suppose you complete the pricing page and billing integration (g2 tasks) but
leave the onboarding flow (g1) undone for 3 days:

```
Onboarding debt = 0.95 * 1.0 * e^(0.1 * 3) = 0.95 * 1.350 = 1.28
Pricing debt    = completed, contributes -0.85 * 0.6375 = -0.54
Billing debt    = completed, contributes -0.90 * 0.1913 = -0.17
```

Net PDS increases because the highest-leverage task (onboarding) is
accumulating exponential debt faster than completed tasks reduce it.

```bash
northstar status
```

```
Priority Debt Score: 1847 (yellow)
Severity: YELLOW -- high-leverage work is being deferred

Top contributors:
  1. Onboarding flow      (debt: 1.28, days undone: 3.0)
  2. Referral program     (debt: 0.41, days undone: 3.0)
  3. Analytics dashboard  (debt: 0.08, days undone: 3.0)

Recommendation: Complete "Onboarding flow" to reduce debt by 1.28 units.
```

NorthStar does not say "stop working on revenue." It says "your growth goal
is accumulating debt faster than your revenue goal is paying it down."

## Step 6 -- Rebalancing After Completion

Once you complete the onboarding flow, the stack rebalances automatically:

```bash
northstar analyze
northstar status
```

```
Priority Stack (updated)
==============================================================
 #  Task                         Leverage   Urgency     Effort
--------------------------------------------------------------
 1  Referral program               10000    normal        8 h
 2  Analytics dashboard             2989    normal       12 h
 3  Customer support portal         1993    normal       10 h
 4  A/B testing framework           1878    normal        8 h
--------------------------------------------------------------
Priority Debt Score: 124 (green)
```

With the top growth task complete, the remaining growth tasks rerank among
themselves. The referral program (high alignment, moderate effort) takes the
top spot. Priority debt drops back to green.

## Key Takeaways

1. **NorthStar does not pick a "winning" goal.** It ranks tasks by their
   individual leverage, letting the math resolve goal conflicts naturally.

2. **Strong single-goal alignment beats weak multi-goal alignment.** A task
   that strongly serves one goal outranks a task that weakly serves two.
   This prevents the "generalist infrastructure" trap.

3. **Priority debt reveals goal neglect.** When you focus exclusively on one
   goal, debt from the other goal's high-leverage tasks grows exponentially,
   creating a natural pressure to rebalance.

4. **The stack rebalances after completions.** Finishing top tasks causes
   the remaining tasks to re-normalize, surfacing the next most impactful
   work regardless of which goal it serves.

5. **Competing priorities are normal.** NorthStar does not force you to
   choose between growth and revenue. It quantifies the tradeoff so you can
   make informed decisions instead of gut-feel context-switching.
