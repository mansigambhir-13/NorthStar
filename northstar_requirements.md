# NorthStar: Complete Product Requirements & System Design

---

# DOCUMENT 1: PRODUCT REQUIREMENTS DOCUMENT (PRD)

---

## 1. Executive Summary

### 1.1 Product Name
**NorthStar** — The Priority Debt Engine

### 1.2 One-Line Description
A Cursor-native AI agent that measures Priority Debt — the cumulative cost of building low-leverage features while high-leverage work remains undone — and provides real-time course correction for AI-native development teams.

### 1.3 Problem Statement
In the AI-native era, execution speed is no longer the bottleneck. Tools like Cursor, Claude, and Copilot have reduced development time from months to days. But this acceleration has created a paradox: teams are now building more low-value features faster than ever before. No existing tool measures whether the work being done is the RIGHT work. The gap between "can we build it?" and "should we build it?" is widening, and it's invisible.

### 1.4 Vision
NorthStar becomes the strategic compass that every AI-native developer and product team relies on — the tool that ensures AI-accelerated productivity is directed at work that actually matters. Just as linters prevent code quality debt, NorthStar prevents priority debt.

### 1.5 Target Users

| User Persona | Description | Pain Point |
|-------------|------------|------------|
| **AI-Native Solo Developer** | Building MVPs with Cursor/Claude. Ships fast but often realizes weeks later they built the wrong thing first. | No external signal to validate priority choices in real-time. |
| **Startup CTO / Tech Lead** | Managing 2-8 engineers all moving fast with AI tools. Struggles to keep everyone aligned on what matters most. | Velocity metrics look great but product impact is stalling. |
| **AI Product Owner (APO)** | Orchestrating AI-driven workflows. Needs to define priorities that maximize leverage across the team. | No quantitative framework for measuring priority quality. |
| **Forward Deployed Engineer (FDE)** | Deploying solutions in messy, undefined environments. Must independently decide what to build first. | Working in ambiguity without a priority framework. |

### 1.6 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Priority Accuracy | >80% correlation with expert panel | Kendall's Tau on 5 standardized test cases |
| Drift Detection Rate | >90% true positive rate | F1-score on simulated drift scenarios |
| Time to First Value | <5 minutes | From `northstar init` to first Priority Debt Score |
| User Decision Quality | 2x improvement | Before/after comparison of priority choices |
| Adoption Signal | Developer runs `northstar check` voluntarily 3+ times/day | Usage telemetry (local only) |

---

## 2. Product Requirements

### 2.1 Functional Requirements

#### FR-001: Project Initialization
- **Description**: User can initialize NorthStar for any software project with a single command.
- **Input**: Project root directory path + optional goals YAML file.
- **Output**: Strategic Context Map stored as persistent state.
- **Acceptance Criteria**:
  - `northstar init` completes in <60 seconds for repos up to 50,000 LOC.
  - Automatically detects: primary language, framework, project structure, README content.
  - Prompts user for business goals if no goals YAML is provided.
  - Creates `.northstar/` directory in project root for state persistence.

#### FR-002: Strategic Context Ingestion
- **Description**: NorthStar ingests and understands the full strategic context of a project.
- **Sources**:
  - Codebase structure (directories, files, dependencies)
  - Documentation (README, CHANGELOG, docs/ folder)
  - Configuration files (package.json, pyproject.toml, Dockerfile)
  - Git history (recent commits, active branches, contributor patterns)
  - Manual input (goals YAML with business objectives, OKRs, deadlines)
- **Output**: `StrategicContext` object containing:
  - Project identity (name, type, stage, primary language)
  - Goal hierarchy (primary goal, secondary goals, constraints)
  - Technical landscape (modules, dependencies, complexity hotspots)
  - Work patterns (recent commit velocity, active areas, contributor focus)
- **Acceptance Criteria**:
  - Correctly identifies project type for Python, JavaScript, TypeScript, Go, Rust projects.
  - Extracts at least 12/15 predefined strategic signals from a standard project.
  - Updates incrementally on subsequent runs (does not re-scan unchanged files).
  - Context is human-readable when exported as JSON.

#### FR-003: Task Discovery & Leverage Scoring
- **Description**: NorthStar discovers pending tasks and scores each by leverage.
- **Task Sources**:
  - Manual input (YAML task list or inline CLI)
  - TODO/FIXME comments in codebase
  - Open issues (if GitHub integration enabled)
  - LLM-inferred tasks from context analysis
- **Leverage Score Formula**:
  ```
  LeverageScore = (GoalAlignment × Impact × UrgencyMultiplier × DependencyUnlock) / EffortEstimate
  ```
  - GoalAlignment (0-1): How directly this task serves the #1 strategic goal
  - Impact (1-100): Estimated user/business impact
  - UrgencyMultiplier:
    - Blocking other tasks: 3.0x
    - Deadline within 48h: 2.5x
    - Deadline within 1 week: 1.5x
    - No deadline: 1.0x
  - DependencyUnlock: 1 + (0.5 × number of tasks this unblocks)
  - EffortEstimate: Hours (from LLM analysis + historical data)
- **Output**: Sorted priority stack with leverage scores normalized to 0-10,000 scale.
- **Acceptance Criteria**:
  - Scores are deterministic given the same inputs (temperature=0 for LLM calls).
  - Each score includes human-readable reasoning (not just a number).
  - Re-ranking completes in <10 seconds for up to 50 tasks.
  - Handles tasks with incomplete information gracefully (uses LLM to estimate missing fields).

#### FR-004: Priority Debt Calculation
- **Description**: NorthStar calculates a single Priority Debt Score (PDS) representing the project's current misallocation of effort.
- **Formula**:
  ```
  PDS = Σ(Weight_i × UndoneLeverage_i × TimeDecay_i) - Σ(Weight_j × DoneLeverage_j)
  
  Where:
    TimeDecay = e^(0.1 × days_undone)
    Weight = Goal alignment score (0-1)
  ```
- **Scale**: 0 (perfect focus) to 10,000 (catastrophic misallocation)
- **Severity Bands**:
  - 0-500: 🟢 Green — Excellent focus
  - 500-2,000: 🟡 Yellow — Some drift, review this week
  - 2,000-5,000: 🟠 Orange — Significant debt, stop and re-prioritize
  - 5,000-10,000: 🔴 Red — Critical strategic misalignment
- **Output**: PDS with diagnosis (which tasks contribute most to debt, recommended rebalancing).
- **Acceptance Criteria**:
  - Score updates in <5 seconds.
  - Diagnosis includes top 3 debt contributors with specific remediation actions.
  - Historical scores are persisted for trend analysis.
  - Score is reproducible (same inputs = same score).

#### FR-005: Real-Time Drift Detection
- **Description**: During active development, NorthStar monitors whether current work aligns with the priority stack.
- **Detection Method**:
  - Tracks active file changes (via filesystem watcher or manual check-in).
  - Maps active files to tasks in the priority stack.
  - Computes drift ratio: current_task_leverage / top_3_average_leverage.
- **Alert Thresholds**:
  - drift_ratio < 0.3 AND session > 30 min → HIGH alert
  - drift_ratio < 0.6 AND session > 45 min → MEDIUM alert
  - drift_ratio < 0.8 AND session > 60 min → LOW alert
- **Alert Format**: Non-blocking terminal notification with:
  - Current task and its leverage score
  - Top alternative task and its leverage score
  - Time spent on current task
  - Options: Continue | Switch | Defer Current
- **Acceptance Criteria**:
  - Alerts are non-blocking (never interrupts coding flow).
  - False positive rate < 15% on simulated sessions.
  - User can snooze alerts for configurable duration.
  - Alert history is logged for retrospective analysis.

#### FR-006: Decision Logging
- **Description**: Every priority-related decision is recorded for accountability and retrospective analysis.
- **Logged Events**:
  - Task started (which task, leverage score, alternative options)
  - Task completed (actual time vs. estimated)
  - Task switched (reason, from-task, to-task)
  - Drift alert triggered (severity, user response)
  - Priority re-ranking (trigger, before/after comparison)
  - Manual priority override (user chose lower-leverage task with stated reason)
- **Storage**: SQLite database in `.northstar/decisions.db`
- **Acceptance Criteria**:
  - All events include ISO 8601 timestamps.
  - Log is queryable by date range, task, event type.
  - Export to JSON and Markdown supported.
  - Log never exceeds 50MB (automatic archival of entries >90 days old).

#### FR-007: Priority Debt Reporting
- **Description**: NorthStar generates periodic reports summarizing priority health.
- **Report Types**:
  - **Session Report**: Generated on `northstar report session` — Summary of current session's decisions and drift events.
  - **Weekly Report**: Generated on `northstar report weekly` — Week-over-week PDS trend, top accomplishments by leverage, biggest debt contributors, recommendations.
  - **Retrospective Report**: Generated on `northstar report retro` — Analysis of past priority decisions: which were correct, which should have been different, lessons learned.
- **Output Format**: Markdown files saved to `.northstar/reports/`
- **Acceptance Criteria**:
  - Reports are human-readable without any technical background.
  - Weekly report includes a text-based PDS trend visualization.
  - Retrospective compares predicted leverage vs. actual outcome.
  - Reports can be generated for any date range.

#### FR-008: CLI Interface
- **Description**: Full-featured command-line interface for all NorthStar operations.
- **Commands**:
  ```
  northstar init [--goals <path>]          Initialize project context
  northstar analyze                         Full priority analysis
  northstar status                          Show current PDS and top priorities
  northstar check                           Quick drift check on current session
  northstar rank [--task <description>]     Add and rank a new task
  northstar tasks                           List all tasks with leverage scores
  northstar log                             View recent decision log
  northstar report <session|weekly|retro>   Generate reports
  northstar config                          View/edit configuration
  northstar export                          Export all data as JSON
  northstar reset                           Clear all NorthStar data for project
  ```
