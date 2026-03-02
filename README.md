# NorthStar — The Priority Debt Engine

A CLI agent that measures **Priority Debt**: the cumulative cost of working on low-leverage tasks while high-leverage work sits undone.

## Quick Start

```bash
pip install -e ".[dev]"
northstar init --goals goals.yaml
northstar analyze
northstar status
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   NorthStar Agent                     │
├────────────┬─────────────┬────────────┬──────────────┤
│ Ingestion  │  Analysis   │ Detection  │  Reporting   │
│ Engine     │  Engine     │ Engine     │  Engine      │
├────────────┼─────────────┼────────────┼──────────────┤
│ • Codebase │ • Priority  │ • Drift    │ • Decision   │
│   scanner  │   Debt calc │   monitor  │   logger     │
│ • Context  │ • Leverage  │ • Session  │ • Reports    │
│   builder  │   ranker    │   tracker  │ • Retros     │
│ • Goal     │ • Gap       │ • Alerts   │              │
│   parser   │   analysis  │            │              │
└────────────┴─────────────┴────────────┴──────────────┘
                         │
              ┌──────────┴──────────┐
              │   State Manager     │
              │  (SQLite + JSON)    │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │ Cursor Integration  │
              └─────────────────────┘
```

## Commands

| Command | Description |
|---------|-------------|
| `northstar init` | Initialize project context |
| `northstar analyze` | Full priority analysis |
| `northstar status` | Show current PDS and top priorities |
| `northstar check` | Quick drift check |
| `northstar rank` | Add and rank a new task |
| `northstar tasks` | List all tasks with leverage scores |
| `northstar log` | View decision log |
| `northstar report` | Generate reports |
| `northstar config` | View/edit configuration |
| `northstar export` | Export all data as JSON |
| `northstar reset` | Clear all NorthStar data |

## Development

```bash
make install    # Install with dev dependencies
make test       # Run tests
make lint       # Run linting
make format     # Auto-format code
make benchmark  # Run benchmark test cases
make demo       # Run demo scenarios
```
