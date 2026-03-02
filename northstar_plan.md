# NorthStar: The Priority Debt Engine

## An End-to-End Plan for a Quest Submission Targeting Both FDE & APO Roles

---

## Part 1: The Innovative Problem — Priority Debt

### The Paradox Nobody's Talking About

In the AI-native era, execution is nearly free. Cursor can scaffold an MVP in hours. Claude can generate production code in minutes. But this has created a devastating paradox that nobody is addressing:

**Teams are building MORE low-value features FASTER than ever before.**

When building is effortless, the bottleneck silently shifts from *"can we build it?"* to *"should we build it?"* — and most teams never notice the shift. They celebrate shipping velocity while their products drift toward irrelevance.

### Introducing: Priority Debt

**Priority Debt** is a new concept — the cumulative cost of working on low-leverage tasks while high-leverage tasks remain undone.

| Concept | Definition | Consequence |
|---------|-----------|-------------|
| **Technical Debt** | Shortcuts in code quality | System degrades over time |
| **Design Debt** | Inconsistencies in UX | User experience fragments |
| **Priority Debt** | Misallocation of effort to low-leverage work | Product loses market relevance |

Priority Debt is the most dangerous because:

1. **It's invisible** — There's no linter for bad priorities. Code works perfectly; it just doesn't matter.
2. **AI accelerates it** — The faster you can build, the faster you accumulate priority debt if your direction is wrong.
3. **It compounds silently** — Every low-leverage feature you ship is a high-leverage feature you didn't ship. The opportunity cost compounds.
4. **It kills companies** — Teams that shipped 10x more features but in the wrong direction lose to teams that shipped 3 features that mattered.

### Why This Is Problem #1

The job posting says their #1 hiring criterion is **Priority Definition Ability**. They say:

> "Businesses that simply consume this productivity gap will become low-value operations."

This is exactly what Priority Debt describes. The productivity gap from AI is real — but without a system to ensure that productivity is directed at the right things, it's wasted energy.

**No tool exists today that measures, tracks, or reduces Priority Debt.** Every AI coding tool makes you faster. None of them make you more directionally correct.

NorthStar fixes this.

---

## Part 2: The Solution — NorthStar Agent

### What Is NorthStar?

NorthStar is a **Cursor-native AI agent** that acts as a real-time priority compass for AI-native development teams. It doesn't write code for you — it ensures the code you write matters.

**Core Concept**: NorthStar maintains persistent awareness of your project's strategic context (goals, user signals, technical debt landscape, deadlines) and continuously evaluates whether your current work is the highest-leverage action available.

### The 5 Capabilities

#### 1. Context Ingestion Engine
- Scans the entire codebase and extracts structural understanding
- Reads README, docs, issue trackers, and config files
- Builds a "Strategic Context Map" — a living model of what this project is, who it serves, and what matters most
- Accepts manual inputs: business goals, OKRs, user feedback themes, deadlines

#### 2. Priority Debt Calculator
- Quantifies priority debt as a single score (0-10,000)
- Analyzes current work-in-progress vs. defined strategic goals
- Detects "drift" — when active development diverges from high-leverage objectives
- Tracks debt over time (session by session, day by day)

#### 3. Leverage Ranker
- Takes all pending/possible tasks and ranks them by leverage
- Leverage Score = (Impact on Core Goal × Urgency × Dependency Unlock Potential) / (Estimated Effort)
- Surfaces the "Next Best Action" — the single highest-leverage thing you could do right now
- Re-ranks dynamically as context changes

#### 4. Drift Detector (Real-Time)
- Monitors your active Cursor session
- If you've been working on something for 30+ minutes that scores below the top 3 priority tasks, it flags it
- Doesn't block you — provides a gentle "priority check" with reasoning
- Example: *"You've spent 45 minutes optimizing the login animation. Meanwhile, the payment integration (Leverage Score: 8,750) remains unstarted. The animation scores 1,200. Continue?"*

#### 5. Decision Logger
- Records every priority decision and its reasoning
- Creates an auditable trail of "why we built what we built"
- Enables teams to do "Priority Retrospectives" — reviewing whether past priority decisions were correct
- Generates weekly Priority Debt Reports

### How NorthStar Works Inside Cursor

