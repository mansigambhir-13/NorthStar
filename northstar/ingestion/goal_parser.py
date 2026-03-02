"""Goal parser — reads, validates, and manages project goals from YAML."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from northstar.analysis.models import Goal, GoalSet, GoalStatus

logger = logging.getLogger(__name__)


class GoalParser:
    """Parses project goals from YAML files or interactive input."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    async def parse(
        self, goals_path: Path | None = None, interactive: bool = True
    ) -> GoalSet:
        """Parse goals from a YAML file, interactive input, or return empty set.

        Args:
            goals_path: Path to a YAML file containing goals. If None, looks for
                        default locations or falls back to interactive/empty.
            interactive: If True and no file found, prompt user for a goal.

        Returns:
            GoalSet with parsed goals.
        """
        # If explicit path provided, load it
        if goals_path is not None:
            path = Path(goals_path)
            if not path.is_absolute():
                path = self.root / path
            if path.exists():
                return self._load_yaml(path)
            logger.warning(f"Goals file not found: {path}")

        # Try default locations
        for default_name in (".northstar/goals.yaml", ".northstar/goals.yml", "goals.yaml"):
            default_path = self.root / default_name
            if default_path.exists():
                return self._load_yaml(default_path)

        # No file found — interactive or empty
        if interactive:
            return await self._interactive_goal()

        return GoalSet()

    def save(self, goals: GoalSet, path: Path) -> None:
        """Save a GoalSet to a YAML file."""
        path = Path(path)
        if not path.is_absolute():
            path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)

        data = []
        for goal in goals.goals:
            entry: dict[str, Any] = {
                "id": goal.id,
                "title": goal.title,
                "description": goal.description,
                "priority": goal.priority,
                "status": goal.status.value,
            }
            if goal.deadline is not None:
                entry["deadline"] = goal.deadline.isoformat()
            if goal.success_criteria:
                entry["success_criteria"] = goal.success_criteria
            data.append(entry)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Saved {len(data)} goals to {path}")

    def _load_yaml(self, path: Path) -> GoalSet:
        """Load and validate goals from a YAML file.

        Supports three formats:
        1. List of dicts: [{id: g1, title: "..."}, ...]
        2. Dict with "goals" key: {goals: [{id: g1, title: "..."}, ...]}
        3. List of strings: ["Ship MVP", "Add analytics"]
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML from {path}: {e}")
            return GoalSet()

        if data is None:
            return GoalSet()

        # Handle {"goals": [...]} wrapper format
        if isinstance(data, dict) and "goals" in data:
            data = data["goals"]

        if not isinstance(data, list):
            logger.error(f"Expected a list of goals in {path}, got {type(data).__name__}")
            return GoalSet()

        goals: list[Goal] = []
        for i, entry in enumerate(data):
            if isinstance(entry, str):
                # Simple string format: treat as goal title
                goal = Goal(
                    id=f"goal-{uuid.uuid4().hex[:8]}",
                    title=entry,
                    priority=i + 1,
                )
                goals.append(goal)
            elif isinstance(entry, dict):
                try:
                    goal = self._parse_goal_entry(entry)
                    goals.append(goal)
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping invalid goal entry at index {i}: {e}")
            else:
                logger.warning(f"Skipping unrecognized goal entry at index {i}: {type(entry)}")

        logger.info(f"Loaded {len(goals)} goals from {path}")
        return GoalSet(goals=goals)

    def _parse_goal_entry(self, entry: dict[str, Any]) -> Goal:
        """Parse a single goal dict into a Goal model."""
        goal_id = entry.get("id", f"goal-{uuid.uuid4().hex[:8]}")
        title = entry.get("title", "")
        if not title:
            raise ValueError("Goal must have a title")

        description = entry.get("description", "")
        priority = int(entry.get("priority", 1))

        status_str = entry.get("status", "active")
        try:
            status = GoalStatus(status_str)
        except ValueError:
            status = GoalStatus.ACTIVE

        deadline = None
        deadline_raw = entry.get("deadline")
        if deadline_raw is not None:
            if isinstance(deadline_raw, datetime):
                deadline = deadline_raw
            elif isinstance(deadline_raw, str):
                try:
                    deadline = datetime.fromisoformat(deadline_raw)
                except ValueError:
                    logger.warning(f"Invalid deadline format: {deadline_raw}")

        success_criteria = entry.get("success_criteria", [])
        if not isinstance(success_criteria, list):
            success_criteria = [str(success_criteria)]

        return Goal(
            id=goal_id,
            title=title,
            description=description,
            priority=priority,
            status=status,
            deadline=deadline,
            success_criteria=success_criteria,
        )

    async def _interactive_goal(self) -> GoalSet:
        """Prompt the user interactively for a single primary goal."""
        try:
            from rich.prompt import Prompt

            title = Prompt.ask("[bold]What is your primary project goal?[/bold]")
            if not title.strip():
                return GoalSet()

            description = Prompt.ask(
                "[bold]Describe this goal briefly[/bold]", default=""
            )
            priority_str = Prompt.ask(
                "[bold]Priority (1=highest)[/bold]", default="1"
            )
            try:
                priority = int(priority_str)
            except ValueError:
                priority = 1

            goal = Goal(
                id=f"goal-{uuid.uuid4().hex[:8]}",
                title=title.strip(),
                description=description.strip(),
                priority=priority,
            )
            return GoalSet(goals=[goal])

        except (ImportError, EOFError, KeyboardInterrupt):
            logger.info("Interactive goal input unavailable or cancelled")
            return GoalSet()
