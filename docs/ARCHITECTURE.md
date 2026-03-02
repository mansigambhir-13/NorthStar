# NorthStar Architecture

## System Overview

```
                         ┌─────────────────────┐
                         │     CLI (Typer)      │
                         │  asyncio.run() bridge│
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │    NorthStar Agent   │
                         │   (Orchestrator)     │
                         └──────────┬──────────┘
                                    │
          ┌─────────────┬───────────┼───────────┬──────────────┐
          │             │           │           │              │
  ┌───────▼──────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌──────▼──────┐
  │  Ingestion   │ │Analysis │ │Detection│ │Reporting│ │   LLM       │
  │  Engine      │ │ Engine  │ │ Engine  │ │ Engine  │ │  Client     │
  ├──────────────┤ ├─────────┤ ├─────────┤ ├─────────┤ ├─────────────┤
  │• Codebase    │ │• Priority│ │• Drift  │ │• Decision│ │• OpenAI /  │
  │  scanner     │ │  Debt    │ │  monitor│ │  logger  │ │  Anthropic │
  │• Context     │ │  calc    │ │• Session│ │• Reports │ │• NullLLM   │
  │  builder     │ │• Leverage│ │  tracker│ │• Retros  │ │  Client    │
  │• Goal parser │ │  ranker  │ │• Alerts │ │          │ │  (offline) │
  │• tree-sitter │ │• Gap     │ │         │ │          │ │• Hash cache│
  │  + regex     │ │  analysis│ │         │ │          │ │            │
  └──────┬───────┘ └────┬────┘ └────┬────┘ └────┬────┘ └──────┬─────┘
         │              │           │           │              │
         └──────────────┴───────────┼───────────┴──────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   State Manager     │
                         ├─────────────────────┤
                         │ SQLite (WAL mode)   │
                         │ + JSON persistence  │
                         └─────────────────────┘
```

## The Four Engines

### 1. Ingestion Engine

Responsible for gathering all inputs needed for priority analysis.

- **Codebase Scanner:** Walks the project directory, identifies source files, extracts structure using tree-sitter AST parsing with regex fallback for unsupported languages.
- **Context Builder:** Aggregates codebase structure, recent git history, open tasks, and current goals into a unified context object.
- **Goal Parser:** Reads goal definitions from YAML configuration files. Goals include names, descriptions, and relative weights.

### 2. Analysis Engine

The core scoring and ranking logic.

- **Priority Debt Calculator:** Computes the Priority Debt Score (PDS) based on the gap between current work allocation and optimal leverage-weighted allocation.
- **Leverage Ranker:** Scores each task on a 0-10000 normalized scale based on goal alignment, effort-to-impact ratio, dependency position, and time sensitivity.
- **Gap Analysis:** Identifies which goals are underserved by the current task list and which are over-served relative to their weight.

### 3. Detection Engine

Monitors for priority drift over time.

- **Drift Monitor:** Compares actual work patterns (from git commits, task completions) against the recommended priority order. Flags when work diverges beyond configured thresholds.
- **Session Tracker:** Records work sessions to build a history of prioritization decisions.
- **Alerts:** Generates alerts when PDS exceeds thresholds or when drift is detected.

### 4. Reporting Engine

Produces human-readable outputs.

- **Decision Logger:** Records every prioritization decision with timestamp, context, and rationale.
- **Reports:** Generates markdown reports summarizing PDS trends, task completion by leverage tier, goal coverage, and drift events.
- **Retrospectives:** Produces end-of-period analysis comparing planned vs. actual priority allocation.

## State Manager

The State Manager is the single persistence layer. No engine accesses the database directly.

### Dual Persistence Strategy

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Structured data | SQLite with WAL mode | Tasks, scores, sessions, metrics — queryable data |
| Context data | JSON files | Goals, configuration, analysis snapshots — human-readable data |

**Why both?** SQLite provides fast queries, concurrent read access, and atomic transactions for operational data. JSON provides human-readable, git-friendly storage for configuration and context that users may want to inspect or version-control.