```
Developer opens Cursor → NorthStar loads Strategic Context Map

Developer starts working → NorthStar monitors activity passively

If (current_work.leverage_score < top_3_average):
    NorthStar triggers a Priority Check (non-blocking notification)
    Shows: Current task score vs. top alternatives
    Developer can: Acknowledge & Continue | Switch | Defer Current

Every session end → NorthStar updates Priority Debt Score
Every week → NorthStar generates Priority Debt Report
```

### Why This Is Innovative

| Existing Tools | What They Do | What They Miss |
|---------------|-------------|---------------|
| Cursor / Copilot | Write code faster | Don't know if the code matters |
| Jira / Linear | Track tasks | Don't rank by leverage |
| OKR tools | Set goals | Don't connect goals to daily work |
| Code quality tools | Measure tech debt | Ignore priority debt |

**NorthStar is the first tool that bridges the gap between strategic intent and daily execution in AI-native workflows.**

---

## Part 3: Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     NorthStar Agent                         │
├─────────────┬──────────────┬──────────────┬────────────────┤
│  Ingestion  │   Analysis   │  Detection   │   Reporting    │
│   Engine    │    Engine    │   Engine     │    Engine      │
├─────────────┼──────────────┼──────────────┼────────────────┤
│ • Codebase  │ • Priority   │ • Real-time  │ • Decision     │
│   scanner   │   Debt calc  │   drift      │   logger       │
│ • Context   │ • Leverage   │   monitor    │ • Weekly       │
│   builder   │   ranker     │ • Session    │   reports      │
│ • Goal      │ • Gap        │   tracker    │ • Priority     │
│   parser    │   analysis   │ • Alert      │   retrospect   │
│             │              │   system     │                │
└─────────────┴──────────────┴──────────────┴────────────────┘
         │              │              │              │
         └──────────────┴──────┬───────┴──────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   State Manager     │
                    │  (Persistent JSON)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Cursor Integration │
                    │  (.cursorrules +    │
                    │   CLI commands)     │
                    └─────────────────────┘