- **Acceptance Criteria**:
  - All commands complete in <15 seconds.
  - `--help` flag on every command with usage examples.
  - Colored terminal output using Rich library.
  - JSON output mode for every command (`--json` flag).
  - Exit codes follow convention (0 = success, 1 = error, 2 = warning).

#### FR-009: Cursor Integration
- **Description**: NorthStar integrates natively with Cursor IDE.
- **Integration Points**:
  - `.cursorrules` file that teaches Cursor about the project's priority context.
  - Cursor-aware commands that consider the active workspace.
  - Context injection: When Cursor asks Claude for help, NorthStar's priority context enriches the prompt.
- **Acceptance Criteria**:
  - `.cursorrules` is auto-generated and auto-updated on `northstar init` and `northstar analyze`.
  - Cursor can access NorthStar's priority stack through the rules file.
  - No conflict with existing `.cursorrules` (NorthStar appends, doesn't overwrite).

#### FR-010: Goals Management
- **Description**: Users can define, update, and track business goals that drive priority calculations.
- **Goal Structure** (YAML):
  ```yaml
  goals:
    primary:
      description: "Process first real transaction within 10 days"
      deadline: "2025-03-15"
      weight: 1.0
    secondary:
      - description: "Support 100 concurrent users"
        deadline: "2025-04-01"
        weight: 0.6
      - description: "Achieve <2s response time"
        weight: 0.4
    constraints:
      - "Must use Razorpay for payments"
      - "WhatsApp Business API rate limits apply"
  ```
- **Acceptance Criteria**:
  - Goals can be set via YAML file or interactive CLI prompt.
  - Goals can be updated without re-initializing the project.
  - Goal changes trigger automatic priority re-ranking.
  - Goal completion is tracked and reflected in PDS calculation.

### 2.2 Non-Functional Requirements

#### NFR-001: Performance
- Init scan: <60 seconds for repos up to 50,000 LOC
- Full analysis: <30 seconds for up to 50 tasks
- Drift check: <5 seconds
- Status query: <2 seconds
- Incremental re-scan: <10 seconds (only changed files)

#### NFR-002: Reliability
- Graceful degradation if LLM API is unavailable (use cached context + rule-based scoring)
- No data loss on crash (SQLite WAL mode for write-ahead logging)
- Automatic state recovery on corrupted state files

#### NFR-003: Security
- Zero hardcoded credentials in codebase
- All API keys via environment variables
- `.northstar/` directory excluded from git by default (auto-adds to .gitignore)
- No telemetry or data transmission without explicit opt-in
- Local-only operation by default

#### NFR-004: Portability
- Runs on macOS, Linux, Windows (WSL)
- Python 3.11+ only dependency
- Optional Docker container for isolated execution
- No system-level dependencies beyond Python

#### NFR-005: Extensibility
- Plugin architecture for custom task sources (GitHub Issues, Linear, Jira)
- Custom scoring dimension support (user can add domain-specific leverage factors)
- Configurable alert thresholds
- Webhook support for external notifications (Slack, Discord)

---

## 3. User Stories

### 3.1 Solo Developer Stories

**US-001**: As a solo developer building an MVP, I want to initialize NorthStar on my project so that I can get an immediate Priority Debt Score telling me if I'm focused on the right things.

**US-002**: As a developer using Cursor, I want NorthStar to alert me when I've been working on a low-leverage task for too long so that I can course-correct before wasting hours.

**US-003**: As a developer about to start a new coding session, I want to run `northstar status` to see my current top priority so I know exactly where to start.

**US-004**: As a developer who just finished a feature, I want NorthStar to automatically re-rank my remaining tasks so my priority stack is always current.

**US-005**: As a developer preparing for a sprint, I want NorthStar to generate a priority-ranked task list with effort estimates so I can plan realistically.

### 3.2 Team Lead Stories

**US-006**: As a tech lead, I want to see which team members have the highest priority debt so I can reallocate work before it becomes critical.

**US-007**: As a tech lead, I want weekly Priority Debt Reports so I can present objective data about our focus quality in standups.

**US-008**: As a tech lead, I want to run Priority Retrospectives so the team can learn from past priority mistakes.

### 3.3 APO Stories

**US-009**: As an APO, I want to define strategic goals in YAML and have NorthStar automatically score all tasks against them so I can see misalignment instantly.

**US-010**: As an APO managing multiple stakeholders, I want NorthStar to objectively rank competing priorities (engineering refactor vs. sales demo vs. CEO pivot) so decisions are data-driven.

**US-011**: As an APO, I want to simulate "what if" scenarios — if we change the primary goal, how does the priority stack shift? — so I can make informed strategic pivots.

### 3.4 FDE Stories

**US-012**: As an FDE deployed at a client site, I want to initialize NorthStar on an unfamiliar codebase and get a priority assessment within 5 minutes so I can start delivering value immediately.

**US-013**: As an FDE with a 48-hour deadline, I want NorthStar to identify the absolute minimum set of tasks needed to deliver a working solution so I can focus on what unblocks everything else.

**US-014**: As an FDE, I want NorthStar to log all my priority decisions so I can show the client an auditable trail of why I built what I built.

---

## 4. User Flows

### 4.1 Flow 1: First-Time Setup

```
1. Developer navigates to project root directory
2. Runs: northstar init
3. NorthStar scans codebase (progress bar shown)
4. NorthStar detects: Python project, FastAPI framework, 12,000 LOC
5. NorthStar reads README and extracts project description
6. NorthStar prompts: "No goals file found. Define your primary goal?"
7. Developer types: "Process first real payment within 10 days"
8. NorthStar prompts: "Any secondary goals? (comma-separated, or press Enter to skip)"
9. Developer types: "Support 100 concurrent users, Response time under 2 seconds"
10. NorthStar creates .northstar/ directory with:
    - context.json (Strategic Context Map)
    - goals.yaml (Structured goals)
    - decisions.db (Empty decision log)
    - .cursorrules.northstar (Cursor context injection)
11. NorthStar runs initial analysis automatically
12. Output:
    ┌────────────────────────────────────────────┐
    │  NORTHSTAR INITIALIZED                      │
    │                                              │
    │  Project: whatsapp-shopping-bot              │
    │  Type: Python / FastAPI                      │
    │  LOC: 12,342                                 │
    │  Primary Goal: First real payment (10 days)  │
    │                                              │
    │  Initial Priority Debt Score: 4,200 🟠       │
    │  Diagnosis: Payment integration not started   │
    │             but is on the critical path.      │
    │                                              │
    │  Top Priority: Razorpay payment integration  │
    │  Leverage Score: 8,900                       │
    │                                              │
    │  Run `northstar tasks` for full stack.       │
    └────────────────────────────────────────────┘
```

### 4.2 Flow 2: Active Development Session

```
1. Developer runs: northstar status
   → Shows current PDS (4,200 🟠) and top 3 tasks
2. Developer opens payment_integration.py in Cursor
3. Developer works for 2 hours on payment integration
4. Developer completes Razorpay basic integration
5. Developer runs: northstar check
   → "Great focus! Current task: Payment Integration (Leverage: 8,900).
      This is your #1 priority. PDS impact: -1,800 when complete."
6. Developer switches to working on login_animation.css
7. After 35 minutes, NorthStar drift alert triggers:
   → "⚠️ DRIFT DETECTED (Medium)
      Current: Login animation (Leverage: 1,200)
      Top priority: Cart management (Leverage: 7,800)
      Time on current: 35 minutes
      [Continue] [Switch to Cart] [Snooze 30min]"
8. Developer chooses "Switch to Cart"
9. NorthStar logs: DriftAlert → UserSwitched → cart_management
10. At session end, developer runs: northstar report session
    → Markdown report saved to .northstar/reports/session_2025-03-01.md
```

### 4.3 Flow 3: Weekly Priority Review

```
1. Tech lead runs: northstar report weekly
2. NorthStar generates report:
   
   # Weekly Priority Debt Report
   ## Week of Feb 24 - Mar 1, 2025
   
   ### PDS Trend
   Mon: 6,200 🔴 → Tue: 5,100 🟠 → Wed: 4,200 🟠 → 
   Thu: 2,800 🟠 → Fri: 1,400 🟢
   
   ### Top Accomplishments (by Leverage Impact)
   1. Payment Integration completed (Leverage: 8,900) → PDS: -2,400
   2. Cart Management completed (Leverage: 7,800) → PDS: -1,600
   3. Product Search v1 completed (Leverage: 6,200) → PDS: -1,200
   
   ### Biggest Remaining Debt Contributors
   1. Error handling & recovery (Leverage: 5,400, undone 4 days)
   2. Load testing (Leverage: 4,100, undone 3 days)
   
   ### Drift Events
   - 3 drift alerts triggered this week
   - 2 resulted in task switches (good)
   - 1 was snoozed then continued (review)
   
   ### Recommendation
   Focus next week on error handling — it's been accumulating
   debt at an accelerating rate due to TimeDecay.
```

### 4.4 Flow 4: Stakeholder Priority Conflict

```
1. APO runs: northstar analyze --scenario conflict_resolution
2. NorthStar prompts for competing priorities:
   a. Engineering wants: "Refactor authentication module" (2 days)
   b. Sales wants: "Build demo dashboard for client pitch" (3 days)
   c. CEO wants: "Pivot to B2B model" (1 week)
3. NorthStar analyzes against Strategic Context:
   
   ┌─────────────────────────────────────────────────────────┐
   │  PRIORITY CONFLICT RESOLUTION                           │
   │                                                          │
   │  1. Auth Refactor          Leverage: 7,200               │
   │     Reason: Prerequisite for BOTH demo and pivot.        │
   │     Blocks: 2 downstream tasks. Must go first.           │
   │                                                          │
   │  2. B2B Pivot Features     Leverage: 6,800               │
   │     Reason: Highest strategic impact if primary goal      │
   │     shifts to B2B. Demo can be derived from pivot work.  │
   │                                                          │
   │  3. Demo Dashboard         Leverage: 3,200               │
   │     Reason: Can reuse 80% of pivot UI. Build last,       │
   │     not first. Standalone demo = throwaway work.         │
   │                                                          │
   │  RECOMMENDED SEQUENCE:                                   │
   │  Days 1-2: Auth refactor (unblocks everything)           │
   │  Days 3-7: B2B pivot core features                       │
   │  Days 8-9: Demo dashboard (derived from pivot UI)        │
   │                                                          │
   │  Total: 9 days for all three (vs. 12 days in parallel)  │
   └─────────────────────────────────────────────────────────┘
```

---

## 5. Out of Scope (v1)

The following are explicitly NOT included in the v1 quest submission:

| Feature | Reason | Future Version |
|---------|--------|---------------|
| GUI / Web Dashboard | Quest values execution over fancy UI | v2 |
| GitHub Issues Integration | Adds external dependency complexity | v2 |
| Team Multi-User Support | Solo dev focus for v1 | v2 |
| Real-Time File Watcher | Simplified to manual `northstar check` for v1 | v1.5 |
| Jira/Linear Sync | Out of scope for quest | v3 |
| Custom LLM Support | Claude-only for v1 | v2 |
| Natural Language Task Input | Structured YAML for v1 | v1.5 |

---

# DOCUMENT 2: SYSTEM DESIGN

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                      │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   CLI    │  │ .cursorrules │  │  Markdown Reports          │ │
│  │ (Rich)   │  │  Generator   │  │  (.northstar/reports/)     │ │
│  └────┬─────┘  └──────┬───────┘  └────────────┬───────────────┘ │
│       │               │                        │                 │
├───────┴───────────────┴────────────────────────┴─────────────────┤
│                        ORCHESTRATION LAYER                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Pipeline Manager                       │   │
│  │  Coordinates engine execution order, handles errors,      │   │
│  │  manages async operations, routes data between engines    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                         ENGINE LAYER                             │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────┐ │
│  │  INGESTION   │ │  ANALYSIS    │ │ DETECTION  │ │REPORTING │ │
│  │  ENGINE      │ │  ENGINE      │ │ ENGINE     │ │ENGINE    │ │
│  │              │ │              │ │            │ │          │ │
│  │ • Codebase   │ │ • Leverage   │ │ • Drift    │ │• Decision│ │
│  │   Scanner    │ │   Ranker     │ │   Monitor  │ │  Logger  │ │
│  │ • Context    │ │ • Priority   │ │ • Session  │ │• Debt    │ │
│  │   Builder    │ │   Debt Calc  │ │   Tracker  │ │  Report  │ │
│  │ • Goal       │ │ • Gap        │ │ • Alert    │ │• Retro   │ │
│  │   Parser     │ │   Analyzer   │ │   System   │ │  Report  │ │
│  │ • Doc Reader │ │              │ │            │ │          │ │
│  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └────┬─────┘ │
│         │                │               │              │       │
├─────────┴────────────────┴───────────────┴──────────────┴───────┤
│                       FOUNDATION LAYER                           │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │    State     │ │     LLM      │ │      Git               │  │
│  │   Manager    │ │   Client     │ │    Integration         │  │
│  │  (SQLite +   │ │ (Claude API) │ │  (History Analysis)    │  │
│  │   JSON)      │ │              │ │                        │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │   Config     │ │   Models     │ │    Exceptions          │  │
│  │  Manager     │ │ (Pydantic)   │ │  (Custom Hierarchy)    │  │
│  └──────────────┘ └──────────────┘ └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
                    ┌──────────────┐
                    │  User Input  │
                    │  (CLI/YAML)  │
                    └──────┬───────┘
                           │
                           ▼
               ┌───────────────────────┐
               │   INGESTION ENGINE    │
               │                       │
               │  Codebase ──┐         │
               │  Docs    ───┤         │
               │  Goals   ───┤         │
               │  Git     ───┘         │
               │         │             │
               │         ▼             │
               │  StrategicContext      │
               └───────────┬───────────┘
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
         ┌─────────────┐  ┌──────────────┐
         │  ANALYSIS   │  │  DETECTION   │
         │  ENGINE     │  │  ENGINE      │
         │             │  │              │
         │ Tasks +     │  │ Active Work  │
         │ Context     │  │ + Priority   │
         │     │       │  │ Stack        │
         │     ▼       │  │     │        │
         │ • Leverage  │  │     ▼        │
         │   Scores    │  │ • Drift      │
         │ • PDS       │  │   Ratio      │
         │ • Gap       │  │ • Alerts     │
         │   Analysis  │  │              │
         └──────┬──────┘  └──────┬───────┘
                │                │
                └───────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  REPORTING       │
              │  ENGINE          │
              │                  │
              │  All Results ──► │
              │  Decision Log    │
              │  Historical Data │
              │        │         │
              │        ▼         │
              │  • Session Rpt   │
              │  • Weekly Rpt    │
              │  • Retro Rpt     │
              └──────────────────┘
```

---

## 2. Data Models

### 2.1 Core Models (Pydantic)

```python
# ====== GOALS ======

class Goal(BaseModel):
    id: str                          # Unique identifier
    description: str                 # Human-readable goal description
    weight: float                    # 0.0-1.0, importance relative to other goals
    deadline: Optional[datetime]     # Target completion date
    status: GoalStatus               # active, completed, paused, abandoned
    created_at: datetime
    completed_at: Optional[datetime]

class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"

class GoalSet(BaseModel):
    primary: Goal
    secondary: List[Goal] = []
    constraints: List[str] = []


# ====== TASKS ======

class Task(BaseModel):
    id: str                          # Unique identifier
    description: str                 # What needs to be done
    status: TaskStatus               # pending, in_progress, completed, deferred
    source: TaskSource               # manual, todo_comment, llm_inferred, github_issue
    goal_alignment: float            # 0.0-1.0, how directly it serves primary goal
    impact: int                      # 1-100, estimated business/user impact
    urgency: UrgencyLevel            # blocking, deadline_48h, deadline_1w, none
    dependencies: List[str]          # IDs of tasks this depends on
    blocks: List[str]                # IDs of tasks this unblocks
    effort_hours: float              # Estimated hours to complete
    leverage_score: float            # Calculated, 0-10,000
    leverage_reasoning: str          # Human-readable explanation of score
    actual_hours: Optional[float]    # Filled on completion
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"

class TaskSource(str, Enum):
    MANUAL = "manual"
    TODO_COMMENT = "todo_comment"
    LLM_INFERRED = "llm_inferred"
    GITHUB_ISSUE = "github_issue"

class UrgencyLevel(str, Enum):
    BLOCKING = "blocking"           # 3.0x multiplier
    DEADLINE_48H = "deadline_48h"   # 2.5x
    DEADLINE_1W = "deadline_1w"     # 1.5x
    NONE = "none"                   # 1.0x


# ====== CONTEXT ======

class CodebaseProfile(BaseModel):
    root_path: str
    primary_language: str
    framework: Optional[str]
    total_files: int
    total_loc: int
    modules: List[ModuleInfo]
    dependencies: List[str]
    complexity_hotspots: List[str]   # Files with highest cyclomatic complexity
    scan_timestamp: datetime

class ModuleInfo(BaseModel):
    path: str
    language: str
    loc: int
    functions: int
    classes: int
    todo_count: int
    last_modified: datetime

class GitProfile(BaseModel):
    total_commits_30d: int
    active_branches: List[str]
    recent_focus_areas: List[str]    # Directories with most recent changes
    contributor_count: int
    commit_velocity: float           # Commits per day (30d average)

class StrategicContext(BaseModel):
    project_name: str
    project_type: str                # "web_app", "api", "cli", "library", etc.
    stage: str                       # "mvp", "growth", "mature"
    codebase: CodebaseProfile
    git: GitProfile
    goals: GoalSet
    tasks: List[Task]
    created_at: datetime
    updated_at: datetime


# ====== SCORES ======

class PriorityDebtScore(BaseModel):
    score: float                     # 0-10,000
    severity: str                    # green, yellow, orange, red
    diagnosis: str                   # Human-readable explanation
    top_contributors: List[DebtContributor]
    recommendations: List[str]
    calculated_at: datetime

class DebtContributor(BaseModel):
    task_id: str
    task_description: str
    leverage_score: float
    days_undone: int
    debt_contribution: float         # How much this task adds to PDS
    remediation: str                 # Specific action to reduce debt


# ====== DRIFT ======

class DriftAlert(BaseModel):
    id: str
    severity: str                    # high, medium, low
    current_task: str
    current_leverage: float
    suggested_task: str
    suggested_leverage: float
    drift_ratio: float
    session_duration_minutes: int
    message: str
    user_response: Optional[str]     # continue, switch, snooze
    triggered_at: datetime
    responded_at: Optional[datetime]


# ====== DECISIONS ======

class DecisionEvent(BaseModel):
    id: str
    event_type: DecisionType
    timestamp: datetime
    task_id: Optional[str]
    from_task_id: Optional[str]      # For switches
    to_task_id: Optional[str]        # For switches
    leverage_score: Optional[float]
    reasoning: Optional[str]
    metadata: Dict[str, Any] = {}

class DecisionType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_SWITCHED = "task_switched"
    DRIFT_ALERT = "drift_alert"
    PRIORITY_RERANK = "priority_rerank"
    MANUAL_OVERRIDE = "manual_override"
    GOAL_UPDATED = "goal_updated"
```

### 2.2 Database Schema (SQLite)

```sql
-- Strategic context snapshots (versioned)
CREATE TABLE context_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Task history
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    source TEXT NOT NULL DEFAULT 'manual',
    goal_alignment REAL NOT NULL DEFAULT 0.5,
    impact INTEGER NOT NULL DEFAULT 50,
    urgency TEXT NOT NULL DEFAULT 'none',
    effort_hours REAL NOT NULL DEFAULT 4.0,
    leverage_score REAL,
    leverage_reasoning TEXT,
    actual_hours REAL,
    dependencies TEXT DEFAULT '[]',  -- JSON array
    blocks TEXT DEFAULT '[]',        -- JSON array
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Priority Debt Score history
CREATE TABLE pds_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score REAL NOT NULL,
    severity TEXT NOT NULL,
    diagnosis TEXT,
    contributors_json TEXT,          -- JSON array of DebtContributor
    recommendations_json TEXT,       -- JSON array of strings
    calculated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Decision event log
CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    task_id TEXT,
    from_task_id TEXT,
    to_task_id TEXT,
    leverage_score REAL,
    reasoning TEXT,
    metadata_json TEXT DEFAULT '{}',
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Drift alert history
CREATE TABLE drift_alerts (
    id TEXT PRIMARY KEY,
    severity TEXT NOT NULL,
    current_task TEXT,
    current_leverage REAL,
    suggested_task TEXT,
    suggested_leverage REAL,
    drift_ratio REAL,
    session_duration_minutes INTEGER,
    message TEXT,
    user_response TEXT,
    triggered_at TEXT NOT NULL DEFAULT (datetime('now')),
    responded_at TEXT
);

-- Session tracking
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at TEXT,
    tasks_worked TEXT DEFAULT '[]',   -- JSON array of task IDs
    drift_alerts_count INTEGER DEFAULT 0,
    switches_count INTEGER DEFAULT 0,
    pds_start REAL,
    pds_end REAL
);

-- Configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for query performance
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_leverage ON tasks(leverage_score DESC);
CREATE INDEX idx_decisions_type ON decisions(event_type);
CREATE INDEX idx_decisions_timestamp ON decisions(timestamp);
CREATE INDEX idx_pds_history_date ON pds_history(calculated_at);
CREATE INDEX idx_drift_alerts_date ON drift_alerts(triggered_at);
```

---

## 3. Component Design

### 3.1 Ingestion Engine

#### 3.1.1 Codebase Scanner (`codebase_scanner.py`)

**Responsibility**: Scan project filesystem and extract structural understanding.

**Algorithm**:
```
1. Walk directory tree (respect .gitignore, skip node_modules/.venv/etc.)
2. For each file:
   a. Detect language from extension
   b. Count lines of code (exclude blank/comment lines)
   c. If Python: parse AST with Tree-sitter → extract functions, classes, imports
   d. If JS/TS: parse AST → extract exports, components, routes
   e. Count TODO/FIXME comments → create task candidates
3. Identify complexity hotspots (files with >500 LOC or >20 functions)
4. Detect framework (FastAPI, Django, React, Next.js, etc.) from imports/config
5. Build dependency graph from import statements
6. Return CodebaseProfile
```

**Caching Strategy**:
- Store file hashes in `.northstar/cache.json`
- On re-scan, only process files with changed hashes
- Cache invalidation: automatic when file mtime changes

#### 3.1.2 Context Builder (`context_builder.py`)

**Responsibility**: Combine all ingested data into a unified StrategicContext.

**Process**:
```
1. Receive: CodebaseProfile, GoalSet, GitProfile, DocumentInsights
2. Merge task lists from all sources (deduplicate by description similarity)
3. Estimate effort for each task using Claude:
   - Prompt: "Given this codebase context and task description, estimate hours to complete"
   - Include: relevant file excerpts, complexity metrics, dependency information
