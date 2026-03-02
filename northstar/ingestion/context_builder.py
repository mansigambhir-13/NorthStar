"""Context builder — orchestrates all ingestion components to build StrategicContext."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from northstar.analysis.models import (
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
)
from northstar.config import NorthStarConfig
from northstar.exceptions import ContextError
from northstar.ingestion.codebase_scanner import CodebaseScanner
from northstar.ingestion.doc_reader import DocReader
from northstar.ingestion.goal_parser import GoalParser
from northstar.integrations.git import GitAnalyzer

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Orchestrates ingestion components to build a complete StrategicContext."""

    def __init__(self, config: NorthStarConfig, llm_client: Any) -> None:
        self.config = config
        self.llm = llm_client
        self.root = Path(config.project_root).resolve()

    async def build(
        self,
        goals_path: Path | str | None = None,
        interactive: bool = True,
    ) -> StrategicContext:
        """Build complete strategic context by orchestrating all sub-scanners.

        Args:
            goals_path: Optional path to a YAML goals file.
            interactive: Whether to allow interactive goal input.

        Returns:
            Fully assembled StrategicContext.
        """
        try:
            project_name = self._detect_project_name()

            # Run scanners
            scanner = CodebaseScanner(config=self.config.scan, root=self.root)
            codebase = await scanner.scan()

            doc_reader = DocReader(llm_client=self.llm, root=self.root)
            docs = await doc_reader.read()

            git_analyzer = GitAnalyzer(root=self.root)
            git_profile = await git_analyzer.analyze()

            goal_parser = GoalParser(root=self.root)
            goals_path_resolved = Path(goals_path) if goals_path else None
            goals = await goal_parser.parse(
                goals_path=goals_path_resolved, interactive=interactive
            )

            # Extract TODO tasks from scanner results
            tasks = self._extract_todo_tasks(codebase.todos)

            now = datetime.utcnow()
            return StrategicContext(
                project_name=project_name,
                project_root=str(self.root),
                codebase=codebase,
                git=git_profile,
                docs=docs,
                goals=goals,
                tasks=tasks,
                created_at=now,
                updated_at=now,
            )

        except ContextError:
            raise
        except Exception as e:
            raise ContextError(f"Failed to build strategic context: {e}") from e

    def _detect_project_name(self) -> str:
        """Detect project name from pyproject.toml, package.json, or directory name."""
        # Try pyproject.toml (use tomllib if available, else simple regex)
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib  # type: ignore[no-redef]
                    except ImportError:
                        tomllib = None  # type: ignore[assignment]

                if tomllib is not None:
                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                    name = data.get("project", {}).get("name")
                    if name:
                        return name
                else:
                    # Simple fallback: regex parse for name
                    content = pyproject.read_text(encoding="utf-8", errors="replace")
                    for line in content.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("name") and "=" in stripped:
                            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                            if value:
                                return value
            except Exception:
                pass

        # Try package.json
        pkg_json = self.root / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                if isinstance(data, dict) and "name" in data:
                    return data["name"]
            except (OSError, ValueError):
                pass

        # Fall back to config or directory name
        if self.config.project_name:
            return self.config.project_name

        return self.root.name

    def _extract_todo_tasks(self, todos: list[dict[str, Any]]) -> list[Task]:
        """Convert TODO/FIXME comments from codebase scan into Task objects."""
        tasks: list[Task] = []
        for todo in todos:
            task_id = f"todo-{uuid.uuid4().hex[:8]}"
            todo_type = todo.get("type", "TODO")
            text = todo.get("text", "")
            file_path = todo.get("file", "")
            line_number = todo.get("line", 0)

            title = f"[{todo_type}] {text}"
            if len(title) > 120:
                title = title[:117] + "..."

            task = Task(
                id=task_id,
                title=title,
                description=f"{todo_type} comment found in {file_path}:{line_number}",
                source=TaskSource.TODO_COMMENT,
                status=TaskStatus.PENDING,
                file_path=file_path,
                line_number=line_number if line_number else None,
            )
            tasks.append(task)

        return tasks
