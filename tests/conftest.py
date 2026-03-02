"""Shared test fixtures for NorthStar."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from northstar.analysis.models import (
    Goal,
    GoalSet,
    GoalStatus,
    Task,
    TaskSource,
    TaskStatus,
    UrgencyLevel,
)
from northstar.config import NorthStarConfig
from northstar.integrations.llm import NullLLMClient


@pytest.fixture
def sample_config() -> NorthStarConfig:
    return NorthStarConfig(project_name="test-project", project_root="/tmp/test-project")


@pytest.fixture
def sample_goal() -> Goal:
    return Goal(
        id="goal-1",
        title="Launch MVP",
        description="Ship the minimum viable product to first 10 users",
        priority=1,
        status=GoalStatus.ACTIVE,
        success_criteria=["User signup works", "Core feature functional", "Deploy to production"],
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 1),
    )


@pytest.fixture
def sample_goals(sample_goal: Goal) -> GoalSet:
    return GoalSet(
        goals=[
            sample_goal,
            Goal(
                id="goal-2",
                title="Payment Integration",
                description="Integrate Stripe for payment processing",
                priority=2,
                status=GoalStatus.ACTIVE,
                created_at=datetime(2025, 1, 1),
                updated_at=datetime(2025, 1, 1),
            ),
        ]
    )


@pytest.fixture
def sample_tasks() -> list[Task]:
    return [
        Task(
            id="task-1",
            title="Build user authentication",
            description="Implement login/signup flow",
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
            goal_id="goal-1",
            goal_alignment=0.9,
            impact=85,
            urgency=UrgencyLevel.BLOCKING,
            effort_hours=4.0,
            blocks=["task-2", "task-3"],
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
        ),
        Task(
            id="task-2",
            title="Design landing page",
            description="Create the main landing page",
            source=TaskSource.MANUAL,
            status=TaskStatus.PENDING,
            goal_id="goal-1",
            goal_alignment=0.6,
            impact=50,
            urgency=UrgencyLevel.NORMAL,
            effort_hours=2.0,
            created_at=datetime(2025, 1, 2),
            updated_at=datetime(2025, 1, 2),
        ),
        Task(
            id="task-3",
            title="Setup CI/CD pipeline",
            description="Configure GitHub Actions",
            source=TaskSource.TODO_COMMENT,
            status=TaskStatus.PENDING,
            goal_id="goal-1",
            goal_alignment=0.4,
            impact=30,
            urgency=UrgencyLevel.NORMAL,
            effort_hours=3.0,
            created_at=datetime(2025, 1, 3),
            updated_at=datetime(2025, 1, 3),
        ),
    ]


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with basic structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "# TODO: Implement main entry point\ndef main():\n    pass\n"
    )
    (tmp_path / "src" / "utils.py").write_text(
        "def helper():\n    return 42\n"
    )
    (tmp_path / "README.md").write_text(
        "# Test Project\nA simple test project for NorthStar.\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n'
    )
    return tmp_path


@pytest.fixture
def null_llm() -> NullLLMClient:
    return NullLLMClient(
        default_response="This is a test response.",
        default_json={
            "project_type": "web_app",
            "project_stage": "mvp",
            "key_features": ["auth", "dashboard"],
        },
    )