```

### Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Core Agent | Python 3.11+ (async) | Fast prototyping, rich AI ecosystem |
| LLM Integration | Claude API (via Anthropic SDK) | Best reasoning for priority analysis |
| State Persistence | Local JSON + SQLite | No external dependencies, Cursor-friendly |
| Codebase Analysis | Tree-sitter + custom AST walker | Language-agnostic code understanding |
| Cursor Integration | .cursorrules + CLI tool | Native Cursor workflow |
| Scoring Engine | Custom Python (NumPy for math) | Reproducible, auditable calculations |
| Reporting | Markdown generation | Universal, version-controllable |
| Testing/Benchmarks | pytest + custom DeepEval harness | Rigorous, reproducible evaluation |

### File Structure

```
northstar/
├── .cursorrules                    # Cursor AI behavior configuration
├── .env.example                    # Template (no real keys)
├── README.md                       # Comprehensive documentation
├── Makefile                        # One-command setup & run
├── Dockerfile                      # Production containerization
├── requirements.txt                # Python dependencies
├── setup.py                        # Package setup
│
├── northstar/                      # Core package
│   ├── __init__.py
│   ├── cli.py                      # CLI entry point
│   ├── config.py                   # Configuration management
│   │
│   ├── ingestion/                  # Context Ingestion Engine
│   │   ├── __init__.py
│   │   ├── codebase_scanner.py     # Scans repo structure & code
│   │   ├── context_builder.py      # Builds Strategic Context Map
│   │   ├── goal_parser.py          # Parses business goals/OKRs
│   │   └── doc_reader.py           # Reads README, docs, issues
│   │
│   ├── analysis/                   # Analysis Engine
│   │   ├── __init__.py
│   │   ├── priority_debt.py        # Priority Debt Calculator
│   │   ├── leverage_ranker.py      # Task leverage scoring
│   │   ├── gap_analyzer.py         # Goal-to-work gap analysis
│   │   └── models.py               # Data models (Task, Goal, Score)
│   │
│   ├── detection/                  # Real-Time Detection Engine
│   │   ├── __init__.py
│   │   ├── drift_monitor.py        # Monitors active session drift
│   │   ├── session_tracker.py      # Tracks what developer is working on
│   │   └── alerting.py             # Non-blocking alert system
│   │
│   ├── reporting/                  # Reporting Engine
│   │   ├── __init__.py
│   │   ├── decision_logger.py      # Logs priority decisions
│   │   ├── debt_report.py          # Generates Priority Debt Reports
│   │   └── retrospective.py        # Priority retrospective analysis
│   │
│   ├── state/                      # Persistent State
│   │   ├── __init__.py
│   │   ├── manager.py              # State persistence (JSON + SQLite)
│   │   └── schema.py               # State data models
│   │
│   └── integrations/               # External Integrations
│       ├── __init__.py
│       ├── cursor.py               # Cursor-specific integration
│       ├── llm.py                  # Claude/LLM API wrapper
│       └── git.py                  # Git history analysis
│
├── benchmarks/                     # Scoring & Comparison System
│   ├── scoring/
│   │   ├── methodology.py          # 1-10,000 scoring framework
│   │   ├── dimensions.py           # Individual scoring dimensions
│   │   └── calculator.py           # Composite score calculator
│   ├── test_cases/
│   │   ├── case_01_ecommerce.py    # E-commerce MVP prioritization
│   │   ├── case_02_api_integration.py  # API integration priorities
│   │   ├── case_03_startup_mvp.py  # Startup MVP scope definition
│   │   ├── case_04_tech_debt.py    # Tech debt vs feature balance
│   │   └── case_05_pivot.py        # Priority shift during pivot
│   ├── baselines/
│   │   ├── vanilla_cursor/         # Same tasks with plain Cursor+Claude
│   │   └── human_expert/           # Same tasks with human PM decisions
│   └── results/
│       ├── comparison_report.md    # Side-by-side analysis
│       └── raw_data/               # Raw scoring data
│
├── examples/                       # Demo Scenarios
│   ├── 01_ecommerce_mvp/           # WhatsApp bot prioritization
│   │   ├── input.yaml              # Business context input
│   │   ├── output/                 # NorthStar's prioritized output
│   │   └── walkthrough.md          # Step-by-step demonstration
│   ├── 02_binance_integration/     # Binance API integration priorities
│   │   ├── input.yaml
│   │   ├── output/
│   │   └── walkthrough.md
│   └── 03_saas_product/            # SaaS product priority management
│       ├── input.yaml
│       ├── output/
│       └── walkthrough.md
│
├── docs/                           # Quest Documentation
│   ├── PROBLEM_STATEMENT.md        # Why Priority Debt, Why #1
│   ├── FDE_PERSPECTIVE.md          # Technical depth showcase
│   ├── APO_PERSPECTIVE.md          # Strategic orchestration showcase
│   ├── ARCHITECTURE.md             # Full architecture deep-dive
│   ├── BENCHMARKS.md               # Complete scoring methodology
│   └── DESIGN_DECISIONS.md         # Why every choice was made
│
└── tests/                          # Test Suite
    ├── unit/
    │   ├── test_priority_debt.py
    │   ├── test_leverage_ranker.py
    │   └── test_context_builder.py
    ├── integration/
    │   ├── test_full_pipeline.py
    │   └── test_cursor_integration.py
    └── conftest.py
```

---

## Part 4: Core Algorithms

### 4.1 Priority Debt Score (PDS)

```
PDS = Σ (Weight_i × UndoneLeverage_i × TimeDecay_i) - Σ (Weight_j × DoneLeverage_j)

Where:
  UndoneLeverage_i = Impact × Urgency × DependencyUnlock for each undone high-leverage task
  DoneLeverage_j   = Impact × Urgency × DependencyUnlock for each completed task
  TimeDecay_i      = e^(0.1 × days_undone) — debt grows exponentially
  Weight           = Alignment to core strategic goal (0-1)

Scale: 0 (perfect focus) to 10,000 (catastrophic misallocation)

Interpretation:
  0 - 500       → Green: Excellent focus. Ship with confidence.
  500 - 2,000   → Yellow: Some drift. Review priorities this week.
  2,000 - 5,000 → Orange: Significant debt. Stop and re-prioritize.
  5,000 - 10,000→ Red: Critical. Major strategic misalignment.
```

### 4.2 Leverage Score (per task)

```
LeverageScore = (GoalAlignment × Impact × UrgencyMultiplier × DependencyUnlock) / EffortEstimate