4. Calculate initial goal alignment for each task using Claude:
   - Prompt: "Rate 0-1 how directly this task serves the goal: [goal]"
5. Build StrategicContext object
6. Persist to SQLite as a context snapshot
7. Return StrategicContext
```

**LLM Interaction Pattern**:
```python
async def estimate_task_effort(task: Task, context: CodebaseProfile) -> float:
    prompt = f"""
    Project: {context.primary_language} / {context.framework}
    Size: {context.total_loc} LOC, {context.total_files} files
    
    Task: {task.description}
    
    Relevant files: {get_relevant_files(task, context)}
    
    Estimate hours to complete this task. Consider:
    - Existing code that can be reused
    - External API integration complexity
    - Testing requirements
    
    Respond with ONLY a JSON object: {{"hours": <float>, "reasoning": "<brief>"}}
    """
    response = await llm_client.complete(prompt, temperature=0)
    return parse_effort_response(response)
```

### 3.2 Analysis Engine

#### 3.2.1 Leverage Ranker (`leverage_ranker.py`)

**Responsibility**: Score and rank all tasks by leverage.

**Algorithm**:
```python
def calculate_leverage(task: Task, context: StrategicContext) -> float:
    # Goal Alignment (0-1)
    goal_alignment = task.goal_alignment
    
    # Impact (1-100, normalized to 0-1)
    impact = task.impact / 100.0
    
    # Urgency Multiplier
    urgency_map = {
        UrgencyLevel.BLOCKING: 3.0,
        UrgencyLevel.DEADLINE_48H: 2.5,
        UrgencyLevel.DEADLINE_1W: 1.5,
        UrgencyLevel.NONE: 1.0,
    }
    urgency = urgency_map[task.urgency]
    
    # Dependency Unlock
    dependency_unlock = 1.0 + (0.5 * len(task.blocks))
    
    # Effort (minimum 0.5 to prevent division by zero)
    effort = max(task.effort_hours, 0.5)
    
    # Raw leverage
    raw = (goal_alignment * impact * urgency * dependency_unlock) / effort
    
    # Normalize to 0-10,000 scale
    # Max theoretical raw: (1.0 * 1.0 * 3.0 * 5.0) / 0.5 = 30.0
    normalized = min((raw / 30.0) * 10000, 10000)
    
    return round(normalized, 0)
```

**Ranking Output**:
```python
class PriorityStack(BaseModel):
    tasks: List[Task]                # Sorted by leverage_score descending
    top_action: Task                 # Highest leverage task
    context_summary: str             # Brief context for Cursor integration
    generated_at: datetime
```

#### 3.2.2 Priority Debt Calculator (`priority_debt.py`)

**Responsibility**: Calculate the Priority Debt Score.

**Algorithm**:
```python
import math

def calculate_pds(
    tasks: List[Task],
    goals: GoalSet,
    history: List[PriorityDebtScore]
) -> PriorityDebtScore:
    
    debt_accumulation = 0.0
    debt_reduction = 0.0
    contributors = []
    
    for task in tasks:
        if task.status in (TaskStatus.PENDING, TaskStatus.DEFERRED):
            # Undone task accumulates debt
            days_undone = (datetime.now() - task.created_at).days
            time_decay = math.exp(0.1 * days_undone)
            
            contribution = (
                task.goal_alignment *
                (task.leverage_score / 10000) *
                time_decay
            )
            debt_accumulation += contribution
            
            contributors.append(DebtContributor(
                task_id=task.id,
                task_description=task.description,
                leverage_score=task.leverage_score,
                days_undone=days_undone,
                debt_contribution=contribution,
                remediation=f"Start this task. Estimated {task.effort_hours}h."
            ))
        
        elif task.status == TaskStatus.COMPLETED:
            # Completed task reduces debt
            debt_reduction += (
                task.goal_alignment *
                (task.leverage_score / 10000)
            )
    
    # Normalize to 0-10,000 scale
    raw_pds = debt_accumulation - debt_reduction
    normalized_pds = max(0, min(raw_pds * 1000, 10000))
    
    # Determine severity
    if normalized_pds < 500:
        severity = "green"
    elif normalized_pds < 2000:
        severity = "yellow"
    elif normalized_pds < 5000:
        severity = "orange"
    else:
        severity = "red"
    
    # Sort contributors by debt contribution (worst first)
    contributors.sort(key=lambda c: c.debt_contribution, reverse=True)
    
    # Generate diagnosis using LLM
    diagnosis = await generate_diagnosis(normalized_pds, contributors[:3], goals)
    
    return PriorityDebtScore(
        score=round(normalized_pds, 0),
        severity=severity,
        diagnosis=diagnosis,
        top_contributors=contributors[:5],
        recommendations=generate_recommendations(contributors[:3]),
        calculated_at=datetime.now()
    )
```

#### 3.2.3 Gap Analyzer (`gap_analyzer.py`)

**Responsibility**: Identify gaps between stated goals and actual work.

**Algorithm**:
```
1. For each goal in GoalSet:
   a. Find all tasks aligned to this goal (alignment > 0.3)
   b. Calculate total effort allocated vs. total effort needed
   c. Calculate coverage ratio = allocated / needed
2. Flag gaps:
   - Coverage < 0.2 → CRITICAL gap (goal has almost no work)
   - Coverage < 0.5 → SIGNIFICANT gap
   - Coverage < 0.8 → MINOR gap
3. Detect orphan tasks (tasks with goal_alignment < 0.1 to ANY goal)
   - These are potential priority debt sources
