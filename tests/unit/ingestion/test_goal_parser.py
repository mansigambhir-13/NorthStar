"""Tests for the goal parser."""

from pathlib import Path

import yaml

from northstar.analysis.models import Goal, GoalSet, GoalStatus
from northstar.ingestion.goal_parser import GoalParser


class TestGoalParser:
    async def test_parse_yaml_file(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        data = {
            "goals": [
                {
                    "id": "g1",
                    "title": "Launch MVP",
                    "description": "Ship to first users",
                    "priority": 1,
                    "success_criteria": ["Signup works", "Core feature done"],
                },
                {
                    "id": "g2",
                    "title": "Add payments",
                    "priority": 2,
                },
            ]
        }
        goals_file.write_text(yaml.dump(data))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert len(goal_set.goals) == 2
        assert goal_set.goals[0].title == "Launch MVP"
        assert goal_set.goals[0].priority == 1
        assert len(goal_set.goals[0].success_criteria) == 2
        assert goal_set.primary is not None
        assert goal_set.primary.id == "g1"

    async def test_parse_simple_list(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        goals_file.write_text(yaml.dump(["Ship MVP", "Add analytics", "Optimize performance"]))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert len(goal_set.goals) == 3
        assert goal_set.goals[0].title == "Ship MVP"

    async def test_parse_flat_list_of_dicts(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        data = [
            {"id": "g1", "title": "First goal", "priority": 1},
            {"id": "g2", "title": "Second goal", "priority": 2},
        ]
        goals_file.write_text(yaml.dump(data))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert len(goal_set.goals) == 2
        assert goal_set.goals[0].title == "First goal"

    async def test_parse_empty_file(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        goals_file.write_text("")

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert len(goal_set.goals) == 0

    async def test_no_file_non_interactive(self, tmp_path: Path) -> None:
        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=None, interactive=False)

        assert len(goal_set.goals) == 0

    async def test_default_goals_yaml(self, tmp_path: Path) -> None:
        default_path = tmp_path / "goals.yaml"
        default_path.write_text(yaml.dump({"goals": [{"id": "g1", "title": "Default goal"}]}))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=None, interactive=False)

        assert len(goal_set.goals) == 1
        assert goal_set.goals[0].title == "Default goal"

    async def test_default_northstar_goals(self, tmp_path: Path) -> None:
        ns_dir = tmp_path / ".northstar"
        ns_dir.mkdir()
        goals_file = ns_dir / "goals.yaml"
        goals_file.write_text(yaml.dump({"goals": [{"id": "g1", "title": "NorthStar goal"}]}))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=None, interactive=False)

        assert len(goal_set.goals) == 1
        assert goal_set.goals[0].title == "NorthStar goal"

    async def test_save_and_reload(self, tmp_path: Path) -> None:
        goals = GoalSet(goals=[
            Goal(id="g1", title="Ship it", priority=1, description="ASAP"),
        ])

        parser = GoalParser(root=tmp_path)
        save_path = tmp_path / "saved_goals.yaml"
        parser.save(goals, path=save_path)

        reloaded = await parser.parse(goals_path=save_path)
        assert len(reloaded.goals) == 1
        assert reloaded.goals[0].title == "Ship it"
        assert reloaded.goals[0].description == "ASAP"

    async def test_goal_with_deadline(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        data = {
            "goals": [{
                "id": "g1",
                "title": "Launch",
                "deadline": "2025-06-01T00:00:00",
            }]
        }
        goals_file.write_text(yaml.dump(data))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert goal_set.goals[0].deadline is not None

    async def test_goal_status_parsing(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        data = {
            "goals": [
                {"id": "g1", "title": "Active", "status": "active"},
                {"id": "g2", "title": "Completed", "status": "completed"},
                {"id": "g3", "title": "Deferred", "status": "deferred"},
            ]
        }
        goals_file.write_text(yaml.dump(data))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert goal_set.goals[0].status == GoalStatus.ACTIVE
        assert goal_set.goals[1].status == GoalStatus.COMPLETED
        assert goal_set.goals[2].status == GoalStatus.DEFERRED

    async def test_active_goals_property(self, tmp_path: Path) -> None:
        goals_file = tmp_path / "goals.yaml"
        data = {
            "goals": [
                {"id": "g1", "title": "Active", "status": "active"},
                {"id": "g2", "title": "Done", "status": "completed"},
            ]
        }
        goals_file.write_text(yaml.dump(data))

        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(goals_path=goals_file)

        assert len(goal_set.active_goals) == 1
        assert goal_set.active_goals[0].id == "g1"

    async def test_missing_file_path(self, tmp_path: Path) -> None:
        parser = GoalParser(root=tmp_path)
        goal_set = await parser.parse(
            goals_path=tmp_path / "nonexistent.yaml", interactive=False
        )

        assert len(goal_set.goals) == 0

    async def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        goals = GoalSet(goals=[
            Goal(id="g1", title="Test"),
        ])

        parser = GoalParser(root=tmp_path)
        save_path = tmp_path / "nested" / "dir" / "goals.yaml"
        parser.save(goals, path=save_path)

        assert save_path.exists()
