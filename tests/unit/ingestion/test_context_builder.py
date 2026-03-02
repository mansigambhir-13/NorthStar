"""Tests for the context builder."""

import subprocess
from pathlib import Path

import yaml

from northstar.analysis.models import TaskSource
from northstar.config import NorthStarConfig
from northstar.ingestion.context_builder import ContextBuilder
from northstar.integrations.llm import NullLLMClient


class TestContextBuilder:
    async def test_build_context(self, tmp_path: Path) -> None:
        # Setup a mini project
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("# TODO: Implement entry point\ndef main():\n    pass\n")
        (tmp_path / "README.md").write_text("# Test Project\n")

        goals_file = tmp_path / "goals.yaml"
        goals_file.write_text(yaml.dump({
            "goals": [{"id": "g1", "title": "Ship MVP", "priority": 1}]
        }))

        config = NorthStarConfig(project_root=str(tmp_path), project_name="test")
        llm = NullLLMClient(default_json={
            "project_type": "cli_tool",
            "raw_summary": "Test project.",
        })

        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(goals_path=goals_file, interactive=False)

        assert context.project_name != ""
        assert context.codebase is not None
        assert context.codebase.total_files >= 1
        assert len(context.goals.goals) == 1
        assert context.goals.primary is not None
        assert context.goals.primary.title == "Ship MVP"

    async def test_todo_extraction(self, tmp_path: Path) -> None:
        (tmp_path / "code.py").write_text("# TODO: Fix auth\ndef auth():\n    pass\n")

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        todo_tasks = [t for t in context.tasks if t.source == TaskSource.TODO_COMMENT]
        assert len(todo_tasks) >= 1
        assert any("Fix auth" in t.title for t in todo_tasks)

    async def test_todo_tasks_have_file_info(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("# TODO: Add validation\nx = 1\n")

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        todo_tasks = [t for t in context.tasks if t.source == TaskSource.TODO_COMMENT]
        assert len(todo_tasks) >= 1
        task = todo_tasks[0]
        assert task.file_path is not None
        assert task.line_number is not None

    async def test_project_name_detection(self, tmp_path: Path) -> None:
        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.project_name == tmp_path.name

    async def test_project_name_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "my-cool-project"\nversion = "1.0.0"\n'
        )

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.project_name == "my-cool-project"

    async def test_project_name_from_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "js-project", "version": "1.0.0"}')

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.project_name == "js-project"

    async def test_with_git_repo(self, tmp_path: Path) -> None:
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
        (tmp_path / "main.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.git is not None
        assert context.git.total_commits >= 1

    async def test_docs_insights(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# My API\nREST API for widgets.\n")

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient(default_json={
            "project_type": "api_service",
            "project_stage": "mvp",
            "key_features": ["REST API"],
            "raw_summary": "Widget API.",
        })
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.docs is not None
        assert context.docs.project_type == "api_service"

    async def test_empty_project(self, tmp_path: Path) -> None:
        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert context.codebase is not None
        assert context.codebase.total_files == 0
        assert context.tasks == []
        assert context.goals.goals == []

    async def test_context_has_project_root(self, tmp_path: Path) -> None:
        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient()
        builder = ContextBuilder(config=config, llm_client=llm)
        context = await builder.build(interactive=False)

        assert str(tmp_path.resolve()) in context.project_root

    async def test_uses_null_llm(self, tmp_path: Path) -> None:
        """Integration test: NullLLMClient records calls and returns defaults."""
        (tmp_path / "README.md").write_text("# Test\n")

        config = NorthStarConfig(project_root=str(tmp_path))
        llm = NullLLMClient(default_json={"project_type": "test"})
        builder = ContextBuilder(config=config, llm_client=llm)
        await builder.build(interactive=False)

        # NullLLMClient should have been called for doc reading
        assert len(llm.calls) == 1