4. Return GapReport with per-goal coverage and orphan list
```

### 3.3 Detection Engine

#### 3.3.1 Drift Monitor (`drift_monitor.py`)

**Responsibility**: Detect when current work drifts from priority stack.

**Design**:
```python
class DriftMonitor:
    def __init__(self, priority_stack: PriorityStack, config: DriftConfig):
        self.stack = priority_stack
        self.config = config
        self.session_start = datetime.now()
        self.current_task: Optional[Task] = None
        self.snooze_until: Optional[datetime] = None
    
    async def check(self, active_files: List[str] = None) -> Optional[DriftAlert]:
        """Manual drift check triggered by user or automated scan."""
        
        if self.snooze_until and datetime.now() < self.snooze_until:
            return None
        
        # Determine current task from active files or manual input
        current = self._infer_current_task(active_files)
        if not current:
            return None
        
        self.current_task = current
        session_minutes = (datetime.now() - self.session_start).total_seconds() / 60
        
        # Calculate drift
        top_3_avg = self._top_3_average()
        drift_ratio = current.leverage_score / top_3_avg if top_3_avg > 0 else 1.0
        
        # Check thresholds
        if drift_ratio < 0.3 and session_minutes > 30:
            severity = "high"
        elif drift_ratio < 0.6 and session_minutes > 45:
            severity = "medium"
        elif drift_ratio < 0.8 and session_minutes > 60:
            severity = "low"
        else:
            return None  # No drift
        
        return DriftAlert(
            id=generate_id(),
            severity=severity,
            current_task=current.description,
            current_leverage=current.leverage_score,
            suggested_task=self.stack.top_action.description,
            suggested_leverage=self.stack.top_action.leverage_score,
            drift_ratio=round(drift_ratio, 3),
            session_duration_minutes=int(session_minutes),
            message=self._format_alert(current, self.stack.top_action, drift_ratio),
            triggered_at=datetime.now()
        )
    
    def _infer_current_task(self, active_files: List[str]) -> Optional[Task]:
        """Map active files to tasks in the priority stack."""
        if not active_files:
            return self.current_task  # Use last known
        
        # Score each task by relevance to active files
        best_match = None
        best_score = 0
        
        for task in self.stack.tasks:
            relevance = compute_file_task_relevance(active_files, task)
            if relevance > best_score:
                best_score = relevance
                best_match = task
        
        return best_match if best_score > 0.3 else None
```

#### 3.3.2 Session Tracker (`session_tracker.py`)

**Responsibility**: Track development sessions for drift analysis and reporting.

```python
class SessionTracker:
    """Tracks a development session from start to end."""
    
    def __init__(self, state_manager: StateManager):
        self.state = state_manager
        self.session_id = generate_id()
        self.started_at = datetime.now()
        self.tasks_worked: List[str] = []
        self.drift_alerts: List[DriftAlert] = []
        self.switches: List[Dict] = []
        self.pds_start: Optional[float] = None
        self.pds_end: Optional[float] = None
    
    def start(self, initial_pds: float):
        self.pds_start = initial_pds
        self.state.save_session_start(self.session_id, self.started_at, initial_pds)
    
    def record_task_start(self, task_id: str):
        self.tasks_worked.append(task_id)
        self.state.log_decision(DecisionEvent(
            id=generate_id(),
            event_type=DecisionType.TASK_STARTED,
            task_id=task_id,
            timestamp=datetime.now()
        ))
    
    def record_drift_alert(self, alert: DriftAlert):
        self.drift_alerts.append(alert)
        self.state.save_drift_alert(alert)
    
    def record_switch(self, from_task: str, to_task: str, reason: str):
        self.switches.append({
            "from": from_task, "to": to_task,
            "reason": reason, "at": datetime.now().isoformat()
        })
        self.state.log_decision(DecisionEvent(
            id=generate_id(),
            event_type=DecisionType.TASK_SWITCHED,
            from_task_id=from_task,
            to_task_id=to_task,
            reasoning=reason,
            timestamp=datetime.now()
        ))
    
    def end(self, final_pds: float):
        self.pds_end = final_pds
        self.state.save_session_end(
            self.session_id, datetime.now(), final_pds,
            self.tasks_worked, len(self.drift_alerts), len(self.switches)
        )
```

### 3.4 Reporting Engine

#### 3.4.1 Report Generator (`debt_report.py`)

**Design Pattern**: Template-based Markdown generation with data injection.

```python
class WeeklyReportGenerator:
    def __init__(self, state: StateManager, llm: LLMClient):
        self.state = state
        self.llm = llm
    
    async def generate(self, week_start: date, week_end: date) -> str:
        # Gather data
        pds_history = self.state.get_pds_history(week_start, week_end)
        decisions = self.state.get_decisions(week_start, week_end)
        drift_alerts = self.state.get_drift_alerts(week_start, week_end)
        completed_tasks = self.state.get_completed_tasks(week_start, week_end)
        remaining_tasks = self.state.get_pending_tasks()
        
        # Build trend line
        trend = self._build_trend(pds_history)
        
        # Calculate accomplishments by leverage impact
        accomplishments = sorted(completed_tasks, key=lambda t: t.leverage_score, reverse=True)
        
        # Identify biggest remaining debt
        debt_contributors = self._get_top_debt_contributors(remaining_tasks)
        
        # Generate AI-powered insights
        insights = await self.llm.analyze_week(
            pds_history, decisions, drift_alerts, completed_tasks
        )
        
        # Render Markdown report
        return self._render_template(
            week_start=week_start,
            week_end=week_end,
            trend=trend,
            accomplishments=accomplishments[:5],
            debt_contributors=debt_contributors[:3],
            drift_summary=self._summarize_drifts(drift_alerts),
            insights=insights,
            decisions_count=len(decisions)
        )
```

### 3.5 Foundation Layer

#### 3.5.1 State Manager (`state/manager.py`)

**Design**: Single source of truth for all persistent data.

```python
class StateManager:
    """Manages all persistent state via SQLite with JSON fallback."""
    
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.northstar_dir = self.root / ".northstar"
        self.db_path = self.northstar_dir / "northstar.db"
        self.context_path = self.northstar_dir / "context.json"
        self._ensure_directory()
        self._init_database()
    
    def _ensure_directory(self):
        self.northstar_dir.mkdir(exist_ok=True)
        # Auto-add to .gitignore
        gitignore = self.root / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if ".northstar/" not in content:
                with open(gitignore, "a") as f:
                    f.write("\n# NorthStar priority tracking\n.northstar/\n")
        
    def _init_database(self):
        """Create tables if they don't exist."""
        self.db = sqlite3.connect(
            str(self.db_path),
            isolation_level=None  # Autocommit for WAL mode
        )
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
    
    # ---- Context Operations ----
    def save_context(self, context: StrategicContext):
        # Save as JSON for human readability
        self.context_path.write_text(context.model_dump_json(indent=2))
        # Also save as versioned snapshot in DB
        self.db.execute(
            "INSERT INTO context_snapshots (snapshot_json) VALUES (?)",
            [context.model_dump_json()]
        )
    
    def load_context(self) -> Optional[StrategicContext]:
        if self.context_path.exists():
            return StrategicContext.model_validate_json(
                self.context_path.read_text()
            )
        return None
    
    # ---- Task Operations ----
    def save_task(self, task: Task): ...
    def get_tasks(self, status: TaskStatus = None) -> List[Task]: ...
    def update_task_status(self, task_id: str, status: TaskStatus): ...
    
    # ---- PDS Operations ----
    def save_pds(self, pds: PriorityDebtScore): ...
    def get_pds_history(self, start: date, end: date) -> List[PriorityDebtScore]: ...
    def get_latest_pds(self) -> Optional[PriorityDebtScore]: ...
    
    # ---- Decision Operations ----
    def log_decision(self, event: DecisionEvent): ...
    def get_decisions(self, start: date, end: date) -> List[DecisionEvent]: ...
    
    # ---- Drift Operations ----
    def save_drift_alert(self, alert: DriftAlert): ...
    def get_drift_alerts(self, start: date, end: date) -> List[DriftAlert]: ...
    
    # ---- Session Operations ----
    def save_session_start(self, ...): ...
    def save_session_end(self, ...): ...
    def get_sessions(self, start: date, end: date) -> List[Dict]: ...
```

#### 3.5.2 LLM Client (`integrations/llm.py`)

**Design**: Abstracted Claude API client with caching, retry logic, and cost tracking.

```python
class LLMClient:
    """Claude API client with retry, caching, and structured output."""
    
    def __init__(self, config: LLMConfig):
        self.client = anthropic.AsyncAnthropic()
        self.model = config.model          # "claude-sonnet-4-5-20250929"
        self.cache = {}                     # In-memory cache for identical prompts
        self.total_tokens = 0
        self.total_cost = 0.0
    
    async def complete(
        self,
        prompt: str,
        system: str = None,
        temperature: float = 0,
        max_tokens: int = 1024,
        response_format: str = "text"  # "text" or "json"
    ) -> str:
        # Check cache
        cache_key = hashlib.md5(f"{prompt}{system}{temperature}".encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Build messages
        messages = [{"role": "user", "content": prompt}]
        
        # Retry with exponential backoff
        for attempt in range(3):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system or self._default_system_prompt(),
                    messages=messages
                )
                
                result = response.content[0].text
                self.total_tokens += response.usage.input_tokens + response.usage.output_tokens
                
                # Cache result
                self.cache[cache_key] = result
                
                if response_format == "json":
                    return self._extract_json(result)
                return result
                
            except anthropic.RateLimitError:
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == 2:
                    raise LLMError(f"LLM call failed after 3 attempts: {e}")
                await asyncio.sleep(1)
    
    def _default_system_prompt(self) -> str:
        return """You are NorthStar's analysis engine. You evaluate software 
        development priorities with precision and strategic thinking. Always 
        respond with structured, actionable analysis. When estimating effort 
        or impact, be realistic and conservative. When providing reasoning, 
        be specific and reference concrete project details."""
    
    async def analyze_task_leverage(self, task: Task, context: StrategicContext) -> Dict:
        """Use Claude to analyze task leverage with full context."""
        prompt = f"""
        Analyze this task's leverage for the project:
        
        PROJECT: {context.project_name} ({context.project_type})
        PRIMARY GOAL: {context.goals.primary.description}
        DEADLINE: {context.goals.primary.deadline}
        CODEBASE: {context.codebase.primary_language}, {context.codebase.total_loc} LOC
        
        TASK: {task.description}
        
        Evaluate and return JSON:
        {{
            "goal_alignment": <0.0-1.0>,
            "impact": <1-100>,
            "effort_hours": <float>,
            "reasoning": "<2-3 sentences explaining the scores>"
        }}
        """
        return await self.complete(prompt, temperature=0, response_format="json")