**WAL mode** (Write-Ahead Logging) enables concurrent readers during writes, which matters for async operations where analysis and drift detection may run simultaneously.

## Data Flow

```
init           scan           build context     rank tasks
 │               │                │                │
 ▼               ▼                ▼                ▼
Goals ──► Codebase ──► Unified ──► Scored ──► PDS
 YAML      structure    context     tasks      calculated
                                                  │
                                                  ▼
                                           monitor drift
                                                  │
                                                  ▼
                                             report
```

1. **init:** User provides goals as YAML. State Manager stores them.
2. **scan:** Ingestion Engine walks codebase, parses structure.
3. **build context:** Context Builder merges codebase data, goals, existing tasks, and git history.
4. **rank tasks:** Analysis Engine scores all tasks using leverage formula. LLM Client may be consulted for nuanced scoring.
5. **calculate PDS:** Priority Debt Score is computed from the gap between current and optimal allocation.
6. **monitor drift:** Detection Engine compares ongoing work against recommended priorities.
7. **report:** Reporting Engine produces summaries, logs, and alerts.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Async throughout | All I/O operations use async/await. Codebase scanning, LLM calls, and database access are all non-blocking. |
| NullLLMClient for offline | A drop-in replacement that returns deterministic, rule-based responses. Enables testing without API costs and operation in air-gapped environments. |
| tree-sitter with regex fallback | tree-sitter provides accurate AST parsing for supported languages. For unsupported languages, regex-based extraction provides best-effort structure analysis. Graceful degradation over hard failure. |
| asyncio.run() at CLI boundary | Typer commands are synchronous. Each command calls `asyncio.run(async_handler())` to bridge into the async domain. This is the standard pattern that avoids nested event loop issues. |
| Normalized scores (0-10000) | All leverage scores use a 0-10000 integer scale. Intuitive, comparable across projects, avoids floating-point display issues. |
| Hash-based LLM caching | LLM responses are cached by hashing the input prompt. Identical analyses skip the API call entirely, reducing cost and latency. |

## File Structure

```
northstar/
  __init__.py
  cli.py              # Typer CLI commands, asyncio.run() bridge
  agent.py             # Orchestrator — coordinates all engines
  models.py            # Pydantic v2 data models
  config.py            # Configuration loading and defaults
  state.py             # State Manager (SQLite + JSON)
  engines/
    __init__.py
    ingestion.py       # Codebase scanner, context builder, goal parser
    analysis.py        # PDS calculator, leverage ranker, gap analysis
    detection.py       # Drift monitor, session tracker, alerts
    reporting.py       # Decision logger, reports, retrospectives
  llm/
    __init__.py
    client.py          # LLM client abstraction
    null_client.py     # NullLLMClient for offline/testing
    cache.py           # Hash-based response cache
  parsers/
    __init__.py
    tree_sitter.py     # tree-sitter AST parsing
    regex_fallback.py  # Regex-based structure extraction
tests/
  __init__.py
  unit/                # Unit tests (NullLLMClient, tmp_path)
  integration/         # Integration tests
  fixtures/            # Test data and frozen inputs
benchmarks/
  cases/               # 5 standardized benchmark test cases
  runner.py            # Benchmark execution harness
  baselines/           # Human expert and vanilla Cursor baselines
docs/                  # Documentation (this directory)
examples/              # Example configurations and demo scenarios
```

## Configuration Hierarchy

Configuration values are resolved in this order (later overrides earlier):

1. **Built-in defaults** — sensible defaults for all settings
2. **YAML config file** — `northstar.yaml` or `~/.northstar/config.yaml`
3. **Environment variables** — `NORTHSTAR_*` prefix (e.g., `NORTHSTAR_LLM_MODEL`)
4. **CLI flags** — command-line arguments override everything

```
Defaults  ──►  YAML  ──►  Env Vars  ──►  CLI Flags
(lowest)                                  (highest)
```
