# NorthStar Benchmarking Methodology

## Purpose

Benchmarking measures how well NorthStar's priority analysis matches expert human judgment. The goal is not perfection — it is consistent, measurable improvement toward expert-level prioritization quality.

## 5-Dimension Scoring

NorthStar benchmarks evaluate five dimensions:

| Dimension | Metric | What It Measures | Weight |
|-----------|--------|-----------------|--------|
| **Ranking Accuracy** | Kendall's Tau correlation | Do NorthStar's task rankings match expert rankings? | 0.30 |
| **Drift Detection** | F1 score | Does NorthStar correctly identify when work drifts from priorities? | 0.25 |
| **Completeness** | Coverage percentage | Does NorthStar analyze all relevant tasks and goals? | 0.20 |
| **Speed** | Wall-clock time | How fast does a full analysis complete? | 0.10 |
| **Actionability** | Expert rating (1-5) | Are NorthStar's recommendations specific and useful? | 0.15 |

### Dimension Details

#### Ranking Accuracy (Kendall's Tau)

Kendall's Tau measures the ordinal correlation between two ranked lists. A score of +1.0 means perfect agreement, 0.0 means no correlation, -1.0 means perfect disagreement.

```
Tau = (concordant_pairs - discordant_pairs) / total_pairs
```

We compare NorthStar's leverage-ranked task list against the expert panel's consensus ranking.

- **Target:** Tau >= 0.80 (strong agreement with experts)
- **Minimum acceptable:** Tau >= 0.60 (moderate agreement)

#### Drift Detection (F1 Score)

F1 is the harmonic mean of precision and recall for drift event detection.

- **Precision:** Of the drift events NorthStar flagged, how many were real?
- **Recall:** Of the real drift events, how many did NorthStar detect?

```
F1 = 2 * (precision * recall) / (precision + recall)
```

- **Target:** F1 >= 0.85
- **Minimum acceptable:** F1 >= 0.70

#### Completeness

Percentage of tasks and goals in the test case that NorthStar successfully ingested and scored.

- **Target:** >= 95%
- **Minimum acceptable:** >= 85%

#### Speed

Wall-clock time for a full `northstar analyze` cycle on the test case.

- **Target:** < 5 seconds (offline mode), < 30 seconds (with LLM)
- **Minimum acceptable:** < 15 seconds (offline), < 60 seconds (with LLM)

#### Actionability

Expert panel rates each recommendation on a 1-5 scale:

1. Vague, not useful
2. Somewhat relevant but not specific
3. Relevant and reasonably specific
4. Specific and actionable
5. Immediately actionable with clear next steps

- **Target:** Average >= 4.0
- **Minimum acceptable:** Average >= 3.0

## 5 Standardized Test Cases

Each test case has frozen inputs (goals, tasks, codebase snapshot, git history) to ensure reproducible results.

| # | Test Case | Description | Tasks | Goals | Key Challenge |
|---|-----------|-------------|-------|-------|---------------|
| 1 | **Greenfield startup** | New project, 3 goals, 15 tasks, no history | 15 | 3 | Pure ranking from scratch |
| 2 | **Mid-project pivot** | Existing project where goals change mid-sprint | 20 | 4 | Detecting drift after goal weight change |
| 3 | **Technical debt vs. features** | Mix of maintenance and feature work | 25 | 3 | Balancing leverage across task types |
| 4 | **Client deployment (FDE)** | Time-pressured client engagement | 18 | 5 | Ranking under tight constraints |
| 5 | **Large backlog triage** | Overwhelmed team with too many tasks | 40 | 4 | Scaling and clear top-N separation |

### Test Case Format

Each test case directory contains:

```
benchmarks/cases/01_greenfield/
  goals.yaml          # Frozen goal definitions
  tasks.yaml          # Frozen task list with descriptions
  codebase/           # Frozen codebase snapshot
  git_history.json    # Simulated git history
  expert_ranking.yaml # Expert panel consensus ranking
  expert_drift.yaml   # Expert-identified drift events
  metadata.yaml       # Test case metadata and expected ranges
```

## Baselines

NorthStar results are compared against two baselines:

### Baseline 1: Vanilla Cursor (No Prioritization)

Default task ordering as presented by a Cursor-based workflow with no priority framework. Tasks are worked in the order they appear or are requested. This represents the "no prioritization" baseline.

### Baseline 2: Human Expert Panel

A panel of 3 experienced engineers/PMs independently rank each test case's tasks. The consensus ranking (using Borda count aggregation) serves as the gold standard.

## Scoring Formula

The overall benchmark score is a weighted sum:

```
Score = (0.30 * ranking_accuracy)
      + (0.25 * drift_f1)
      + (0.20 * completeness)
      + (0.10 * speed_score)
      + (0.15 * actionability_normalized)
```

Where:
- `ranking_accuracy` = Kendall's Tau normalized to [0, 1] range: `(tau + 1) / 2`
- `drift_f1` = F1 score (already [0, 1])
- `completeness` = coverage percentage as decimal
- `speed_score` = `min(1.0, target_time / actual_time)` (faster is better, capped at 1.0)
- `actionability_normalized` = `average_rating / 5.0`

**Overall target: Score >= 0.80** (indicating >80% correlation with expert-level prioritization)

## Running Benchmarks

```bash
# Run all benchmark test cases
make benchmark

# Run a specific test case
python -m benchmarks.runner --case 01_greenfield

# Run with verbose output
python -m benchmarks.runner --verbose

# Compare against baselines
python -m benchmarks.runner --compare-baselines

# Output results as JSON
python -m benchmarks.runner --output results.json
```

## Interpreting Results

```
NorthStar Benchmark Results
============================
Test Case                  | Tau   | F1    | Compl | Speed | Action | Total
01_greenfield              | 0.85  | 0.90  | 0.97  | 1.00  | 0.84   | 0.89
02_mid_pivot               | 0.78  | 0.82  | 0.95  | 0.95  | 0.80   | 0.84
03_tech_debt_features      | 0.82  | 0.88  | 0.96  | 1.00  | 0.82   | 0.87
04_client_deployment       | 0.80  | 0.85  | 0.94  | 0.98  | 0.78   | 0.85
05_large_backlog           | 0.75  | 0.80  | 0.92  | 0.85  | 0.76   | 0.81
────────────────────────────────────────────────────────────────────────
OVERALL                    | 0.80  | 0.85  | 0.95  | 0.96  | 0.80   | 0.85
TARGET                     | 0.80  | 0.85  | 0.95  | 1.00  | 0.80   | 0.80
STATUS                     |  PASS |  PASS |  PASS |  PASS |  PASS  |  PASS
```