```

#### 3.5.3 Git Integration (`integrations/git.py`)

```python
class GitAnalyzer:
    """Analyzes git history for development patterns."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    async def analyze(self) -> GitProfile:
        """Extract development patterns from git history."""
        commits_30d = await self._get_recent_commits(days=30)
        branches = await self._get_active_branches()
        focus_areas = self._identify_focus_areas(commits_30d)
        
        return GitProfile(
            total_commits_30d=len(commits_30d),
            active_branches=branches,
            recent_focus_areas=focus_areas,
            contributor_count=len(set(c.author for c in commits_30d)),
            commit_velocity=len(commits_30d) / 30.0
        )
    
    async def _get_recent_commits(self, days: int) -> List[CommitInfo]:
        """Parse git log for recent commits."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%H|%an|%ae|%at|%s",
             "--name-only"],
            capture_output=True, text=True, cwd=self.repo_path
        )
        return self._parse_git_log(result.stdout)
    
    def _identify_focus_areas(self, commits: List[CommitInfo]) -> List[str]:
        """Find directories with most recent changes."""
        dir_counts = Counter()
        for commit in commits:
            for file in commit.files:
                dir_counts[str(Path(file).parent)] += 1
        return [d for d, _ in dir_counts.most_common(5)]
```

---

## 4. API Design (Internal)

### 4.1 Engine Interfaces

Each engine exposes a clean async interface:

```python
# Ingestion Engine Interface
class IngestionEngine:
    async def scan_codebase(self, root_path: str) -> CodebaseProfile
    async def read_docs(self, root_path: str) -> DocumentInsights
    async def parse_goals(self, goals_path: str) -> GoalSet
    async def analyze_git(self, root_path: str) -> GitProfile
    async def build_context(self, root_path: str, goals_path: str = None) -> StrategicContext

# Analysis Engine Interface
class AnalysisEngine:
    async def rank_tasks(self, tasks: List[Task], context: StrategicContext) -> PriorityStack
    async def calculate_pds(self, context: StrategicContext) -> PriorityDebtScore
    async def analyze_gaps(self, context: StrategicContext) -> GapReport
    async def simulate_rebalance(self, context: StrategicContext, changes: List[TaskChange]) -> PriorityDebtScore

# Detection Engine Interface
class DetectionEngine:
    async def check_drift(self, active_files: List[str] = None) -> Optional[DriftAlert]
    def start_session(self) -> str
    def end_session(self) -> SessionSummary
    def snooze_alerts(self, duration_minutes: int)

# Reporting Engine Interface
class ReportingEngine:
    async def session_report(self) -> str
    async def weekly_report(self, week_start: date = None) -> str
    async def retrospective(self, start: date, end: date) -> str
    def export_decisions(self, start: date, end: date, format: str = "json") -> str
```

### 4.2 Pipeline Manager

```python
class PipelineManager:
    """Coordinates engine execution and data flow."""
    
    def __init__(self, project_root: str, config: NorthStarConfig):
        self.state = StateManager(project_root)
        self.llm = LLMClient(config.llm)
        self.ingestion = IngestionEngine(self.state, self.llm)
        self.analysis = AnalysisEngine(self.state, self.llm)
        self.detection = DetectionEngine(self.state)
        self.reporting = ReportingEngine(self.state, self.llm)
    
    async def initialize(self, goals_path: str = None) -> StrategicContext:
        """Full project initialization pipeline."""
        context = await self.ingestion.build_context(self.state.root, goals_path)
        stack = await self.analysis.rank_tasks(context.tasks, context)
        pds = await self.analysis.calculate_pds(context)
        self.state.save_context(context)
        self.state.save_pds(pds)
        return context
    
    async def analyze(self) -> Dict:
        """Full analysis pipeline."""
        context = self.state.load_context()
        if not context:
            raise NorthStarError("Project not initialized. Run: northstar init")
        
        # Re-scan for changes
        context = await self.ingestion.build_context(str(self.state.root))
        
        # Rank and score
        stack = await self.analysis.rank_tasks(context.tasks, context)
        pds = await self.analysis.calculate_pds(context)
        gaps = await self.analysis.analyze_gaps(context)
        
        # Persist
        self.state.save_context(context)
        self.state.save_pds(pds)
        
        return {
            "priority_stack": stack,
            "pds": pds,
            "gaps": gaps
        }
    
    async def quick_check(self) -> Dict:
        """Fast drift check for active session."""
        alert = await self.detection.check_drift()
        pds = self.state.get_latest_pds()
        return {"alert": alert, "pds": pds}
```

---

## 5. Configuration

### 5.1 Configuration File (`.northstar/config.yaml`)

```yaml
# NorthStar Configuration

# LLM Settings
llm:
  model: "claude-sonnet-4-5-20250929"    # Model for analysis
  temperature: 0                          # Deterministic scoring
  max_tokens: 2048                        # Max tokens per call
  cache_enabled: true                     # Cache identical prompts

# Drift Detection
drift:
  enabled: true
  thresholds:
    high:
      ratio: 0.3
      minutes: 30
    medium:
      ratio: 0.6
      minutes: 45
    low:
      ratio: 0.8
      minutes: 60
  snooze_default_minutes: 30

# Scanning
scan:
  ignore_patterns:
    - "node_modules"
    - ".venv"
    - "__pycache__"
    - ".git"
    - "dist"
    - "build"
    - ".northstar"
  max_file_size_kb: 500                   # Skip files larger than this
  supported_languages:
    - python
    - javascript
    - typescript
    - go
    - rust

# Reporting
reporting:
  output_dir: ".northstar/reports"
  format: "markdown"

# Scoring
scoring:
  leverage:
    urgency_multipliers:
      blocking: 3.0
      deadline_48h: 2.5
      deadline_1w: 1.5
      none: 1.0
    dependency_factor: 0.5               # Per unlocked task
    min_effort: 0.5                       # Floor for effort divisor
  pds:
    time_decay_rate: 0.1                 # Exponential decay factor
    green_threshold: 500
    yellow_threshold: 2000
    orange_threshold: 5000
```

---

## 6. Error Handling Strategy

### 6.1 Exception Hierarchy

```python
class NorthStarError(Exception):
    """Base exception for all NorthStar errors."""
    pass

class InitializationError(NorthStarError):
    """Project initialization failed."""
    pass

class ContextError(NorthStarError):
    """Strategic context is missing or corrupted."""
    pass

class LLMError(NorthStarError):
    """LLM API call failed."""
    pass

class ScanError(NorthStarError):
    """Codebase scanning failed."""
    pass

class StateError(NorthStarError):
    """State persistence operation failed."""
    pass

class ConfigError(NorthStarError):
    """Configuration is invalid or missing."""
    pass
```

### 6.2 Graceful Degradation

```
IF LLM API unavailable:
  → Use cached context for analysis
  → Fall back to rule-based scoring (no LLM estimation)
  → Warn user: "Running in offline mode. Scores may be less accurate."

IF Git not available:
  → Skip GitProfile
  → Warn user: "Git analysis unavailable. Context may be less complete."

IF State DB corrupted:
  → Attempt auto-repair (re-create tables)
  → If fails: backup corrupted DB, create fresh one
  → Warn user: "State reset. Historical data may be lost."

IF Codebase scan fails on specific files:
  → Log error, skip file, continue scanning
  → Report skipped files count in output
```

---

## 7. Testing Strategy

### 7.1 Test Pyramid

```
                    ┌─────────┐
                    │  E2E    │  3 demo scenarios
                    │  Tests  │  (Day 5 deliverables)
                   ┌┴─────────┴┐
                   │Integration │  Full pipeline tests
                   │   Tests    │  Engine-to-engine flows
                  ┌┴────────────┴┐
                  │  Unit Tests   │  Individual functions
                  │               │  All algorithms
                  └───────────────┘
