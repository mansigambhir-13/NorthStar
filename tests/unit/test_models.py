"""Tests for Pydantic models and enums."""

from datetime import datetime

from northstar.analysis.models import (
    CodebaseProfile,
    DebtContributor,
    DecisionEvent,
    DecisionType,
    DriftAlert,
    GapReport,
    Goal,
    GoalSet,
    GoalStatus,
    ModuleInfo,
    PriorityDebtScore,
    PriorityStack,
    SessionSummary,
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)


class TestEnums:
    def test_goal_status_values(self) -> None:
        assert GoalStatus.ACTIVE == "active"
        assert GoalStatus.COMPLETED == "completed"
        assert GoalStatus.DEFERRED == "deferred"
        assert GoalStatus.CANCELLED == "cancelled"

    def test_task_status_values(self) -> None:
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"

    def test_task_source_values(self) -> None:
        assert TaskSource.MANUAL == "manual"
        assert TaskSource.TODO_COMMENT == "todo_comment"
        assert TaskSource.LLM_INFERRED == "llm_inferred"

    def test_urgency_level_values(self) -> None:
        assert UrgencyLevel.BLOCKING == "blocking"
        assert UrgencyLevel.DEADLINE_48H == "deadline_48h"
        assert UrgencyLevel.NORMAL == "normal"

    def test_decision_type_values(self) -> None:
        assert DecisionType.TASK_STARTED == "task_started"
        assert DecisionType.DRIFT_ALERT == "drift_alert"
        assert DecisionType.RERANK == "rerank"


class TestGoalModels:
    def test_goal_creation(self) -> None:
        goal = Goal(id="g1", title="Ship MVP", priority=1)
        assert goal.id == "g1"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.description == ""

    def test_goal_set_primary(self) -> None:
        gs = GoalSet(
            goals=[
                Goal(id="g1", title="Primary", priority=1),
                Goal(id="g2", title="Secondary", priority=2),
            ]
        )
        assert gs.primary is not None
        assert gs.primary.id == "g1"

    def test_goal_set_active_goals(self) -> None:
        gs = GoalSet(
            goals=[
                Goal(id="g1", title="Active", priority=1),
                Goal(id="g2", title="Done", priority=2, status=GoalStatus.COMPLETED),
            ]
        )
        assert len(gs.active_goals) == 1

    def test_goal_set_empty(self) -> None:
        gs = GoalSet()
        assert gs.primary is None
        assert gs.active_goals == []

    def test_goal_json_roundtrip(self) -> None:
        goal = Goal(id="g1", title="Test", priority=1, created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1))
        data = goal.model_dump_json()
        restored = Goal.model_validate_json(data)
        assert restored.id == goal.id
        assert restored.title == goal.title


class TestTaskModels:
    def test_task_defaults(self) -> None:
        task = Task(id="t1", title="Do thing")
        assert task.source == TaskSource.MANUAL
        assert task.status == TaskStatus.PENDING
        assert task.impact == 50
        assert task.effort_hours == 1.0
        assert task.leverage_score == 0.0

    def test_task_with_all_fields(self) -> None:
        task = Task(
            id="t1",
            title="Auth",
            goal_alignment=0.9,
            impact=85,
            urgency=UrgencyLevel.BLOCKING,
            effort_hours=4.0,
            blocks=["t2", "t3"],
        )
        assert task.urgency == UrgencyLevel.BLOCKING
        assert len(task.blocks) == 2

    def test_task_json_roundtrip(self) -> None:
        task = Task(id="t1", title="Test", created_at=datetime(2025, 1, 1), updated_at=datetime(2025, 1, 1))
        data = task.model_dump_json()
        restored = Task.model_validate_json(data)
        assert restored.id == task.id


