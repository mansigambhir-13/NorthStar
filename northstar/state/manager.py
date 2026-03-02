"""State manager for NorthStar — async SQLite + JSON persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from northstar.analysis.models import (
    DebtContributor,
    DecisionEvent,
    DecisionType,
    DriftAlert,
    PriorityDebtScore,
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)
from northstar.exceptions import StateError
from northstar.state.schema import CREATE_TABLES

logger = logging.getLogger(__name__)

# Gitignore content for the .northstar directory
_GITIGNORE_CONTENT = """\
# NorthStar state — machine-local, not committed
*
!.gitignore
"""


def _json_dumps(obj: Any) -> str:
    """Serialize a Python object to a JSON string."""
    return json.dumps(obj, default=str)


def _json_loads(raw: str | None) -> Any:
    """Deserialize a JSON string; returns default on None/empty."""
    if not raw:
        return None
    return json.loads(raw)


def _iso(dt: datetime | None) -> str | None:
    """Convert a datetime to ISO-8601 string, or None."""
    if dt is None:
        return None
    return dt.isoformat()


def _from_iso(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 string to datetime, or None."""
    if not raw:
        return None
    return datetime.fromisoformat(raw)


class StateManager:
    """Async context manager for NorthStar state persistence.

    Dual-persistence:
      - SQLite (WAL mode, foreign keys) for structured data
      - ``context.json`` file for the full StrategicContext
    """

    def __init__(
        self,
        db_path: str | Path = ".northstar/state.db",
        context_path: str | Path = ".northstar/context.json",
    ) -> None:
        self.db_path = Path(db_path)
        self.context_path = Path(context_path)
        self._db: aiosqlite.Connection | None = None

    # ── Async context manager ────────────────────────────────────────

    async def __aenter__(self) -> StateManager:
        # Ensure the .northstar directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_path.parent.mkdir(parents=True, exist_ok=True)

        # Write a .gitignore so state files are not committed
        gitignore = self.db_path.parent / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(_GITIGNORE_CONTENT)

        # Open the database
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row

        # Enable WAL mode and foreign keys
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

        # Create tables
        await self._db.executescript(CREATE_TABLES)
        await self._db.commit()

        logger.info("StateManager opened: %s", self.db_path)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise StateError("StateManager is not open — use 'async with StateManager() as sm:'")
        return self._db

    # ── Strategic Context (JSON file) ────────────────────────────────

    async def save_context(self, ctx: StrategicContext) -> None:
        """Persist StrategicContext to a JSON file."""
        data = ctx.model_dump_json(indent=2)
        self.context_path.parent.mkdir(parents=True, exist_ok=True)
        self.context_path.write_text(data)

    async def load_context(self) -> StrategicContext | None:
        """Load StrategicContext from the JSON file, or None if absent."""
        if not self.context_path.exists():
            return None
        raw = self.context_path.read_text()
        if not raw.strip():
            return None
        return StrategicContext.model_validate_json(raw)

    # ── Tasks ────────────────────────────────────────────────────────

    async def save_task(self, task: Task) -> None:
        """Insert or replace a single task."""
        await self.db.execute(
            """INSERT OR REPLACE INTO tasks
               (id, title, description, source, status, goal_id, goal_alignment,
                impact, urgency, effort_hours, blocks, leverage_score, reasoning,
                file_path, line_number, created_at, updated_at, completed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                task.id,
                task.title,
                task.description,
                task.source.value,
                task.status.value,
                task.goal_id,
                task.goal_alignment,
                task.impact,
                task.urgency.value,
                task.effort_hours,
                _json_dumps(task.blocks),
                task.leverage_score,
                task.reasoning,
                task.file_path,
                task.line_number,
                _iso(task.created_at),
                _iso(task.updated_at),
                _iso(task.completed_at),
            ),
        )
        await self.db.commit()

    async def save_tasks(self, tasks: list[Task]) -> None:
        """Bulk-insert or replace multiple tasks."""
        for task in tasks:
            await self.db.execute(
                """INSERT OR REPLACE INTO tasks
                   (id, title, description, source, status, goal_id, goal_alignment,
                    impact, urgency, effort_hours, blocks, leverage_score, reasoning,
                    file_path, line_number, created_at, updated_at, completed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    task.id,
                    task.title,
                    task.description,
                    task.source.value,
                    task.status.value,
                    task.goal_id,
                    task.goal_alignment,
                    task.impact,
                    task.urgency.value,
                    task.effort_hours,
                    _json_dumps(task.blocks),
                    task.leverage_score,
                    task.reasoning,
                    task.file_path,
                    task.line_number,
                    _iso(task.created_at),
                    _iso(task.updated_at),
                    _iso(task.completed_at),
                ),
            )
        await self.db.commit()

    def _row_to_task(self, row: aiosqlite.Row) -> Task:
        """Convert a database row to a Task model."""
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            source=TaskSource(row["source"]),
            status=TaskStatus(row["status"]),
            goal_id=row["goal_id"],
            goal_alignment=row["goal_alignment"],
            impact=row["impact"],
            urgency=UrgencyLevel(row["urgency"]),
            effort_hours=row["effort_hours"],
            blocks=_json_loads(row["blocks"]) or [],
            leverage_score=row["leverage_score"],
            reasoning=row["reasoning"] or "",
            file_path=row["file_path"],
            line_number=row["line_number"],
            created_at=_from_iso(row["created_at"]),  # type: ignore[arg-type]
            updated_at=_from_iso(row["updated_at"]),  # type: ignore[arg-type]
            completed_at=_from_iso(row["completed_at"]),
        )

    async def get_task(self, task_id: str) -> Task | None:
        """Retrieve a task by ID, or None."""
        cursor = await self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    async def get_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """List tasks, optionally filtered by status."""
        if status is not None:
            cursor = await self.db.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY leverage_score DESC",
                (status.value,),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM tasks ORDER BY leverage_score DESC"
            )
        rows = await cursor.fetchall()
        return [self._row_to_task(r) for r in rows]

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        completed_at: datetime | None = None,
    ) -> None:
        """Update a task's status (and optionally completed_at)."""
        now = datetime.utcnow()
        await self.db.execute(
            "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (status.value, _iso(completed_at), _iso(now), task_id),
        )
        await self.db.commit()

    # ── Priority Debt Score ──────────────────────────────────────────

    async def save_pds(self, pds: PriorityDebtScore) -> None:
        """Insert a PDS snapshot into pds_history."""
        contributors = [c.model_dump() for c in pds.top_contributors]
        await self.db.execute(
            """INSERT INTO pds_history
               (score, severity, top_contributors, diagnosis, recommendations, calculated_at)
               VALUES (?,?,?,?,?,?)""",
            (
                pds.score,
                pds.severity,
                _json_dumps(contributors),
                pds.diagnosis,
                _json_dumps(pds.recommendations),
                _iso(pds.calculated_at),
            ),
        )
        await self.db.commit()

    def _row_to_pds(self, row: aiosqlite.Row) -> PriorityDebtScore:
        """Convert a database row to a PriorityDebtScore."""
        raw_contributors = _json_loads(row["top_contributors"]) or []
        contributors = [DebtContributor(**c) for c in raw_contributors]
        return PriorityDebtScore(
            score=row["score"],
            severity=row["severity"],
            top_contributors=contributors,
            diagnosis=row["diagnosis"] or "",
            recommendations=_json_loads(row["recommendations"]) or [],
            calculated_at=_from_iso(row["calculated_at"]),  # type: ignore[arg-type]
        )

    async def get_latest_pds(self) -> PriorityDebtScore | None:
        """Get the most recent PDS entry."""
        cursor = await self.db.execute(
            "SELECT * FROM pds_history ORDER BY calculated_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_pds(row)

    async def get_pds_history(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PriorityDebtScore]:
        """Get PDS history, optionally bounded by date range."""
        query = "SELECT * FROM pds_history"
        params: list[str] = []
        clauses: list[str] = []
        if start is not None:
            clauses.append("calculated_at >= ?")
            params.append(_iso(start))  # type: ignore[arg-type]
        if end is not None:
            clauses.append("calculated_at <= ?")
            params.append(_iso(end))  # type: ignore[arg-type]
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY calculated_at ASC"
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_pds(r) for r in rows]

    # ── Decision Events ──────────────────────────────────────────────

    async def log_decision(self, event: DecisionEvent) -> None:
        """Insert a decision event."""
        await self.db.execute(
            """INSERT INTO decisions
               (id, event_type, timestamp, task_id, task_title,
                from_task_id, to_task_id, leverage_score, reason, metadata)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                event.id,
                event.event_type.value,
                _iso(event.timestamp),
                event.task_id,
                event.task_title,
                event.from_task_id,
                event.to_task_id,
                event.leverage_score,
                event.reason,
                _json_dumps(event.metadata),
            ),
        )
        await self.db.commit()

    async def get_decisions(
        self,
        limit: int = 50,
        event_type: DecisionType | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[DecisionEvent]:
        """Query decision events with optional filters."""
        query = "SELECT * FROM decisions"
        params: list[Any] = []
        clauses: list[str] = []
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type.value)
        if start is not None:
            clauses.append("timestamp >= ?")
            params.append(_iso(start))
        if end is not None:
            clauses.append("timestamp <= ?")
            params.append(_iso(end))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            DecisionEvent(
                id=r["id"],
                event_type=DecisionType(r["event_type"]),
                timestamp=_from_iso(r["timestamp"]),  # type: ignore[arg-type]
                task_id=r["task_id"],
                task_title=r["task_title"] or "",
                from_task_id=r["from_task_id"],
                to_task_id=r["to_task_id"],
                leverage_score=r["leverage_score"],
                reason=r["reason"] or "",
                metadata=_json_loads(r["metadata"]) or {},
            )
            for r in rows
        ]

    # ── Drift Alerts ─────────────────────────────────────────────────

    async def save_drift_alert(self, alert: DriftAlert) -> None:
        """Insert a drift alert."""
        await self.db.execute(
            """INSERT INTO drift_alerts
               (id, severity, current_task_id, current_task_title, current_leverage,
                top_task_id, top_task_title, top_leverage, drift_ratio,
                session_minutes, message, user_response, snoozed_until, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                alert.id,
                alert.severity,
                alert.current_task_id,
                alert.current_task_title,
                alert.current_leverage,
                alert.top_task_id,
                alert.top_task_title,
                alert.top_leverage,
                alert.drift_ratio,
                alert.session_minutes,
                alert.message,
                alert.user_response,
                _iso(alert.snoozed_until),
                _iso(alert.created_at),
            ),
        )
        await self.db.commit()

    async def update_drift_response(self, alert_id: str, response: str) -> None:
        """Record a user's response to a drift alert."""
        await self.db.execute(
            "UPDATE drift_alerts SET user_response = ? WHERE id = ?",
            (response, alert_id),
        )
        await self.db.commit()

    # ── Sessions ─────────────────────────────────────────────────────

    async def save_session_start(self, session_id: str, start_time: datetime) -> None:
        """Begin tracking a session."""
        await self.db.execute(
            """INSERT INTO sessions
               (id, start_time, tasks_started, tasks_completed)
               VALUES (?,?,?,?)""",
            (session_id, _iso(start_time), "[]", "[]"),
        )
        await self.db.commit()

    async def save_session_end(
        self,
        session_id: str,
        end_time: datetime,
        duration_minutes: float = 0.0,
        tasks_started: list[str] | None = None,
        tasks_completed: list[str] | None = None,
        drift_alerts: int = 0,
        pds_start: float = 0.0,
        pds_end: float = 0.0,
    ) -> None:
        """Finalize a session with summary data."""
        await self.db.execute(
            """UPDATE sessions SET
                 end_time = ?,
                 duration_minutes = ?,
                 tasks_started = ?,
                 tasks_completed = ?,
                 drift_alerts = ?,
                 pds_start = ?,
                 pds_end = ?
               WHERE id = ?""",
            (
                _iso(end_time),
                duration_minutes,
                _json_dumps(tasks_started or []),
                _json_dumps(tasks_completed or []),
                drift_alerts,
                pds_start,
                pds_end,
                session_id,
            ),
        )
        await self.db.commit()

    # ── Config key-value ─────────────────────────────────────────────

    async def get_config_value(self, key: str) -> str | None:
        """Get a config value by key, or None."""
        cursor = await self.db.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return row["value"]

    async def set_config_value(self, key: str, value: str) -> None:
        """Set a config key-value pair (upsert)."""
        now = datetime.utcnow().isoformat()
        await self.db.execute(
            "INSERT OR REPLACE INTO config (key, value, updated_at) VALUES (?,?,?)",
            (key, value, now),
        )
        await self.db.commit()

    # ── Maintenance ──────────────────────────────────────────────────

    async def reset(self) -> None:
        """Drop all tables and recreate them. Destructive."""
        tables = ["config", "sessions", "drift_alerts", "decisions", "pds_history", "tasks", "goals"]
        for table in tables:
            await self.db.execute(f"DROP TABLE IF EXISTS {table}")  # noqa: S608
        # Also drop indexes (they go away with tables, but be explicit)
        await self.db.executescript(CREATE_TABLES)
        await self.db.commit()
        logger.warning("StateManager: all tables reset")

    async def export_all(self) -> dict[str, list[dict[str, Any]]]:
        """Export every table as a dict of lists."""
        result: dict[str, list[dict[str, Any]]] = {}
        tables = ["goals", "tasks", "pds_history", "decisions", "drift_alerts", "sessions", "config"]
        for table in tables:
            cursor = await self.db.execute(f"SELECT * FROM {table}")  # noqa: S608
            rows = await cursor.fetchall()
            result[table] = [dict(r) for r in rows]
        return result