Where:
  GoalAlignment     = How directly this task serves the #1 strategic goal (0-1)
  Impact            = Estimated user/business impact (1-100)
  UrgencyMultiplier = Time sensitivity factor:
                      - Blocking others: 3x
                      - Deadline within 48h: 2.5x
                      - Deadline within 1 week: 1.5x
                      - No deadline: 1x
  DependencyUnlock  = Number of other tasks this unblocks (1 + 0.5 × count)
  EffortEstimate    = Estimated hours (from LLM analysis + historical data)

Scale: 0 - 10,000 (normalized)
```

### 4.3 Drift Detection Algorithm

```python
# Pseudocode
def check_drift(current_activity, priority_stack, session_duration):
    current_leverage = calculate_leverage(current_activity)
    top_3_average = mean(priority_stack[:3].leverage_scores)
    
    drift_ratio = current_leverage / top_3_average
    
    if drift_ratio < 0.3 and session_duration > 30_minutes:
        return DriftAlert(
            severity="high",
            message=f"Current task scores {current_leverage}. "
                    f"Top priority scores {priority_stack[0].leverage_score}. "
                    f"Drift ratio: {drift_ratio:.1%}",
            suggestion=priority_stack[0]
        )
    elif drift_ratio < 0.6 and session_duration > 45_minutes:
        return DriftAlert(severity="medium", ...)
    
    return None  # No drift detected
```

---

## Part 5: The Scoring System (1-10,000) — Benchmark Framework

### 5 Dimensions, 5 Test Cases

```
NorthStar Score = Σ across 5 dimensions:

┌────────────────────────────┬────────┬─────────────────────────────────────┐
│ Dimension                  │ Max    │ Measurement Method                  │
├────────────────────────────┼────────┼─────────────────────────────────────┤
│ Priority Accuracy          │ 3,000  │ Does NorthStar rank tasks the same  │
│                            │        │ way as a panel of 3 human experts?  │
│                            │        │ Kendall's Tau correlation × 3000    │
├────────────────────────────┼────────┼─────────────────────────────────────┤
│ Drift Detection Precision  │ 2,500  │ Of 20 simulated sessions with       │
│                            │        │ known drift/no-drift, how many      │
│                            │        │ does NorthStar correctly classify?  │
│                            │        │ F1-score × 2500                    │
├────────────────────────────┼────────┼─────────────────────────────────────┤
│ Context Completeness       │ 2,000  │ Given a codebase, how many of 15   │
│                            │        │ predefined strategic signals does   │
│                            │        │ NorthStar correctly extract?        │
│                            │        │ (correct / 15) × 2000              │
├────────────────────────────┼────────┼─────────────────────────────────────┤
│ Speed vs. Cursor Baseline  │ 1,500  │ Time to produce priority ranking   │
│                            │        │ vs. vanilla Cursor+Claude prompt.   │
│                            │        │ If faster: (baseline/northstar) ×   │
│                            │        │ 750. If also more accurate: +750.   │
├────────────────────────────┼────────┼─────────────────────────────────────┤
│ Actionability              │ 1,000  │ Are NorthStar's suggestions         │
│                            │        │ specific enough to act on           │
│                            │        │ immediately? Human rater scores     │
│                            │        │ each suggestion 1-10.              │
│                            │        │ (avg_score / 10) × 1000            │
└────────────────────────────┴────────┴─────────────────────────────────────┘

Total Maximum: 10,000
```

### 5 Test Cases

```
Test Case 1: E-Commerce MVP
  Input: "Build a WhatsApp shopping bot with payments"
  Expected: NorthStar should prioritize payment integration > product search
            > cart > UI polish (revenue-critical path first)
  Measure: Priority order vs. expert panel

Test Case 2: Binance API Integration (aligned with their priorities)
  Input: "Integrate Binance spot trading with alerts and portfolio view"
  Expected: NorthStar should prioritize auth > market data > trade execution
            > alerts > portfolio (dependency chain order)
  Measure: Priority order vs. expert panel

Test Case 3: Startup Pivot
  Input: Codebase with existing features + new strategic direction
  Expected: NorthStar detects that 60% of current work is on deprecated
            features and flags massive priority debt
  Measure: Drift detection accuracy

Test Case 4: Tech Debt vs. Features
  Input: Codebase with known tech debt + feature requests
  Expected: NorthStar balances short-term delivery with long-term health
            based on deadline proximity and debt severity
  Measure: Leverage ranking quality

