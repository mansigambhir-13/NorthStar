"""Tests for REST API endpoints using FastAPI TestClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from northstar.web.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_pm():
    """Patch PipelineManager to return canned data."""
    with patch("northstar.web.api.PipelineManager") as MockPM:
        pm = AsyncMock()
        MockPM.return_value = pm
        yield pm


class TestStatusEndpoint:
    def test_get_status(self, client, mock_pm):
        mock_pm.get_status.return_value = {
            "project": "test",
            "pds": 500.0,
            "severity": "yellow",
            "top_tasks": [{"title": "Auth", "leverage": 8000}],
            "display": "PDS: 500",
        }
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pds"] == 500.0
        assert data["severity"] == "yellow"


class TestAnalyzeEndpoint:
    def test_post_analyze(self, client, mock_pm):
        mock_pm.analyze.return_value = {
            "pds": {"score": 1200},
            "top_tasks": [],
            "gaps": [],
            "display": "Analysis done",
        }
        resp = client.post("/api/analyze")
        assert resp.status_code == 200
        assert "pds" in resp.json()


class TestCheckEndpoint:
    def test_get_check(self, client, mock_pm):
        mock_pm.quick_check.return_value = {
            "pds": 100.0,
            "severity": "green",
            "active_tasks": 0,
            "display": "PDS: 100",
        }
        resp = client.get("/api/check")
        assert resp.status_code == 200
        assert resp.json()["severity"] == "green"


class TestTasksEndpoints:
    def test_get_tasks(self, client, mock_pm):
        mock_pm.get_tasks.return_value = {
            "tasks": [{"id": "t-1", "title": "Task 1", "leverage_score": 500}],
            "display": "Tasks",
        }
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 1

    def test_add_task(self, client, mock_pm):
        mock_pm.add_and_rank_task.return_value = {
            "tasks": [{"title": "New task", "leverage": 100}],
            "display": "Ranked",
        }
        resp = client.post("/api/tasks", json={"description": "New task"})
        assert resp.status_code == 200

    def test_add_task_empty(self, client, mock_pm):
        """POST with empty description should still work (validation at pipeline level)."""
        mock_pm.add_and_rank_task.return_value = {"tasks": [], "display": ""}
        resp = client.post("/api/tasks", json={"description": ""})
        assert resp.status_code == 200


class TestPDSEndpoints:
    def test_get_pds_no_data(self, client, mock_pm):
        # Mock state manager with no PDS
        sm = AsyncMock()
        sm.get_latest_pds.return_value = None
        mock_pm._get_state_manager.return_value = sm
        mock_pm._cleanup = AsyncMock()

        resp = client.get("/api/pds")
        assert resp.status_code == 200
        assert resp.json()["score"] == 0

    def test_get_pds_history(self, client, mock_pm):
        sm = AsyncMock()
        sm.get_pds_history.return_value = []
        mock_pm._get_state_manager.return_value = sm
        mock_pm._cleanup = AsyncMock()

        resp = client.get("/api/pds/history")
        assert resp.status_code == 200
        assert resp.json()["history"] == []


class TestDecisionsEndpoint:
    def test_get_decisions(self, client, mock_pm):
        mock_pm.get_decisions.return_value = {
            "decisions": [],
            "display": "No decisions logged.",
        }
        resp = client.get("/api/decisions")
        assert resp.status_code == 200


class TestReportsEndpoint:
    def test_generate_valid_report(self, client, mock_pm):
        mock_pm.generate_report.return_value = {"path": "/tmp/report.md"}
        resp = client.post("/api/reports/session")
        assert resp.status_code == 200

    def test_generate_invalid_report(self, client, mock_pm):
        resp = client.post("/api/reports/invalid")
        assert resp.status_code == 400


class TestConfigEndpoints:
    def test_get_config(self, client, mock_pm):
        mock_pm.get_config.return_value = {
            "config": {"project_name": "test"},
            "display": "project_name: test",
        }
        resp = client.get("/api/config")
        assert resp.status_code == 200

    def test_set_config(self, client, mock_pm):
        mock_pm.set_config = AsyncMock()
        resp = client.put("/api/config/project_name", json={"value": "new-name"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestInitEndpoint:
    def test_post_init(self, client, mock_pm):
        mock_pm.initialize.return_value = {
            "project_name": "test",
            "goals": 2,
            "tasks": 5,
            "status": "initialized",
        }
        resp = client.post("/api/init")
        assert resp.status_code == 200
        assert resp.json()["status"] == "initialized"


class TestGoalsEndpoint:
    def test_get_goals_not_initialized(self, client, mock_pm):
        sm = AsyncMock()
        sm.load_context.return_value = None
        mock_pm._get_state_manager.return_value = sm
        mock_pm._cleanup = AsyncMock()

        resp = client.get("/api/goals")
        assert resp.status_code == 200
        assert resp.json()["goals"] == []
