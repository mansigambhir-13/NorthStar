"""PipelineManager — orchestrates all NorthStar engines."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from northstar.analysis.models import (
    PriorityDebtScore,
    PriorityStack,
    StrategicContext,
    Task,
    TaskSource,
    TaskStatus,
)
from northstar.config import NorthStarConfig
from northstar.exceptions import InitializationError, NorthStarError

console = Console()


class PipelineManager:
    """Lazy-initializing orchestrator for the NorthStar analysis pipeline."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or ".").resolve()
        self.northstar_dir = self.project_root / ".northstar"
        self._config: NorthStarConfig | None = None
        self._state_manager: Any = None
        self._llm_client: Any = None
        self._initialized = False

    @property
    def config(self) -> NorthStarConfig:
        if self._config is None:
            config_path = self.northstar_dir / "config.yaml"
            self._config = NorthStarConfig.load(config_path)
            self._config.project_root = str(self.project_root)
            if not self._config.project_name:
                self._config.project_name = self.project_root.name
        return self._config

    def _get_llm_client(self) -> Any:
        if self._llm_client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                from northstar.integrations.llm import LLMClient

                self._llm_client = LLMClient(
                    model=self.config.llm.model,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    cache_enabled=self.config.llm.cache_enabled,
                    cache_ttl=self.config.llm.cache_ttl_seconds,
                )
            else:
                from northstar.integrations.llm import NullLLMClient

                self._llm_client = NullLLMClient()
        return self._llm_client

    async def _get_state_manager(self) -> Any:
        if self._state_manager is None:
            from northstar.state.manager import StateManager

            db_path = self.northstar_dir / "state.db"
            context_path = self.northstar_dir / "context.json"
            self._state_manager = StateManager(db_path=db_path, context_path=context_path)
            await self._state_manager.__aenter__()
        return self._state_manager

    async def _cleanup(self) -> None:
        if self._state_manager is not None:
            await self._state_manager.__aexit__(None, None, None)
        if self._llm_client is not None:
            await self._llm_client.close()

    async def initialize(
        self,
        goals_path: Path | None = None,
        interactive: bool = True,
    ) -> dict[str, Any]:
        """Initialize NorthStar for the project: scan, parse goals, build context."""
        self.northstar_dir.mkdir(parents=True, exist_ok=True)

        try:
            from northstar.ingestion.context_builder import ContextBuilder

            builder = ContextBuilder(config=self.config, llm_client=self._get_llm_client())
            context = await builder.build(goals_path=goals_path, interactive=interactive)

            sm = await self._get_state_manager()
            await sm.save_context(context)

            for task in context.tasks:
                await sm.save_task(task)

            self.config.save(self.northstar_dir / "config.yaml")
            self._initialized = True

            return {
                "project_name": context.project_name,
                "total_files": context.codebase.total_files if context.codebase else 0,
                "total_loc": context.codebase.total_loc if context.codebase else 0,
                "goals": len(context.goals.goals),
                "tasks": len(context.tasks),
                "status": "initialized",
            }
        except Exception as e:
            raise InitializationError(f"Failed to initialize: {e}") from e
        finally:
            await self._cleanup()

    async def analyze(self) -> dict[str, Any]:
        """Run full priority analysis: rank tasks, calculate PDS, detect gaps."""
        try:
            sm = await self._get_state_manager()
            context = await sm.load_context()
            if context is None:
                return {"error": "Not initialized. Run 'northstar init' first.", "display": "Not initialized. Run 'northstar init' first."}

            tasks = await sm.get_tasks()
            llm = self._get_llm_client()

            from northstar.analysis.leverage_ranker import LeverageRanker

            ranker = LeverageRanker(config=self.config.scoring, llm_client=llm)
            stack = await ranker.rank(tasks, context.goals)

            for task in stack.tasks:
                await sm.save_task(task)

            from northstar.analysis.priority_debt import PriorityDebtCalculator

            calc = PriorityDebtCalculator(llm_client=llm)
            pds = await calc.calculate(stack.tasks)
            await sm.save_pds(pds)

            from northstar.analysis.gap_analyzer import GapAnalyzer

            gap_analyzer = GapAnalyzer(llm_client=llm)
            gaps = await gap_analyzer.analyze(stack.tasks, context.goals)

            try:
                from northstar.integrations.cursor import CursorIntegration

                cursor = CursorIntegration(project_root=self.project_root)
                cursor.update_cursorrules(pds=pds, stack=stack, goals=context.goals)
            except Exception:
                pass

            display = _format_analysis(pds, stack, gaps)
            return {
                "pds": pds.model_dump(mode="json"),
                "top_tasks": [t.model_dump(mode="json") for t in stack.tasks[:5]],
                "gaps": [g.model_dump(mode="json") for g in gaps],
                "display": display,
            }
        finally:
            await self._cleanup()

    async def quick_check(self) -> dict[str, Any]:
        """Quick drift check on current session."""
        try:
            sm = await self._get_state_manager()
            context = await sm.load_context()
            if context is None:
                return {"display": "Not initialized. Run 'northstar init' first."}

            tasks = await sm.get_tasks()
            pds_record = await sm.get_latest_pds()

            pds_score = pds_record.score if pds_record else 0.0
            severity = PriorityDebtScore.severity_for_score(pds_score)
            active = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

            display = f"PDS: {pds_score:.0f} ({severity})"
            if active:
                display += f" | Active: {active[0].title} (leverage: {active[0].leverage_score:.0f})"

            return {"pds": pds_score, "severity": severity, "active_tasks": len(active), "display": display}
        finally:
            await self._cleanup()

    async def add_and_rank_task(self, task_description: str | None = None) -> dict[str, Any]:
        """Add a task and re-rank all tasks."""
        try:
            sm = await self._get_state_manager()
            context = await sm.load_context()
            if context is None:
                return {"display": "Not initialized. Run 'northstar init' first."}

            if task_description:
                import uuid

                task = Task(
                    id=f"task-{uuid.uuid4().hex[:8]}",
                    title=task_description,
                    source=TaskSource.MANUAL,
                )
                await sm.save_task(task)

            tasks = await sm.get_tasks()
            llm = self._get_llm_client()

            from northstar.analysis.leverage_ranker import LeverageRanker

            ranker = LeverageRanker(config=self.config.scoring, llm_client=llm)
            stack = await ranker.rank(tasks, context.goals)

            for t in stack.tasks:
                await sm.save_task(t)

            return {
                "tasks": [{"title": t.title, "leverage": t.leverage_score} for t in stack.tasks[:10]],
                "display": _format_stack(stack),
            }
        finally:
            await self._cleanup()

    async def generate_report(self, report_type: str = "session") -> dict[str, Any]:
        """Generate a report of the specified type."""
        try:
            sm = await self._get_state_manager()
            llm = self._get_llm_client()

            if report_type == "session":
                from northstar.reporting.debt_report import SessionReportGenerator

                gen = SessionReportGenerator(state_manager=sm, llm_client=llm)
                return await gen.generate()
            elif report_type == "weekly":
                from northstar.reporting.debt_report import WeeklyReportGenerator

                gen = WeeklyReportGenerator(state_manager=sm, llm_client=llm)
                return await gen.generate()
            elif report_type == "retro":
                from northstar.reporting.retrospective import RetrospectiveGenerator

                gen = RetrospectiveGenerator(state_manager=sm, llm_client=llm)
                return await gen.generate()
            else:
                return {"error": f"Unknown report type: {report_type}"}
        finally:
            await self._cleanup()

    async def get_status(self) -> dict[str, Any]:
        """Get current PDS and top priorities."""
        try:
            sm = await self._get_state_manager()
            context = await sm.load_context()
            if context is None:
                return {"display": "Not initialized. Run 'northstar init' first."}

            tasks = await sm.get_tasks()
            pds_record = await sm.get_latest_pds()

            pds_score = pds_record.score if pds_record else 0.0
            severity = PriorityDebtScore.severity_for_score(pds_score)
            pending = sorted(
                [t for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)],
                key=lambda t: t.leverage_score,
                reverse=True,
            )

            display = _format_status(context, pds_score, severity, pending[:5])
            return {
                "project": context.project_name,
                "pds": pds_score,
                "severity": severity,
                "top_tasks": [{"title": t.title, "leverage": t.leverage_score} for t in pending[:5]],
                "display": display,
            }
        finally:
            await self._cleanup()

    async def get_tasks(self) -> dict[str, Any]:
        """Get all tasks with leverage scores."""
        try:
            sm = await self._get_state_manager()
            tasks = await sm.get_tasks()
            tasks_sorted = sorted(tasks, key=lambda t: t.leverage_score, reverse=True)
            display = _format_task_list(tasks_sorted)
            return {
                "tasks": [t.model_dump(mode="json") for t in tasks_sorted],
                "display": display,
            }
        finally:
            await self._cleanup()

    async def get_decisions(self, limit: int = 20) -> dict[str, Any]:
        """Get recent decision log entries."""
        try:
            sm = await self._get_state_manager()
            decisions = await sm.get_decisions(limit=limit)
            lines = []
            for d in decisions:
                lines.append(f"[{d.timestamp.isoformat()[:19]}] {d.event_type.value}: {d.task_title or d.reason}")
            display = "\n".join(lines) if lines else "No decisions logged."
            return {
                "decisions": [d.model_dump(mode="json") for d in decisions],
                "display": display,
            }
        finally:
            await self._cleanup()

    async def get_config(self, key: str | None = None) -> dict[str, Any]:
        """Get configuration."""
        data = self.config.model_dump()
        if key:
            parts = key.split(".")
            current: Any = data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return {"display": f"Unknown config key: {key}"}
            return {"value": current, "display": f"{key} = {current}"}
        import yaml

        display = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return {"config": data, "display": display}

    async def set_config(self, key: str, value: str) -> None:
        """Set a configuration value."""
        sm = await self._get_state_manager()
        await sm.set_config_value(key, value)
        await self._cleanup()

    async def export_all(self, output_path: Path | None = None) -> dict[str, Any]:
        """Export all NorthStar data as JSON."""
        try:
            sm = await self._get_state_manager()
            data = await sm.export_all()
            path = output_path or (self.northstar_dir / "export.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return {"path": str(path), "tables": list(data.keys()), "display": f"Exported to {path}"}
        finally:
            await self._cleanup()

    async def reset(self) -> None:
        """Clear all NorthStar data."""
        try:
            sm = await self._get_state_manager()
            await sm.reset()
        finally:
            await self._cleanup()


# ── Display Helpers ──────────────────────────────────────────────────

def _severity_color(severity: str) -> str:
    return {"green": "green", "yellow": "yellow", "orange": "dark_orange", "red": "red"}.get(severity, "white")


def _format_status(ctx: StrategicContext, pds: float, severity: str, top_tasks: list[Task]) -> str:
    color = _severity_color(severity)
    lines = [
        f"[bold]Project:[/bold] {ctx.project_name}",
        f"[bold]Priority Debt Score:[/bold] [{color}]{pds:.0f} ({severity.upper()})[/{color}]",
        "",
        "[bold]Top Priorities:[/bold]",
    ]
    for i, t in enumerate(top_tasks, 1):
        lines.append(f"  {i}. {t.title} (leverage: {t.leverage_score:.0f})")
    return "\n".join(lines)


def _format_analysis(
    pds: PriorityDebtScore, stack: PriorityStack, gaps: list[Any]
) -> str:
    color = _severity_color(pds.severity)
    lines = [
        f"[bold]Priority Debt Score:[/bold] [{color}]{pds.score:.0f} ({pds.severity.upper()})[/{color}]",
        "",
    ]
    if pds.top_contributors:
        lines.append("[bold]Top Debt Contributors:[/bold]")
        for c in pds.top_contributors[:3]:
            lines.append(f"  - {c.task_title}: {c.debt_contribution:.0f} debt")
    lines.append("")
    lines.append("[bold]Priority Stack:[/bold]")
    for i, t in enumerate(stack.tasks[:5], 1):
        lines.append(f"  {i}. {t.title} (leverage: {t.leverage_score:.0f})")
    return "\n".join(lines)


def _format_stack(stack: PriorityStack) -> str:
    lines = ["[bold]Priority Stack:[/bold]"]
    for i, t in enumerate(stack.tasks[:10], 1):
        lines.append(f"  {i}. {t.title} (leverage: {t.leverage_score:.0f})")
    return "\n".join(lines)


def _format_task_list(tasks: list[Task]) -> str:
    if not tasks:
        return "No tasks found."
    lines = ["[bold]All Tasks:[/bold]"]
    for t in tasks:
        status_icon = {"pending": "○", "in_progress": "◔", "completed": "●"}.get(t.status.value, "?")
        lines.append(f"  {status_icon} {t.title} [{t.status.value}] leverage={t.leverage_score:.0f}")
    return "\n".join(lines)