Test Case 5: Multi-Stakeholder Conflict
  Input: Engineering wants refactor, Sales wants demo feature, CEO wants pivot
  Expected: NorthStar provides objective leverage ranking that resolves
            the conflict with data, not opinions
  Measure: Actionability score
```

### Baseline Comparison: NorthStar vs. Vanilla Cursor+Claude

For each test case, run the same scenario two ways:

**Method A (Vanilla Cursor)**: Open Cursor, paste the business context, ask "What should I work on first and why?"

**Method B (NorthStar)**: Run `northstar analyze` on the same context.

Compare: ranking accuracy, reasoning depth, persistence (does vanilla remember context across sessions?), drift detection (vanilla can't do this at all).

---

## Part 6: Three Demo Scenarios (Detailed)

### Demo 1: E-Commerce MVP (Shows Your Emma/CustomerConnect Experience)

**Input (input.yaml):**
```yaml
project:
  name: "WhatsApp Shopping Bot"
  description: "AI-powered shopping agent on WhatsApp with product search, cart, and payments"
  stage: "MVP"
  deadline: "2 weeks"
  
goals:
  primary: "Process first real transaction within 10 days"
  secondary: "Support 100 concurrent users"
  
constraints:
  - "WhatsApp Business API rate limits"
  - "Razorpay integration required for payments"
  - "Must support Hinglish"
  
current_tasks:
  - name: "Beautiful product carousel UI"
    status: "in_progress"
    effort_spent: "3 days"
  - name: "Payment integration"
    status: "not_started"
  - name: "Product search with NLP"
    status: "in_progress"
    effort_spent: "1 day"
  - name: "Cart management"
    status: "not_started"
  - name: "User onboarding flow"
    status: "not_started"
```

**NorthStar Output:**
```
🔴 PRIORITY DEBT SCORE: 6,200 / 10,000 (CRITICAL)