```

### 7.2 Test Coverage Requirements

| Component | Min Coverage | Key Tests |
|-----------|-------------|-----------|
| Leverage Ranker | 95% | Edge cases: zero effort, max urgency, no dependencies |
| PDS Calculator | 95% | All severity bands, time decay accuracy, empty task lists |
| Drift Monitor | 90% | Threshold boundaries, snooze behavior, session tracking |
| Context Builder | 85% | Multiple languages, missing files, incomplete goals |
| State Manager | 90% | CRUD operations, concurrent access, corruption recovery |
| CLI | 80% | All commands, help text, error messages, JSON output |

### 7.3 Benchmark Test Cases (5 standardized)

Each benchmark test case includes:
- Fixed input (goals + tasks + codebase mock)
- Expected priority ordering (from expert panel)
- Expected PDS range
- Expected drift detection outcomes
- Performance timing requirements

These are frozen and never modified — they serve as the reproducible scoring foundation.

---

# DOCUMENT 3: END-TO-END FEATURE SPECIFICATION

---

## Feature Map

```
NorthStar v1.0 Feature Map
│
├── F1: Project Initialization
│   ├── F1.1: Codebase Scanning
│   ├── F1.2: Goal Definition (YAML + Interactive)
│   ├── F1.3: Context Assembly
│   └── F1.4: .cursorrules Generation
│
├── F2: Priority Analysis
│   ├── F2.1: Task Discovery (Manual + Auto)
│   ├── F2.2: Leverage Scoring
│   ├── F2.3: Priority Stack Generation
│   └── F2.4: Priority Debt Score Calculation
│
├── F3: Gap Analysis
│   ├── F3.1: Goal-Work Alignment Check
│   ├── F3.2: Orphan Task Detection
│   └── F3.3: Strategic Gap Reporting
│
├── F4: Drift Detection
│   ├── F4.1: Session Tracking
│   ├── F4.2: Active Work Inference
│   ├── F4.3: Drift Ratio Calculation
│   ├── F4.4: Alert Generation
│   └── F4.5: Alert Response Handling
│
├── F5: Decision Management
│   ├── F5.1: Event Logging
│   ├── F5.2: Decision History Query
│   └── F5.3: Decision Export
│
├── F6: Reporting
│   ├── F6.1: Session Report
│   ├── F6.2: Weekly Report
│   └── F6.3: Retrospective Report
│
├── F7: CLI Interface
│   ├── F7.1: Init Command
│   ├── F7.2: Analyze Command
│   ├── F7.3: Status Command
│   ├── F7.4: Check Command
│   ├── F7.5: Rank Command
│   ├── F7.6: Tasks Command
│   ├── F7.7: Log Command
│   ├── F7.8: Report Command
│   ├── F7.9: Config Command
│   ├── F7.10: Export Command
│   └── F7.11: Reset Command
│
├── F8: Cursor Integration
│   ├── F8.1: .cursorrules Auto-Generation
│   ├── F8.2: Priority Context Injection
│   └── F8.3: Workspace Awareness
│
├── F9: State Persistence
│   ├── F9.1: SQLite Database Management
│   ├── F9.2: Context Versioning
│   ├── F9.3: Auto-Backup
│   └── F9.4: Data Export/Import
│
└── F10: Benchmark System
    ├── F10.1: 5-Dimension Scoring Framework
    ├── F10.2: 5 Standardized Test Cases
    ├── F10.3: Vanilla Cursor Baseline Comparison
    └── F10.4: Reproducible Score Generation
```

---

## Detailed Feature Specifications

### F1: Project Initialization

#### F1.1: Codebase Scanning

| Attribute | Detail |
|-----------|--------|
| **ID** | F1.1 |
| **Priority** | P0 (Critical) |
| **Effort** | 4 hours |
| **Dependencies** | None |

**Description**: Scan a project's filesystem to understand its structure, languages, frameworks, and complexity.

**Inputs**:
- Project root directory path
- Scan configuration (ignore patterns, max file size)

**Outputs**:
- `CodebaseProfile` object with: file counts, LOC, language breakdown, framework detection, module map, complexity hotspots, TODO/FIXME extraction

**Algorithm Detail**:
1. Walk directory tree respecting `.gitignore` and configured ignore patterns
2. For each file: detect language, count LOC, extract TODOs
3. For Python files: use Tree-sitter AST to extract functions, classes, imports
4. For JS/TS files: detect framework from imports (React, Next.js, Express)
5. Compute cyclomatic complexity approximation (branch count per function)
6. Identify complexity hotspots (top 10% by complexity)
7. Build module dependency graph
8. Detect framework from config files (package.json, pyproject.toml, etc.)

**Edge Cases**:
- Monorepo with multiple languages → detect all, report primary
- Binary files → skip entirely
- Symlinks → follow but detect cycles
- Empty directories → ignore
- Files >500KB → skip, log warning

**Acceptance Criteria**:
- Completes in <60s for 50,000 LOC
- Correctly identifies language for 95%+ of files
- Correctly detects framework for common stacks (FastAPI, Django, React, Next.js, Express)
- Incremental re-scan only processes changed files

---

#### F1.2: Goal Definition

| Attribute | Detail |
|-----------|--------|
| **ID** | F1.2 |
| **Priority** | P0 (Critical) |
| **Effort** | 2 hours |
| **Dependencies** | None |

**Description**: Accept business goals that drive all priority calculations.

**Input Methods**:
- YAML file (`--goals goals.yaml`)
- Interactive CLI prompt (when no file provided)

**YAML Schema**:
```yaml
goals:
  primary:
    description: str (required)
    deadline: date (optional, ISO format)
    weight: float (optional, default 1.0)
  secondary:
    - description: str
      deadline: date (optional)
      weight: float (optional, default 0.5)
  constraints:
    - str
```

**Interactive Flow**:
```
> northstar init

🔍 Scanning codebase...
✅ Detected: Python / FastAPI / 12,342 LOC

No goals file found. Let's define your priorities:

Primary goal: [user types goal]
Deadline (YYYY-MM-DD, or press Enter to skip): [user input]

Secondary goals (comma-separated, or Enter to skip):
[user types goals]

Any constraints? (comma-separated, or Enter to skip):
[user types constraints]

✅ Goals saved to .northstar/goals.yaml
```

**Acceptance Criteria**:
- YAML validation with clear error messages for malformed input
- Interactive mode produces valid YAML identical to manual creation
- Goals can be updated without full re-initialization

---

#### F1.3: Context Assembly

| Attribute | Detail |
|-----------|--------|
| **ID** | F1.3 |
| **Priority** | P0 (Critical) |
| **Effort** | 3 hours |
| **Dependencies** | F1.1, F1.2 |

**Description**: Combine codebase profile, goals, git history, and documentation into a unified `StrategicContext`.

**Process**:
1. Run codebase scan → CodebaseProfile
2. Parse goals → GoalSet
3. Analyze git history → GitProfile
4. Read documentation → DocumentInsights
5. Use Claude to infer: project stage, potential tasks from context, goal-task alignment
6. Merge all into StrategicContext
7. Persist to `.northstar/context.json` + SQLite snapshot

**LLM Usage**:
- Single batched prompt that receives all context and returns structured analysis
- Temperature=0 for deterministic results
- Response cached for identical inputs

---

#### F1.4: Cursorrules Generation

| Attribute | Detail |
|-----------|--------|
| **ID** | F1.4 |
| **Priority** | P1 (Important) |
| **Effort** | 1 hour |
| **Dependencies** | F1.3 |

**Description**: Auto-generate `.cursorrules` additions that inject NorthStar's priority context into Cursor.

**Generated Content**:
```
## NorthStar Priority Context (auto-generated)
## Last updated: [timestamp]

### Current Priority Debt Score: [score] [emoji]
### Primary Goal: [goal description]
### Deadline: [deadline]

### Priority Stack (Top 5):
1. [Task] — Leverage: [score] — [brief reason]
2. [Task] — Leverage: [score] — [brief reason]
...

### When suggesting code changes:
- Prioritize work on: [top priority task]
- Avoid: [lowest leverage tasks] unless specifically requested
- Consider: [constraints]
```

**Behavior**:
- If `.cursorrules` exists: append NorthStar section (delimited by markers)
- If doesn't exist: create new file with NorthStar section
- Updates automatically on `northstar analyze`
- NorthStar section is clearly marked: `## --- NorthStar Auto-Generated ---`

---

### F2: Priority Analysis

#### F2.2: Leverage Scoring

| Attribute | Detail |
|-----------|--------|
| **ID** | F2.2 |
| **Priority** | P0 (Critical) |
| **Effort** | 4 hours |
| **Dependencies** | F1.3 |

**Full Scoring Specification**:

```
INPUT:
  task: Task object
  context: StrategicContext

PROCESS:
  1. Validate inputs (goal_alignment in [0,1], impact in [1,100], etc.)
  
  2. Resolve missing values:
     IF task.goal_alignment is None:
       → Estimate via LLM with project context
     IF task.impact is None:
       → Estimate via LLM: "Rate 1-100 impact of [task] on [goal]"
     IF task.effort_hours is None:
       → Estimate via LLM: "Estimate hours for [task] in [codebase context]"
  
  3. Calculate components:
     goal_alignment = task.goal_alignment                    # 0.0 - 1.0
     impact = task.impact / 100.0                            # 0.0 - 1.0
     urgency = URGENCY_MAP[task.urgency]                     # 1.0 - 3.0
     dep_unlock = 1.0 + (0.5 * len(task.blocks))            # 1.0 - N
     effort = max(task.effort_hours, 0.5)                    # 0.5 - N
  
  4. Raw leverage:
     raw = (goal_alignment * impact * urgency * dep_unlock) / effort
  
  5. Normalize to 0-10,000:
     MAX_RAW = (1.0 * 1.0 * 3.0 * 5.0) / 0.5 = 30.0
     normalized = min((raw / MAX_RAW) * 10000, 10000)
  
  6. Generate reasoning via LLM (if not cached):
     "Explain in 2 sentences why [task] scores [score] given [goal]"

OUTPUT:
  task.leverage_score = round(normalized, 0)
  task.leverage_reasoning = reasoning_text
```

**Score Interpretation Guide**:
- 8,000-10,000: Critical path — do this NOW
- 5,000-7,999: High leverage — schedule this week
- 2,000-4,999: Medium leverage — schedule this sprint
- 500-1,999: Low leverage — backlog
- 0-499: Minimal leverage — consider removing

---

#### F2.4: Priority Debt Score Calculation

| Attribute | Detail |
|-----------|--------|
| **ID** | F2.4 |
| **Priority** | P0 (Critical) |
| **Effort** | 3 hours |
| **Dependencies** | F2.2 |

**Full Specification**:

