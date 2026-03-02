"""All Pydantic models and enums for NorthStar."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──────────────────────────────────────────────────────────────

class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class TaskSource(str, Enum):
    MANUAL = "manual"
    TODO_COMMENT = "todo_comment"
    LLM_INFERRED = "llm_inferred"
    GITHUB_ISSUE = "github_issue"
    GOAL_DERIVED = "goal_derived"


class UrgencyLevel(str, Enum):
    BLOCKING = "blocking"
    DEADLINE_48H = "deadline_48h"
    DEADLINE_1W = "deadline_1w"
    NORMAL = "normal"


class DecisionType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_SWITCHED = "task_switched"
    DRIFT_ALERT = "drift_alert"
    RERANK = "rerank"
    MANUAL_OVERRIDE = "manual_override"
    GOAL_UPDATED = "goal_updated"


# ── Goal Models ────────────────────────────────────────────────────────

class Goal(BaseModel):
    """A strategic goal for the project."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str = ""
    priority: int = 1  # 1 = highest
    status: GoalStatus = GoalStatus.ACTIVE
    deadline: datetime | None = None
    success_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GoalSet(BaseModel):
    """Collection of project goals."""

    model_config = ConfigDict(from_attributes=True)

    goals: list[Goal] = Field(default_factory=list)

    @property
    def primary(self) -> Goal | None:
        active = [g for g in self.goals if g.status == GoalStatus.ACTIVE]
        return min(active, key=lambda g: g.priority, default=None)

    @property
    def active_goals(self) -> list[Goal]:
        return [g for g in self.goals if g.status == GoalStatus.ACTIVE]


# ── Task Models ────────────────────────────────────────────────────────

class Task(BaseModel):
    """A work item with leverage scoring metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str = ""
    source: TaskSource = TaskSource.MANUAL
    status: TaskStatus = TaskStatus.PENDING
    goal_id: str | None = None
    goal_alignment: float = 0.0  # 0-1
    impact: int = 50  # 1-100
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    effort_hours: float = 1.0
    blocks: list[str] = Field(default_factory=list)  # task IDs this unblocks
    leverage_score: float = 0.0  # 0-10000, computed
    reasoning: str = ""
    file_path: str | None = None
    line_number: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


# ── Codebase Models ───────────────────────────────────────────────────

class ModuleInfo(BaseModel):
    """Information about a code module/directory."""

    model_config = ConfigDict(from_attributes=True)

    path: str
    language: str = "unknown"
    loc: int = 0
    num_files: int = 0
    complexity_score: float = 0.0
    frameworks: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class CodebaseProfile(BaseModel):
    """Profile of the scanned codebase."""

    model_config = ConfigDict(from_attributes=True)

    root_path: str
    primary_language: str = "unknown"
    total_files: int = 0
    total_loc: int = 0
    modules: list[ModuleInfo] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)  # language -> LOC
    frameworks: list[str] = Field(default_factory=list)
    todos: list[dict[str, Any]] = Field(default_factory=list)
    file_hashes: dict[str, str] = Field(default_factory=dict)
    scan_timestamp: datetime = Field(default_factory=datetime.utcnow)


class GitProfile(BaseModel):
    """Git repository analysis."""

    model_config = ConfigDict(from_attributes=True)

    branch: str = "main"
    total_commits: int = 0
    recent_commits: list[dict[str, str]] = Field(default_factory=list)
    active_branches: list[str] = Field(default_factory=list)
    commit_velocity: float = 0.0  # commits per day (last 30 days)
    focus_areas: list[str] = Field(default_factory=list)  # most-edited dirs
    contributors: list[str] = Field(default_factory=list)


class DocumentInsights(BaseModel):
    """Insights extracted from project documentation."""

    model_config = ConfigDict(from_attributes=True)

    project_type: str = ""
    project_stage: str = ""
    target_users: list[str] = Field(default_factory=list)
    key_features: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    priorities_mentioned: list[str] = Field(default_factory=list)
    raw_summary: str = ""


# ── Strategic Context ─────────────────────────────────────────────────

class StrategicContext(BaseModel):
    """Complete strategic context for a project."""

    model_config = ConfigDict(from_attributes=True)

    project_name: str = ""
    project_root: str = "."
    codebase: CodebaseProfile | None = None
    git: GitProfile | None = None
    docs: DocumentInsights | None = None
    goals: GoalSet = Field(default_factory=GoalSet)
    tasks: list[Task] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Scoring Models ────────────────────────────────────────────────────

class DebtContributor(BaseModel):
    """A task contributing to priority debt."""

    model_config = ConfigDict(from_attributes=True)

    task_id: str
    task_title: str
    leverage_score: float
    days_undone: float
    debt_contribution: float
    remediation: str = ""


class PriorityDebtScore(BaseModel):
    """Priority Debt Score with diagnosis."""

    model_config = ConfigDict(from_attributes=True)

    score: float = 0.0  # 0-10000
    severity: str = "green"  # green/yellow/orange/red
    top_contributors: list[DebtContributor] = Field(default_factory=list)
    diagnosis: str = ""
    recommendations: list[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

    @staticmethod
    def severity_for_score(score: float) -> str:
        if score < 500:
            return "green"
        elif score < 2000:
            return "yellow"
        elif score < 5000:
            return "orange"
        return "red"


class PriorityStack(BaseModel):
    """Sorted list of tasks by leverage score."""

    model_config = ConfigDict(from_attributes=True)

    tasks: list[Task] = Field(default_factory=list)
    ranked_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def top(self) -> Task | None:
        return self.tasks[0] if self.tasks else None

    @property
    def top_n(self) -> list[Task]:
        return self.tasks[:3]

    def top_n_average(self, n: int = 3) -> float:
        top = self.tasks[:n]
        if not top:
            return 0.0
        return sum(t.leverage_score for t in top) / len(top)


# ── Drift & Detection ────────────────────────────────────────────────

class DriftAlert(BaseModel):
    """A drift detection alert."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    severity: str  # high/medium/low
    current_task_id: str | None = None
    current_task_title: str = ""
    current_leverage: float = 0.0
    top_task_id: str | None = None
    top_task_title: str = ""
    top_leverage: float = 0.0
    drift_ratio: float = 0.0
    session_minutes: float = 0.0
    message: str = ""
    user_response: str | None = None  # continue/switch/snooze
    snoozed_until: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Decision Logging ─────────────────────────────────────────────────

class DecisionEvent(BaseModel):
    """A logged priority decision."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: DecisionType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: str | None = None
    task_title: str = ""
    from_task_id: str | None = None
    to_task_id: str | None = None
    leverage_score: float | None = None
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Reports ──────────────────────────────────────────────────────────

class GapReport(BaseModel):
    """Goal-to-work gap analysis."""

    model_config = ConfigDict(from_attributes=True)

    goal_id: str
    goal_title: str
    coverage: float = 0.0  # 0-1
    allocated_effort: float = 0.0
    needed_effort: float = 0.0
    severity: str = "low"  # low/medium/high/critical
    orphan_tasks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    """Summary of a development session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: float = 0.0
    tasks_started: list[str] = Field(default_factory=list)
    tasks_completed: list[str] = Field(default_factory=list)
    drift_alerts: int = 0
    pds_start: float = 0.0
    pds_end: float = 0.0
    decisions: list[DecisionEvent] = Field(default_factory=list)