DIAGNOSIS: You've spent 3 days on product carousel UI while payment 
integration (your primary goal's critical path) hasn't started. 
Your goal is "first real transaction in 10 days." You cannot transact 
without payments. The carousel is cosmetic.

PRIORITY STACK (by Leverage Score):
1. Payment Integration        → Leverage: 9,100  ← START HERE
   Reason: Blocks primary goal. Zero transactions possible without it.
   Unlocks: Cart → Checkout → Transaction (3 dependencies)

2. Cart Management            → Leverage: 7,800
   Reason: Required for checkout flow. Minimal viable version: 2 hours.

3. Product Search (continue)  → Leverage: 6,200
   Reason: Already 1 day in. Good progress. Finish basic version.

4. User Onboarding            → Leverage: 3,500
   Reason: Important but not blocking. Can onboard manually for MVP.

5. Product Carousel UI        → Leverage: 1,200  ← PAUSE THIS
   Reason: Cosmetic. WhatsApp text-based product lists work for MVP.
   Recommendation: Stop immediately. Resume after first transaction.

RECOMMENDED NEXT 48 HOURS:
  Hour 0-8:   Razorpay integration (test mode)
  Hour 8-12:  Cart management (minimal)
  Hour 12-16: Connect cart → payment → confirmation
  Hour 16-20: End-to-end test: search → cart → pay → confirm
  Hour 20-24: Fix critical bugs from test

PROJECTED DEBT AFTER REBALANCE: 1,400 (Green)
```

### Demo 2: Binance API Integration (Aligned With Their Priorities)

**Input:** A project to build a crypto trading dashboard with Binance integration.

**NorthStar identifies:**
- Developer is spending time on a fancy candlestick chart visualization
- Meanwhile, API authentication (the foundation for everything) is incomplete
- Priority Debt: 5,800 — the chart is worthless without authenticated data

**NorthStar reorders:** Auth → Market Data WebSocket → Order Execution → Portfolio View → Charts (last, not first)

### Demo 3: SaaS Product Priority Conflict

**Input:** A SaaS codebase where engineering, sales, and CEO have conflicting priorities.

**NorthStar provides:** Objective leverage ranking that shows the CEO's pivot direction unlocks 4x more value than the sales demo feature, but the engineering refactor is a prerequisite for both. Result: Refactor (2 days) → Pivot feature → Sales demo (can be derived from pivot feature).

---

## Part 7: Dual-Role Documentation Strategy

### FDE_PERSPECTIVE.md — Technical Deep-Dive

This document showcases:

1. **Architecture decisions** — Why async Python, why Tree-sitter for AST, why SQLite for state
2. **Code quality** — Type hints, comprehensive docstrings, clean abstractions
3. **Production readiness** — Docker containerization, environment variable management, error handling
4. **API integration patterns** — Claude API usage for reasoning, Git integration for history analysis
5. **Performance optimization** — Caching strategies, incremental codebase scanning, efficient state persistence
6. **Testing rigor** — Unit tests, integration tests, benchmark reproducibility
7. **Security** — No hardcoded secrets, .env.example pattern, input sanitization

**Key talking point**: "I didn't just build an agent — I built a production system with proper state management, error recovery, and extensible architecture. This is how FDEs think: not just solving the problem, but deploying the solution reliably."

### APO_PERSPECTIVE.md — Strategic Showcase

This document showcases:

1. **Problem identification** — How I identified Priority Debt as the core unsolved problem in AI-native workflows
2. **Market analysis** — Why existing tools (Jira, Linear, OKR platforms) fail at this
3. **Framework creation** — Priority Debt as a new, measurable concept (like Technical Debt was once new)
4. **Product vision** — How NorthStar evolves: single developer → team → enterprise
5. **Prioritization meta-game** — The agent itself demonstrates priority definition ability (it IS the product of correct prioritization)
6. **Metrics design** — The 1-10,000 scoring system as a product feature, not just a benchmark
7. **Go-to-market thinking** — Who needs this first (AI-native startups), who needs it most (scaling teams)

**Key talking point**: "I didn't just build a tool — I identified a new category of problem (Priority Debt), created a measurement framework for it, and built the first solution. This is how APOs think: not just managing tasks, but defining what matters."

---

## Part 8: The .cursorrules File

```
# NorthStar — Priority Debt Engine for AI-Native Development
# Cursor Configuration File

## Project Identity
NorthStar is a Cursor-native AI agent that measures and reduces Priority Debt
in software projects. It maintains persistent strategic context and evaluates
whether current development work is the highest-leverage action available.

## Core Concept
Priority Debt = cumulative cost of working on low-leverage tasks while
high-leverage tasks remain undone. NorthStar quantifies this on a 0-10,000 scale.

## Architecture
- Python 3.11+, async-first, type-hinted throughout
- 4 engines: Ingestion, Analysis, Detection, Reporting
- State: SQLite + JSON for persistence across sessions
- LLM: Claude API for strategic reasoning
- Codebase analysis: Tree-sitter for AST parsing

## Key Files
- northstar/analysis/priority_debt.py — Core PDS calculation
- northstar/analysis/leverage_ranker.py — Task leverage scoring
- northstar/detection/drift_monitor.py — Real-time drift detection
- northstar/ingestion/context_builder.py — Strategic Context Map builder
- northstar/state/manager.py — Persistent state management

## Code Conventions
- All public functions have Google-style docstrings
- Type hints on every function signature
- Data models use Pydantic BaseModel
- Scores are always on the 0-10,000 scale
- Tasks are always represented as Task dataclass with leverage_score field
- Strategic goals use the Goal model with alignment weights

## When Generating Code
- Always reference models.py for data structures before creating new ones
- Check priority_debt.py for the PDS formula before modifying scoring
- Use the async pattern from llm.py for any new LLM calls
- Follow the existing error handling pattern: custom exceptions in each engine
- State changes must go through state/manager.py — never write directly

## Testing
- Every new function needs a corresponding test in tests/unit/
- Benchmark test cases are in benchmarks/test_cases/ — don't modify inputs
- Run: pytest tests/ -v --tb=short

## Dependencies
- anthropic (Claude API)
- tree-sitter + tree-sitter-python (AST analysis)
- pydantic (data validation)
- rich (terminal output)
- sqlite3 (state persistence)
- numpy (scoring calculations)
```

---

## Part 9: 7-Day Execution Plan

### Day 1: Foundation & Problem Statement (8 hours)

**Morning (4h):**
- [ ] Initialize GitHub repo with full directory structure
- [ ] Write `.cursorrules` file
- [ ] Create `.env.example` with all required variables
- [ ] Set up `requirements.txt` and `setup.py`
- [ ] Create `Makefile` with: `make install`, `make test`, `make run`, `make benchmark`
- [ ] Write `Dockerfile`

**Afternoon (4h):**
- [ ] Write `PROBLEM_STATEMENT.md` — the full Priority Debt thesis
- [ ] Write initial `README.md` with project overview, quick start, and architecture diagram
- [ ] Define all data models in `northstar/analysis/models.py`:
  - `Task`, `Goal`, `StrategicContext`, `PriorityDebtScore`, `LeverageScore`, `DriftAlert`
- [ ] Create the config system (`config.py`)

**Day 1 Deliverable**: Repo is set up, problem is articulated, data models are defined.

---

### Day 2: Ingestion Engine (8 hours)

**Morning (4h):**
- [ ] Build `codebase_scanner.py`:
  - Walks directory tree, identifies file types, extracts structure
  - Uses Tree-sitter for Python AST analysis (functions, classes, imports)
  - Generates a `CodebaseProfile` with: size, complexity, module map
- [ ] Build `doc_reader.py`:
  - Reads README.md, CHANGELOG, any docs/ folder
  - Extracts key themes and stated goals using Claude API

**Afternoon (4h):**
- [ ] Build `goal_parser.py`:
  - Accepts YAML input (business goals, OKRs, constraints)
  - Validates and structures into `Goal` objects with alignment weights
- [ ] Build `context_builder.py`:
  - Combines codebase profile + docs + goals into `StrategicContext`
  - This is the "brain" that all other engines reference
- [ ] Write unit tests for all ingestion components

**Day 2 Deliverable**: NorthStar can ingest a codebase and build a Strategic Context Map.

---

### Day 3: Analysis Engine (8 hours)

**Morning (4h):**
- [ ] Build `leverage_ranker.py`:
  - Takes list of tasks + `StrategicContext`
  - Calculates `LeverageScore` for each task using the formula
  - Uses Claude API to estimate effort and impact when not manually specified
  - Returns sorted priority stack

**Afternoon (4h):**
- [ ] Build `priority_debt.py`:
  - Takes priority stack + current work status
  - Calculates Priority Debt Score (0-10,000)
  - Identifies the biggest debt contributors
  - Generates human-readable diagnosis
- [ ] Build `gap_analyzer.py`:
  - Compares stated goals vs. actual work distribution
  - Identifies strategic gaps (goals with zero aligned work)
- [ ] Write unit tests for all analysis components

**Day 3 Deliverable**: NorthStar can rank tasks by leverage and calculate Priority Debt.

---

### Day 4: Detection + Reporting + State (8 hours)

**Morning (4h):**
- [ ] Build `state/manager.py`:
  - SQLite backend for persistent state across sessions
  - Stores: context snapshots, priority decisions, debt history, session logs
- [ ] Build `detection/drift_monitor.py`:
  - Monitors current work activity (via file change detection or manual input)
  - Compares against priority stack
  - Triggers `DriftAlert` when drift ratio exceeds threshold
- [ ] Build `detection/session_tracker.py`:
  - Tracks session duration and active files
  - Feeds into drift monitor

**Afternoon (4h):**
- [ ] Build `reporting/decision_logger.py`:
  - Logs every priority decision with timestamp, reasoning, and context
  - Queryable history
- [ ] Build `reporting/debt_report.py`:
  - Generates weekly Priority Debt Report in Markdown
  - Includes: score trend, top debt contributors, recommendations
- [ ] Build `cli.py`:
  - `northstar init` — Initialize context for a project
  - `northstar analyze` — Run full priority analysis
  - `northstar status` — Show current Priority Debt Score
  - `northstar check` — Run drift check on current session
  - `northstar report` — Generate Priority Debt Report
- [ ] Write integration tests

**Day 4 Deliverable**: Full pipeline works end-to-end. CLI is functional.

---

### Day 5: Demo Scenarios (8 hours)

**Morning (4h):**
- [ ] Build Demo 1 (E-Commerce MVP):
  - Create `input.yaml` with WhatsApp bot context
  - Run NorthStar, capture full output
  - Write `walkthrough.md` with annotated results
- [ ] Build Demo 2 (Binance Integration):
  - Create `input.yaml` with crypto dashboard context
  - Run NorthStar, capture full output
  - Write `walkthrough.md`

**Afternoon (4h):**
- [ ] Build Demo 3 (SaaS Priority Conflict):
  - Create `input.yaml` with multi-stakeholder conflict
  - Run NorthStar, capture full output
  - Write `walkthrough.md`
- [ ] Create demo runner script: `make demo` runs all 3 demos sequentially
- [ ] Verify all demos produce clean, compelling output

**Day 5 Deliverable**: 3 complete, documented demo scenarios that showcase NorthStar's power.

---

### Day 6: Benchmarks & Comparison (8 hours)

**Morning (4h):**
- [ ] Build scoring framework (`benchmarks/scoring/`):
  - `methodology.py` — Implements the 5-dimension scoring system
  - `dimensions.py` — Individual dimension calculators
  - `calculator.py` — Composite score aggregation
- [ ] Run all 5 test cases through NorthStar, record raw results

**Afternoon (4h):**
- [ ] Run baseline comparison (vanilla Cursor+Claude):
  - For each test case, prompt Cursor with same context
  - Record responses, timing, and quality
  - Document side-by-side in `comparison_report.md`
- [ ] Calculate final NorthStar score with full methodology transparency
- [ ] Write `BENCHMARKS.md` with:
  - Methodology explanation
  - Per-dimension scores
  - Per-test-case breakdown
  - Baseline comparison table
  - Honest assessment of strengths and weaknesses

**Day 6 Deliverable**: Complete, reproducible benchmark with transparent scoring.

---

### Day 7: Polish, Documentation & Ship (8 hours)

**Morning (4h):**
- [ ] Write `FDE_PERSPECTIVE.md` (technical showcase)
- [ ] Write `APO_PERSPECTIVE.md` (strategic showcase)
- [ ] Write `ARCHITECTURE.md` (full technical deep-dive)
- [ ] Write `DESIGN_DECISIONS.md` (why every choice was made)
- [ ] Finalize `README.md`:
  - Clean overview
  - Quick start (< 5 minutes)
  - Architecture diagram
  - Demo screenshots/outputs
  - Link to all docs

**Afternoon (4h):**
- [ ] Security audit:
  - Grep for any hardcoded keys, tokens, URLs
  - Verify `.env.example` is clean
  - Check `.gitignore` covers all sensitive files
- [ ] Code cleanup:
  - Remove dead code, unused imports
  - Ensure consistent formatting (run `black` and `isort`)
  - Verify all tests pass: `make test`
- [ ] Final demo run: `make demo` → verify clean output
- [ ] Final benchmark run: `make benchmark` → verify scores match docs
- [ ] Push to GitHub
- [ ] Send submission

**Day 7 Deliverable**: Ship it. 🚀

---

## Part 10: Why This Wins

### For FDE Evaluation
- Production-grade Python with async patterns, proper state management, and Docker
- Real API integrations (Claude, Tree-sitter, Git)
- Comprehensive test suite with reproducible benchmarks
- Clean architecture with clear separation of concerns
- Security-conscious design (no secrets, env vars, proper .gitignore)

### For APO Evaluation
- Identified a genuinely new problem category (Priority Debt)
- Created a measurement framework that didn't exist before
- Demonstrated priority definition ability through the agent's purpose itself
- Strategic vision: single dev → team → enterprise scaling path
- Product thinking: the scoring system IS the product, not just a benchmark

### The Meta-Argument
The agent IS the argument. NorthStar exists because of correct priority definition. Building a "priority compass" as a quest submission for a company that values priority definition above all else is the strongest possible signal that you understand what they're looking for.

You're not just showing you can code. You're not just showing you can strategize. You're showing that you know **what matters most** — which is the one thing they say they're hiring for.

---

## Appendix: Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Scope creep | Stick to MVP. Drift detection can be simplified to file-change analysis. |
| LLM costs during dev | Use Claude Haiku for development, Sonnet for final benchmarks. |
| Tree-sitter complexity | Fall back to simple regex-based code analysis if needed. |
| Demo output quality | Pre-seed strategic context manually if auto-ingestion is imperfect. |
| Time overrun | Days 5-6 can be compressed. Demos and benchmarks can be done in parallel. |
| Benchmark gaming | Be transparent about limitations. Honest self-assessment scores higher than inflated numbers. |