```
INPUT:
  tasks: List[Task] (all tasks, all statuses)
  goals: GoalSet
  
PROCESS:
  debt = 0.0
  reduction = 0.0
  contributors = []
  
  FOR each task:
    IF task.status in [PENDING, DEFERRED]:
      days = (now - task.created_at).days
      decay = e^(0.1 × days)
      contribution = goal_alignment × (leverage_score/10000) × decay
      debt += contribution
      contributors.append({task, contribution, days})
    
    IF task.status == COMPLETED:
      reduction += goal_alignment × (leverage_score/10000)
  
  raw_pds = debt - reduction
  pds = clamp(raw_pds × 1000, 0, 10000)
  
  severity = 
    pds < 500    → "green"
    pds < 2000   → "yellow"
    pds < 5000   → "orange"
    pds ≥ 5000   → "red"
  
  diagnosis = LLM_GENERATE(
    "Given PDS {pds} ({severity}), top contributors: {top_3}, 
     and goal: {primary_goal}, explain the current state in 3 sentences."
  )
  
  recommendations = [
    f"Start {c.task.description} — reduces PDS by ~{c.contribution*1000:.0f}"
    for c in sorted(contributors, reverse=True)[:3]
  ]

OUTPUT:
  PriorityDebtScore(score, severity, diagnosis, contributors[:5], recommendations)
```

---

### F4: Drift Detection

#### F4.3: Drift Ratio Calculation

| Attribute | Detail |
|-----------|--------|
| **ID** | F4.3 |
| **Priority** | P1 (Important) |
| **Effort** | 2 hours |
| **Dependencies** | F2.3, F4.2 |

**Specification**:

```
INPUT:
  current_task: Task (inferred from active work)
  priority_stack: PriorityStack (current ranked tasks)
  session_duration: int (minutes since session start)

PROCESS:
  top_3 = priority_stack.tasks[:3]
  top_3_avg = mean([t.leverage_score for t in top_3])
  
  IF top_3_avg == 0:
    drift_ratio = 1.0  # No drift if no priorities defined
  ELSE:
    drift_ratio = current_task.leverage_score / top_3_avg
  
  # Check if current task IS in top 3
  IF current_task.id in [t.id for t in top_3]:
    drift_ratio = 1.0  # No drift if working on a top priority
  
  alert = None
  IF drift_ratio < 0.3 AND session_duration > 30:
    alert = DriftAlert(severity="high", ...)
  ELIF drift_ratio < 0.6 AND session_duration > 45:
    alert = DriftAlert(severity="medium", ...)
  ELIF drift_ratio < 0.8 AND session_duration > 60:
    alert = DriftAlert(severity="low", ...)

OUTPUT:
  drift_ratio: float
  alert: Optional[DriftAlert]
```

---

### F7: CLI Interface (Complete Command Spec)

#### F7.1: `northstar init`

```
USAGE: northstar init [OPTIONS]

OPTIONS:
  --goals PATH      Path to goals YAML file
  --no-interactive  Skip interactive prompts (requires --goals)
  --verbose         Show detailed scan output
  --json            Output result as JSON

BEHAVIOR:
  1. Scan codebase in current directory
  2. If --goals provided: parse goals file
  3. If no --goals and not --no-interactive: prompt for goals
  4. Build StrategicContext
  5. Run initial analysis
  6. Generate .cursorrules additions
  7. Display summary with PDS and top priority

EXIT CODES:
  0: Success
  1: Scan failed
  2: Goals file invalid
  3: LLM unavailable (degraded mode used)
```

#### F7.2: `northstar analyze`

```
USAGE: northstar analyze [OPTIONS]

OPTIONS:
  --full            Force full re-scan (not incremental)
  --json            Output as JSON
  --quiet           Only output PDS score

BEHAVIOR:
  1. Load existing context
  2. Incremental codebase re-scan
  3. Re-rank all tasks
  4. Calculate new PDS
  5. Run gap analysis
  6. Update .cursorrules
  7. Display full analysis

OUTPUT FORMAT:
  ┌────────────────────────────────────────────┐
  │  NORTHSTAR ANALYSIS                        │
  │                                             │
  │  Priority Debt Score: 4,200 🟠              │
  │  Change: -800 since last analysis           │
  │                                             │
  │  ═══ PRIORITY STACK ═══                     │
  │  #1  Payment Integration      ▓▓▓▓▓ 8,900  │
  │  #2  Cart Management          ▓▓▓▓  7,800  │
  │  #3  Product Search v2        ▓▓▓   6,200  │
  │  #4  User Onboarding          ▓▓    3,500  │
  │  #5  Login Animation          ▓     1,200  │
  │                                             │
  │  ═══ GAPS ═══                               │
  │  ⚠ "Scalability" goal has 0 aligned tasks  │
  │                                             │
  │  ═══ RECOMMENDATION ═══                     │
  │  Start Payment Integration immediately.     │
  │  It blocks 3 downstream tasks and is on     │
  │  the critical path to your primary goal.    │
  └────────────────────────────────────────────┘
```

#### F7.3: `northstar status`

```
USAGE: northstar status [OPTIONS]

OPTIONS:
  --json    Output as JSON

BEHAVIOR:
  1. Load latest PDS from state
  2. Load current priority stack
  3. Display compact status

OUTPUT FORMAT:
  PDS: 4,200 🟠  |  Top: Payment Integration (8,900)  |  Tasks: 5 pending
```

#### F7.4: `northstar check`

```
USAGE: northstar check [OPTIONS]

OPTIONS:
  --task DESCRIPTION   Manually specify current task
  --json               Output as JSON

BEHAVIOR:
  1. Infer current task from recent file changes (git diff) or --task flag
  2. Run drift calculation
  3. Display result

OUTPUT (no drift):
  ✅ On track! Working on: Payment Integration (Leverage: 8,900)
  Session: 45 minutes | PDS trend: ↓ (improving)

OUTPUT (drift detected):
  ⚠️ DRIFT DETECTED (Medium)
  Current: Login Animation (Leverage: 1,200)
  Top Priority: Cart Management (Leverage: 7,800)
  Session: 38 minutes
  
  [C]ontinue  [S]witch to Cart  [Z] Snooze 30min
```

#### F7.5: `northstar rank`

```
USAGE: northstar rank --task "DESCRIPTION" [OPTIONS]

OPTIONS:
  --impact N          Override impact estimate (1-100)
  --effort N          Override effort estimate (hours)
  --urgency LEVEL     Set urgency (blocking|deadline_48h|deadline_1w|none)
  --json              Output as JSON

BEHAVIOR:
  1. Create new Task from description
  2. Use LLM to estimate missing fields
  3. Calculate leverage score
  4. Insert into priority stack
  5. Recalculate PDS
  6. Display new ranking position

OUTPUT:
  📌 New task: "Add error logging middleware"
  Leverage Score: 4,200 → Ranked #3 of 6
  PDS impact: +180 if deferred
```

---

### F10: Benchmark System

#### F10.1: 5-Dimension Scoring Framework

**Dimension Specifications**:

```
DIMENSION 1: Priority Accuracy (Max: 3,000)
  Method: Kendall's Tau rank correlation
  Process:
    1. For each test case, NorthStar ranks N tasks
    2. Expert panel independently ranks same N tasks
    3. Compute Kendall's Tau (τ) correlation coefficient
    4. Score = τ × 3,000 (τ ranges from -1 to +1, but floor at 0)
  Per-test: 600 points (5 tests × 600 = 3,000)

DIMENSION 2: Drift Detection Precision (Max: 2,500)
  Method: F1-score on classification
  Process:
    1. 20 simulated sessions (10 with drift, 10 without)
    2. NorthStar classifies each as drift/no-drift
    3. Compute F1 = 2 × (precision × recall) / (precision + recall)
    4. Score = F1 × 2,500

DIMENSION 3: Context Completeness (Max: 2,000)
  Method: Signal extraction accuracy
  Process:
    1. Each test case codebase has 15 planted strategic signals
       (e.g., "uses FastAPI", "has payment integration", "3 contributors")
    2. NorthStar extracts what it finds
    3. Score = (correct_extractions / 15) × 2,000
  Per-test: 400 points (5 tests × 400 = 2,000)

DIMENSION 4: Speed vs. Baseline (Max: 1,500)
  Method: Time comparison + accuracy bonus
  Process:
    1. Same task given to NorthStar and vanilla Cursor+Claude
    2. Time both to produce priority ranking
    3. Speed score = min(baseline_time / northstar_time, 2.0) × 750
    4. If NorthStar also more accurate: +750 bonus
  Maximum: 750 (speed) + 750 (accuracy bonus) = 1,500

DIMENSION 5: Actionability (Max: 1,000)
  Method: Human rater scoring
  Process:
    1. NorthStar generates recommendations for each test case
    2. Rate each recommendation 1-10:
       - Is it specific enough to act on immediately?
       - Does it include concrete next steps?
       - Does it reference actual project details?
    3. Score = (average_rating / 10) × 1,000
```

---

## Dependency Graph (Build Order)

```
Week 1: Foundation
  F1.1 (Codebase Scanner) ──→ F1.3 (Context Assembly)
  F1.2 (Goal Definition) ───→ F1.3
  
Week 1-2: Core Analysis
  F1.3 ──→ F2.1 (Task Discovery)
  F1.3 ──→ F2.2 (Leverage Scoring)
  F2.1 + F2.2 ──→ F2.3 (Priority Stack)
  F2.3 ──→ F2.4 (PDS Calculation)
  F2.3 ──→ F3.1 (Gap Analysis)
  
Week 2: Detection & State
  F2.3 ──→ F4.1 (Session Tracking)
  F4.1 ──→ F4.2 (Work Inference)
  F4.2 ──→ F4.3 (Drift Ratio)
  F4.3 ──→ F4.4 (Alert Generation)
  F9.1 (SQLite) runs parallel, used by all
  
Week 2-3: Interface & Reporting
  All F2 + F4 ──→ F7 (CLI)
  F5.1 (Decision Logging) ──→ F6 (Reporting)
  F1.3 ──→ F1.4 (.cursorrules) ──→ F8 (Cursor Integration)
  
Week 3: Benchmarks & Polish
  All features ──→ F10 (Benchmark System)
```
