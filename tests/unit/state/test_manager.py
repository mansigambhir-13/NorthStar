"""Comprehensive tests for StateManager — async SQLite + JSON persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from northstar.analysis.models import (
    DebtContributor,
    DecisionEvent,
    DecisionType,
    DriftAlert,
    GoalSet,
    PriorityDebtScore,
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)
from northstar.exceptions import StateError
from northstar.state.manager import StateManager


# ── Helpers ──────────────────────────────────────────────────────────


def _db_path(tmp_path: Path) -> Path:
    return tmp_path / ".northstar" / "state.db"


def _ctx_path(tmp_path: Path) -> Path:
    return tmp_path / ".northstar" / "context.json"


def _make_manager(tmp_path: Path) -> StateManager:
    return StateManager(db_path=_db_path(tmp_path), context_path=_ctx_path(tmp_path))


def _make_task(id: str = "task-1", **overrides) -> Task:
    defaults = dict(
        id=id,
        title=f"Task {id}",
        description="A test task",
        source=TaskSource.MANUAL,
        status=TaskStatus.PENDING,
        goal_id="goal-1",
        goal_alignment=0.8,
        impact=75,
        urgency=UrgencyLevel.NORMAL,
        effort_hours=2.0,
        blocks=["task-x"],
        leverage_score=500.0,
        reasoning="important",
        created_at=datetime(2025, 6, 1),
        updated_at=datetime(2025, 6, 1),
    )
    defaults.update(overrides)
    return Task(**defaults)


def _make_pds(**overrides) -> PriorityDebtScore:
    defaults = dict(
        score=1200.0,
        severity="yellow",
        top_contributors=[
            DebtContributor(
                task_id="t1",
                task_title="Auth",
                leverage_score=8000,
                days_undone=5.0,
                debt_contribution=600.0,
                remediation="Fix auth ASAP",
            )
        ],
        diagnosis="Moderate debt accumulation",
        recommendations=["Work on auth", "Clear blockers"],
        calculated_at=datetime(2025, 6, 15, 12, 0, 0),
    )
    defaults.update(overrides)
    return PriorityDebtScore(**defaults)


def _make_decision(**overrides) -> DecisionEvent:
    defaults = dict(
        id="dec-1",
        event_type=DecisionType.TASK_STARTED,
        timestamp=datetime(2025, 6, 15, 10, 0, 0),
        task_id="task-1",
        task_title="Auth",
        reason="Highest leverage",
        metadata={"source": "auto"},
    )
    defaults.update(overrides)
    return DecisionEvent(**defaults)


def _make_drift_alert(**overrides) -> DriftAlert:
    defaults = dict(
        id="drift-1",
        severity="high",
        current_task_id="task-2",
        current_task_title="Landing page",
        current_leverage=200.0,
        top_task_id="task-1",
        top_task_title="Auth",
        top_leverage=8000.0,
        drift_ratio=0.025,
        session_minutes=45.0,
        message="You are drifting from the highest-leverage task",
        created_at=datetime(2025, 6, 15, 10, 30, 0),
    )
    defaults.update(overrides)
    return DriftAlert(**defaults)


# ── Async Context Manager ───────────────────────────────────────────


class TestAsyncContextManager:
    async def test_creates_db_and_directory(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            assert _db_path(tmp_path).exists()
            assert (tmp_path / ".northstar").is_dir()

    async def test_sets_wal_mode(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            cursor = await sm.db.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"

    async def test_sets_foreign_keys(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            cursor = await sm.db.execute("PRAGMA foreign_keys")
            row = await cursor.fetchone()
            assert row[0] == 1

    async def test_creates_gitignore(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            gi = tmp_path / ".northstar" / ".gitignore"
            assert gi.exists()
            content = gi.read_text()
            assert "*" in content

    async def test_tables_exist(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            cursor = await sm.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            rows = await cursor.fetchall()
            names = {r[0] for r in rows}
            expected = {"goals", "tasks", "pds_history", "decisions", "drift_alerts", "sessions", "config"}
            assert expected.issubset(names)

    async def test_db_property_raises_when_closed(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        with pytest.raises(StateError):
            _ = sm.db

    async def test_db_closed_after_exit(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            assert sm._db is not None
        assert sm._db is None


# ── Strategic Context (JSON) ────────────────────────────────────────


class TestStrategicContext:
    async def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        ctx = StrategicContext(
            project_name="my-project",
            project_root="/tmp/my-project",
            goals=GoalSet(),
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        )
        async with sm:
            await sm.save_context(ctx)
            loaded = await sm.load_context()

        assert loaded is not None
        assert loaded.project_name == "my-project"
        assert loaded.project_root == "/tmp/my-project"

    async def test_load_returns_none_when_missing(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            result = await sm.load_context()
        assert result is None

    async def test_overwrite_context(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_context(StrategicContext(project_name="v1"))
            await sm.save_context(StrategicContext(project_name="v2"))
            loaded = await sm.load_context()
        assert loaded is not None
        assert loaded.project_name == "v2"


# ── Tasks ────────────────────────────────────────────────────────────


class TestTasks:
    async def test_save_and_get_task(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        task = _make_task()
        async with sm:
            await sm.save_task(task)
            fetched = await sm.get_task("task-1")
        assert fetched is not None
        assert fetched.id == "task-1"
        assert fetched.title == "Task task-1"
        assert fetched.blocks == ["task-x"]
        assert fetched.goal_alignment == 0.8
        assert fetched.urgency == UrgencyLevel.NORMAL

    async def test_get_missing_task_returns_none(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            assert await sm.get_task("nope") is None

    async def test_save_tasks_bulk(self, tmp_path: Path, sample_tasks: list[Task]) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_tasks(sample_tasks)
            all_tasks = await sm.get_tasks()
        assert len(all_tasks) == 3

    async def test_get_tasks_filtered_by_status(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        t1 = _make_task("t1", status=TaskStatus.PENDING)
        t2 = _make_task("t2", status=TaskStatus.IN_PROGRESS)
        t3 = _make_task("t3", status=TaskStatus.COMPLETED, completed_at=datetime(2025, 6, 2))
        async with sm:
            await sm.save_tasks([t1, t2, t3])
            pending = await sm.get_tasks(status=TaskStatus.PENDING)
            completed = await sm.get_tasks(status=TaskStatus.COMPLETED)
        assert len(pending) == 1
        assert pending[0].id == "t1"
        assert len(completed) == 1
        assert completed[0].id == "t3"

    async def test_update_task_status(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        task = _make_task()
        now = datetime(2025, 6, 10, 15, 0, 0)
        async with sm:
            await sm.save_task(task)
            await sm.update_task_status("task-1", TaskStatus.COMPLETED, completed_at=now)
            fetched = await sm.get_task("task-1")
        assert fetched is not None
        assert fetched.status == TaskStatus.COMPLETED
        assert fetched.completed_at is not None
        assert fetched.completed_at.year == 2025

    async def test_upsert_task(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        task_v1 = _make_task(title="Version 1")
        task_v2 = _make_task(title="Version 2", leverage_score=999.0)
        async with sm:
            await sm.save_task(task_v1)
            await sm.save_task(task_v2)
            fetched = await sm.get_task("task-1")
        assert fetched is not None
        assert fetched.title == "Version 2"
        assert fetched.leverage_score == 999.0

    async def test_tasks_ordered_by_leverage(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        low = _make_task("low", leverage_score=10.0)
        high = _make_task("high", leverage_score=9000.0)
        mid = _make_task("mid", leverage_score=500.0)
        async with sm:
            await sm.save_tasks([low, high, mid])
            tasks = await sm.get_tasks()
        assert tasks[0].id == "high"
        assert tasks[-1].id == "low"


# ── Priority Debt Score ──────────────────────────────────────────────


class TestPDS:
    async def test_save_and_get_latest(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        pds = _make_pds()
        async with sm:
            await sm.save_pds(pds)
            latest = await sm.get_latest_pds()
        assert latest is not None
        assert latest.score == 1200.0
        assert latest.severity == "yellow"
        assert len(latest.top_contributors) == 1
        assert latest.top_contributors[0].task_id == "t1"
        assert latest.recommendations == ["Work on auth", "Clear blockers"]

    async def test_get_latest_returns_none_when_empty(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            assert await sm.get_latest_pds() is None

    async def test_latest_returns_most_recent(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        old = _make_pds(score=500.0, calculated_at=datetime(2025, 6, 1))
        new = _make_pds(score=2000.0, calculated_at=datetime(2025, 6, 15))
        async with sm:
            await sm.save_pds(old)
            await sm.save_pds(new)
            latest = await sm.get_latest_pds()
        assert latest is not None
        assert latest.score == 2000.0

    async def test_pds_history_date_range(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        p1 = _make_pds(score=100, calculated_at=datetime(2025, 6, 1))
        p2 = _make_pds(score=200, calculated_at=datetime(2025, 6, 10))
        p3 = _make_pds(score=300, calculated_at=datetime(2025, 6, 20))
        async with sm:
            await sm.save_pds(p1)
            await sm.save_pds(p2)
            await sm.save_pds(p3)

            # Full history
            all_pds = await sm.get_pds_history()
            assert len(all_pds) == 3

            # Start only
            after = await sm.get_pds_history(start=datetime(2025, 6, 5))
            assert len(after) == 2

            # End only
            before = await sm.get_pds_history(end=datetime(2025, 6, 15))
            assert len(before) == 2

            # Both
            between = await sm.get_pds_history(
                start=datetime(2025, 6, 5), end=datetime(2025, 6, 15)
            )
            assert len(between) == 1
            assert between[0].score == 200

    async def test_pds_history_ordered_ascending(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_pds(_make_pds(score=300, calculated_at=datetime(2025, 6, 20)))
            await sm.save_pds(_make_pds(score=100, calculated_at=datetime(2025, 6, 1)))
            history = await sm.get_pds_history()
        assert history[0].score == 100
        assert history[1].score == 300


# ── Decision Events ──────────────────────────────────────────────────


class TestDecisions:
    async def test_log_and_retrieve(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        event = _make_decision()
        async with sm:
            await sm.log_decision(event)
            decisions = await sm.get_decisions()
        assert len(decisions) == 1
        assert decisions[0].id == "dec-1"
        assert decisions[0].event_type == DecisionType.TASK_STARTED
        assert decisions[0].metadata == {"source": "auto"}

    async def test_filter_by_event_type(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        d1 = _make_decision(id="d1", event_type=DecisionType.TASK_STARTED)
        d2 = _make_decision(id="d2", event_type=DecisionType.DRIFT_ALERT)
        d3 = _make_decision(id="d3", event_type=DecisionType.TASK_STARTED)
        async with sm:
            await sm.log_decision(d1)
            await sm.log_decision(d2)
            await sm.log_decision(d3)
            started = await sm.get_decisions(event_type=DecisionType.TASK_STARTED)
            drifts = await sm.get_decisions(event_type=DecisionType.DRIFT_ALERT)
        assert len(started) == 2
        assert len(drifts) == 1

    async def test_filter_by_date_range(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        d1 = _make_decision(id="d1", timestamp=datetime(2025, 6, 1))
        d2 = _make_decision(id="d2", timestamp=datetime(2025, 6, 15))
        d3 = _make_decision(id="d3", timestamp=datetime(2025, 6, 30))
        async with sm:
            await sm.log_decision(d1)
            await sm.log_decision(d2)
            await sm.log_decision(d3)
            mid = await sm.get_decisions(start=datetime(2025, 6, 10), end=datetime(2025, 6, 20))
        assert len(mid) == 1
        assert mid[0].id == "d2"

    async def test_limit(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            for i in range(10):
                d = _make_decision(id=f"d{i}", timestamp=datetime(2025, 6, 1 + i))
                await sm.log_decision(d)
            limited = await sm.get_decisions(limit=3)
        assert len(limited) == 3

    async def test_decisions_ordered_desc(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.log_decision(_make_decision(id="early", timestamp=datetime(2025, 6, 1)))
            await sm.log_decision(_make_decision(id="late", timestamp=datetime(2025, 6, 30)))
            decisions = await sm.get_decisions()
        assert decisions[0].id == "late"
        assert decisions[1].id == "early"


# ── Drift Alerts ─────────────────────────────────────────────────────


class TestDriftAlerts:
    async def test_save_drift_alert(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        alert = _make_drift_alert()
        async with sm:
            await sm.save_drift_alert(alert)
            cursor = await sm.db.execute("SELECT * FROM drift_alerts WHERE id = ?", ("drift-1",))
            row = await cursor.fetchone()
        assert row is not None
        assert row["severity"] == "high"
        assert row["drift_ratio"] == 0.025

    async def test_update_drift_response(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        alert = _make_drift_alert()
        async with sm:
            await sm.save_drift_alert(alert)
            await sm.update_drift_response("drift-1", "switch")
            cursor = await sm.db.execute(
                "SELECT user_response FROM drift_alerts WHERE id = ?", ("drift-1",)
            )
            row = await cursor.fetchone()
        assert row is not None
        assert row["user_response"] == "switch"

    async def test_alert_fields_roundtrip(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        alert = _make_drift_alert()
        async with sm:
            await sm.save_drift_alert(alert)
            cursor = await sm.db.execute("SELECT * FROM drift_alerts WHERE id = ?", ("drift-1",))
            row = await cursor.fetchone()
        assert row["current_task_title"] == "Landing page"
        assert row["top_task_title"] == "Auth"
        assert row["session_minutes"] == 45.0
        assert row["message"] == "You are drifting from the highest-leverage task"


# ── Sessions ─────────────────────────────────────────────────────────


class TestSessions:
    async def test_session_lifecycle(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        start = datetime(2025, 6, 15, 9, 0, 0)
        end = datetime(2025, 6, 15, 10, 30, 0)
        async with sm:
            await sm.save_session_start("sess-1", start)

            # Verify start
            cursor = await sm.db.execute("SELECT * FROM sessions WHERE id = ?", ("sess-1",))
            row = await cursor.fetchone()
            assert row is not None
            assert row["end_time"] is None

            # End session
            await sm.save_session_end(
                "sess-1",
                end_time=end,
                duration_minutes=90.0,
                tasks_started=["task-1", "task-2"],
                tasks_completed=["task-1"],
                drift_alerts=2,
                pds_start=800.0,
                pds_end=600.0,
            )
            cursor = await sm.db.execute("SELECT * FROM sessions WHERE id = ?", ("sess-1",))
            row = await cursor.fetchone()

        assert row is not None
        assert row["duration_minutes"] == 90.0
        assert row["drift_alerts"] == 2
        assert row["pds_start"] == 800.0
        assert row["pds_end"] == 600.0

        # Verify JSON-encoded list fields
        import json

        assert json.loads(row["tasks_started"]) == ["task-1", "task-2"]
        assert json.loads(row["tasks_completed"]) == ["task-1"]

    async def test_session_start_creates_row(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_session_start("s1", datetime(2025, 1, 1))
            cursor = await sm.db.execute("SELECT COUNT(*) FROM sessions")
            count = (await cursor.fetchone())[0]
        assert count == 1


# ── Config ───────────────────────────────────────────────────────────


class TestConfig:
    async def test_set_and_get(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.set_config_value("theme", "dark")
            val = await sm.get_config_value("theme")
        assert val == "dark"

    async def test_get_missing_returns_none(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            assert await sm.get_config_value("nonexistent") is None

    async def test_upsert_config(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.set_config_value("key", "v1")
            await sm.set_config_value("key", "v2")
            val = await sm.get_config_value("key")
        assert val == "v2"

    async def test_multiple_keys(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.set_config_value("a", "1")
            await sm.set_config_value("b", "2")
            await sm.set_config_value("c", "3")
            assert await sm.get_config_value("a") == "1"
            assert await sm.get_config_value("b") == "2"
            assert await sm.get_config_value("c") == "3"


# ── Reset ────────────────────────────────────────────────────────────


class TestReset:
    async def test_reset_clears_all_data(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            # Insert some data
            await sm.save_task(_make_task())
            await sm.save_pds(_make_pds())
            await sm.log_decision(_make_decision())
            await sm.save_drift_alert(_make_drift_alert())
            await sm.set_config_value("x", "y")
            await sm.save_session_start("s1", datetime(2025, 1, 1))

            # Verify data exists
            assert len(await sm.get_tasks()) == 1
            assert await sm.get_latest_pds() is not None

            # Reset
            await sm.reset()

            # Verify all empty
            assert len(await sm.get_tasks()) == 0
            assert await sm.get_latest_pds() is None
            assert len(await sm.get_decisions()) == 0
            assert await sm.get_config_value("x") is None

    async def test_tables_recreated_after_reset(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.reset()
            # Should be able to use normally after reset
            await sm.save_task(_make_task())
            fetched = await sm.get_task("task-1")
        assert fetched is not None


# ── Export ────────────────────────────────────────────────────────────


class TestExport:
    async def test_export_all_empty(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            data = await sm.export_all()
        assert "tasks" in data
        assert "goals" in data
        assert "pds_history" in data
        assert "decisions" in data
        assert "drift_alerts" in data
        assert "sessions" in data
        assert "config" in data
        # All empty
        for table_data in data.values():
            assert len(table_data) == 0

    async def test_export_all_with_data(self, tmp_path: Path) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_task(_make_task("t1"))
            await sm.save_task(_make_task("t2"))
            await sm.save_pds(_make_pds())
            await sm.log_decision(_make_decision())
            await sm.set_config_value("version", "1")
            data = await sm.export_all()
        assert len(data["tasks"]) == 2
        assert len(data["pds_history"]) == 1
        assert len(data["decisions"]) == 1
        assert len(data["config"]) == 1


# ── Integration with conftest fixtures ───────────────────────────────


class TestWithFixtures:
    async def test_sample_tasks_roundtrip(self, tmp_path: Path, sample_tasks: list[Task]) -> None:
        sm = _make_manager(tmp_path)
        async with sm:
            await sm.save_tasks(sample_tasks)
            fetched = await sm.get_tasks()
        assert len(fetched) == len(sample_tasks)
        ids = {t.id for t in fetched}
        assert ids == {"task-1", "task-2", "task-3"}

    async def test_sample_tasks_preserve_fields(self, tmp_path: Path, sample_tasks: list[Task]) -> None:
        sm = _make_manager(tmp_path)
        task = sample_tasks[0]  # task-1: auth, blocking, goal_alignment=0.9
        async with sm:
            await sm.save_task(task)
            fetched = await sm.get_task(task.id)
        assert fetched is not None
        assert fetched.source == TaskSource.MANUAL
        assert fetched.urgency == UrgencyLevel.BLOCKING
        assert fetched.goal_alignment == 0.9
        assert fetched.impact == 85
        assert fetched.blocks == ["task-2", "task-3"]
