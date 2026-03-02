# NorthStar for Forward Deployed Engineers

## The FDE Context

Forward Deployed Engineers (FDEs) operate in ambiguous, undefined environments. Unlike product engineers with clear backlogs and well-scoped tickets, FDEs are dropped into client engagements where:

- Requirements are vague or contradictory
- Stakeholders have competing priorities
- Timelines are aggressive and non-negotiable
- The "right thing to build" changes weekly
- There is no product manager making prioritization calls

FDEs must independently decide what to build first, what to defer, and what to ignore entirely. These decisions are made under time pressure with incomplete information. The cost of getting them wrong is not just wasted engineering time — it is a failed client engagement.

## Why FDEs Need NorthStar

In a typical client deployment, an FDE faces dozens of potential work items in the first week alone: integration requests, bug reports, feature asks, infrastructure concerns, data migration needs. Without a systematic framework, prioritization defaults to:

- **Loudest stakeholder wins** — whoever emails most gets their feature first
- **Easiest task wins** — small wins feel productive but may be low-leverage
- **Most recent request wins** — recency bias disguised as responsiveness

NorthStar replaces gut-feel prioritization with a quantitative leverage framework. It does not remove the FDE's judgment — it augments it with data.

## Use Cases

### Client Deployment Prioritization

When starting a new client engagement:

```bash
northstar init --goals client_goals.yaml
northstar analyze
northstar status
```

NorthStar ingests the client's stated goals, scans the current codebase and task landscape, and produces a ranked list of work items by leverage score. The FDE can immediately see which tasks will move the needle most.

### Feature Triage Under Time Pressure

When a client requests five features and you have capacity for two:

```bash
northstar rank --task "SSO integration" --effort medium --impact high
northstar rank --task "CSV export" --effort low --impact low
northstar rank --task "Dashboard redesign" --effort high --impact high
northstar rank --task "Email notifications" --effort medium --impact medium
northstar rank --task "API rate limiting" --effort low --impact medium
northstar tasks
```

NorthStar scores each task against the client's goals and shows which two deliver maximum leverage. The FDE can present a data-backed recommendation instead of a subjective opinion.

### Daily Drift Detection

At the start of each day:

```bash
northstar check
```

NorthStar compares what you worked on yesterday against what the leverage model recommends. If you spent 6 hours on a low-leverage task while a high-leverage task sat idle, NorthStar flags the drift. This is not a judgment — it is a course correction signal.

### Weekly Client Reports

At the end of each week:

```bash
northstar report --format markdown
```

Generate a report showing: tasks completed (with leverage scores), Priority Debt trend over the week, alignment between work done and client goals. This gives the client visibility into not just what was built, but why it was prioritized.

## How to Use: The FDE Workflow

### Day 0: Initialize

```bash
# Define client goals in YAML
cat > client_goals.yaml << EOF
goals:
  - name: "Reduce onboarding time"
    weight: 0.4
    description: "New users should be productive within 30 minutes"
  - name: "Improve data reliability"
    weight: 0.35
    description: "Zero data loss, <1% error rate on imports"
  - name: "Enable self-service"
    weight: 0.25
    description: "Reduce support tickets by 50%"
EOF

northstar init --goals client_goals.yaml
```

### Daily: Analyze and Check

```bash
northstar analyze   # Full analysis (run when tasks change)
northstar check     # Quick drift check (run daily)
northstar status    # View current PDS and top priorities
```

### Weekly: Report and Adjust

```bash
northstar report          # Generate weekly summary
northstar log             # Review decision history
northstar config --show   # Verify goal weights still match client priorities
```

## What NorthStar Does NOT Do

- It does not replace FDE judgment. It informs it.
- It does not talk to clients. The FDE interprets and communicates.
- It does not guarantee correct prioritization. It reduces the probability of systematic error.
- It does not require an LLM in production. NullLLMClient enables fully offline operation for sensitive client environments.
