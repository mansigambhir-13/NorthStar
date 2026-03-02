# NorthStar for AI Product Owners

## The APO Context

AI Product Owners (APOs) orchestrate AI-driven workflows across teams. Unlike traditional product managers who manage a single backlog, APOs must:

- Define priorities that maximize leverage across the entire team
- Balance short-term delivery pressure with long-term strategic alignment
- Coordinate multiple workstreams that may have competing resource needs
- Ensure AI-accelerated execution does not outrun strategic direction
- Make prioritization decisions visible and defensible to leadership

The core challenge: when every engineer on the team can ship 5x faster with AI tools, the cost of prioritizing wrong is also 5x. Speed amplifies both good and bad prioritization decisions.

## Why APOs Need NorthStar

Traditional product management tools track throughput: tickets closed, story points delivered, velocity trends. None of these metrics answer the APO's central question: **"Is my team's work aligned with our highest-leverage goals?"**

NorthStar provides team-wide Priority Debt visibility. It transforms prioritization from a subjective, meeting-driven process into a quantitative, continuously-monitored discipline.

## Use Cases

### Sprint Planning

Before each sprint, use NorthStar to evaluate candidate work items:

```bash
# Rank all proposed sprint items against team goals
northstar rank --task "User authentication revamp" --effort high --impact high
northstar rank --task "Fix pagination bug" --effort low --impact low
northstar rank --task "Analytics dashboard" --effort medium --impact high
northstar rank --task "Update dependencies" --effort low --impact low
northstar rank --task "Onboarding flow v2" --effort medium --impact high

# View ranked list with leverage scores
northstar tasks

# Check projected PDS for different sprint compositions
northstar status
```

Instead of debating priorities in a 2-hour meeting, the APO presents a leverage-ranked backlog. Discussion shifts from "what should we do?" to "do we agree with this ranking?"

### Sprint Retrospectives

At the end of each sprint, measure prioritization quality — not just execution quality:

```bash
northstar report --format markdown
```

The report shows:
- **PDS trend** over the sprint: Did Priority Debt increase or decrease?
- **Leverage distribution**: What percentage of work was high-leverage vs. low-leverage?
- **Drift events**: How many times did the team deviate from the recommended priority order?
- **Goal alignment**: Which goals received the most and least attention?

This enables a new retrospective question: "We shipped 12 features this sprint. Were they the RIGHT 12 features?"

### Goal Alignment Auditing

As business priorities shift (new quarter, new funding round, pivoting market), verify that team work reflects the new reality:

```bash
# Update goal weights to reflect new priorities
northstar config --set goals.weights.retention=0.5
northstar config --set goals.weights.growth=0.3
northstar config --set goals.weights.infrastructure=0.2

# Re-analyze with new weights
northstar analyze

# Check if current work aligns with updated goals
northstar status
```

NorthStar immediately shows whether the current task list is aligned with the new priorities or whether significant reprioritization is needed.

### Weekly Priority Health Reports

Set up a weekly cadence to track team-level priority health:

```bash
northstar report --format markdown
```

The weekly report provides:

| Metric | This Week | Last Week | Trend |
|--------|-----------|-----------|-------|
| Priority Debt Score | 3,200 | 4,100 | Improving |
| High-leverage tasks completed | 5 | 3 | Improving |
| Low-leverage tasks completed | 8 | 12 | Improving |
| Drift events detected | 2 | 5 | Improving |
| Goal coverage | 85% | 70% | Improving |

This gives the APO a single dashboard for prioritization quality, analogous to how code coverage gives a single number for test quality.

## The APO Workflow

### Weekly Rhythm

| Day | Action | Command |
|-----|--------|---------|
| Monday | Review PDS, set weekly focus | `northstar status` |
| Tuesday-Thursday | Daily drift checks | `northstar check` |
| Friday | Generate weekly report | `northstar report` |
| Friday | Review decision log | `northstar log` |

### Quarterly Rhythm

| Event | Action | Command |
|-------|--------|---------|
| Quarter start | Update goals and weights | `northstar init --goals new_quarter.yaml` |
| Quarter mid | Audit alignment | `northstar analyze && northstar status` |
| Quarter end | Full retrospective report | `northstar report --format markdown` |

## What NorthStar Gives APOs

1. **A shared language for priority quality.** PDS is a number everyone can track.
2. **Evidence for hard conversations.** "Our PDS is 7,200 — we need to reprioritize" is more actionable than "I feel like we are working on the wrong things."
3. **Continuous monitoring, not quarterly reviews.** Priority Debt is measured daily, not discovered at the end of the quarter.
4. **AI-speed prioritization for AI-speed execution.** When the team ships faster, prioritization must keep pace.