class TestCodebaseModels:
    def test_module_info(self) -> None:
        m = ModuleInfo(path="src/", language="python", loc=500)
        assert m.complexity_score == 0.0

    def test_codebase_profile(self) -> None:
        cp = CodebaseProfile(root_path="/tmp/project", primary_language="python", total_files=10, total_loc=1000)
        assert cp.total_files == 10
        assert cp.languages == {}

    def test_codebase_profile_json_roundtrip(self) -> None:
        cp = CodebaseProfile(root_path="/tmp", scan_timestamp=datetime(2025, 1, 1))
        data = cp.model_dump_json()
        restored = CodebaseProfile.model_validate_json(data)
        assert restored.root_path == "/tmp"


class TestScoringModels:
    def test_priority_debt_score_severity(self) -> None:
        assert PriorityDebtScore.severity_for_score(0) == "green"
        assert PriorityDebtScore.severity_for_score(499) == "green"
        assert PriorityDebtScore.severity_for_score(500) == "yellow"
        assert PriorityDebtScore.severity_for_score(1999) == "yellow"
        assert PriorityDebtScore.severity_for_score(2000) == "orange"
        assert PriorityDebtScore.severity_for_score(4999) == "orange"
        assert PriorityDebtScore.severity_for_score(5000) == "red"
        assert PriorityDebtScore.severity_for_score(10000) == "red"

    def test_priority_stack_top(self) -> None:
        ps = PriorityStack(
            tasks=[
                Task(id="t1", title="High", leverage_score=9000),
                Task(id="t2", title="Low", leverage_score=100),
            ]
        )
        assert ps.top is not None
        assert ps.top.id == "t1"
        assert len(ps.top_n) == 2

    def test_priority_stack_empty(self) -> None:
        ps = PriorityStack()
        assert ps.top is None
        assert ps.top_n_average() == 0.0

    def test_priority_stack_top_n_average(self) -> None:
        ps = PriorityStack(
            tasks=[
                Task(id="t1", title="A", leverage_score=9000),
                Task(id="t2", title="B", leverage_score=6000),
                Task(id="t3", title="C", leverage_score=3000),
            ]
        )
        assert ps.top_n_average(3) == 6000.0

    def test_debt_contributor(self) -> None:
        dc = DebtContributor(
            task_id="t1", task_title="Auth", leverage_score=8000, days_undone=5.0, debt_contribution=1200.0
        )
        assert dc.remediation == ""


class TestDetectionModels:
    def test_drift_alert(self) -> None:
        alert = DriftAlert(id="da1", severity="high", drift_ratio=0.2, session_minutes=45.0)
        assert alert.user_response is None

    def test_decision_event(self) -> None:
        event = DecisionEvent(id="de1", event_type=DecisionType.TASK_STARTED, task_id="t1")
        assert event.reason == ""


class TestReportModels:
    def test_gap_report(self) -> None:
        gr = GapReport(goal_id="g1", goal_title="MVP", coverage=0.5, severity="medium")
        assert gr.allocated_effort == 0.0

    def test_session_summary(self) -> None:
        ss = SessionSummary(session_id="s1", start_time=datetime(2025, 1, 1))
        assert ss.end_time is None
        assert ss.drift_alerts == 0


class TestStrategicContext:
    def test_strategic_context_defaults(self) -> None:
        ctx = StrategicContext()
        assert ctx.codebase is None
        assert ctx.goals.goals == []
        assert ctx.tasks == []

    def test_strategic_context_json_roundtrip(self) -> None:
        ctx = StrategicContext(
            project_name="test",
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        data = ctx.model_dump_json()
        restored = StrategicContext.model_validate_json(data)
        assert restored.project_name == "test"


class TestValidation:
    def test_task_rejects_invalid_source(self) -> None:
        import pytest as _pt

        with _pt.raises(Exception):
            Task(id="t1", title="X", source="invalid_source")  # type: ignore[arg-type]

    def test_goal_rejects_invalid_status(self) -> None:
        import pytest as _pt

        with _pt.raises(Exception):
            Goal(id="g1", title="X", status="bad_status")  # type: ignore[arg-type]
