"""Tests for the SQLite schema definition."""

from __future__ import annotations

import sqlite3

import pytest

from northstar.state.schema import CREATE_TABLES, SCHEMA_VERSION


class TestSchemaVersion:
    def test_schema_version_is_integer(self) -> None:
        assert isinstance(SCHEMA_VERSION, int)

    def test_schema_version_is_positive(self) -> None:
        assert SCHEMA_VERSION >= 1


class TestCreateTables:
    def test_sql_is_valid(self) -> None:
        """Execute CREATE_TABLES against an in-memory SQLite to verify syntax."""
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
        finally:
            conn.close()

    def test_all_expected_tables_exist(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"goals", "tasks", "pds_history", "decisions", "drift_alerts", "sessions", "config"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_indexes_created(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected_indexes = {
            "idx_tasks_status",
            "idx_tasks_goal_id",
            "idx_decisions_timestamp",
            "idx_decisions_event_type",
            "idx_pds_history_calculated_at",
            "idx_drift_alerts_created_at",
        }
        assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"

    def test_tasks_has_goal_id_column(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]
        finally:
            conn.close()

        assert "goal_id" in columns, "tasks should have goal_id column"

    def test_idempotent_creation(self) -> None:
        """Running CREATE_TABLES twice should not error (IF NOT EXISTS)."""
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            conn.executescript(CREATE_TABLES)  # second time — must not fail
        finally:
            conn.close()

    def test_goals_columns(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute("PRAGMA table_info(goals)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"id", "title", "description", "priority", "status", "deadline",
                    "success_criteria", "created_at", "updated_at"}
        assert expected.issubset(columns)

    def test_tasks_columns(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"id", "title", "description", "source", "status", "goal_id",
                    "goal_alignment", "impact", "urgency", "effort_hours", "blocks",
                    "leverage_score", "reasoning", "file_path", "line_number",
                    "created_at", "updated_at", "completed_at"}
        assert expected.issubset(columns)

    def test_pds_history_columns(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute("PRAGMA table_info(pds_history)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"id", "score", "severity", "top_contributors", "diagnosis",
                    "recommendations", "calculated_at"}
        assert expected.issubset(columns)

    def test_sessions_columns(self) -> None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(CREATE_TABLES)
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            conn.close()

        expected = {"id", "start_time", "end_time", "duration_minutes",
                    "tasks_started", "tasks_completed", "drift_alerts",
                    "pds_start", "pds_end"}
        assert expected.issubset(columns)
