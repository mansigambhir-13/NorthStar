"""NorthStar CLI — all commands defined via Typer."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from northstar import __version__
from northstar.exceptions import NorthStarError

app = typer.Typer(
    name="northstar",
    help="NorthStar — The Priority Debt Engine. Measures priority debt and keeps you focused on high-leverage work.",
    no_args_is_help=True,
)
console = Console()


def _run(coro):  # type: ignore[no-untyped-def]
    """Bridge async coroutines to sync Typer commands."""
    try:
        return asyncio.run(coro)
    except NorthStarError as e:
        console.print(Panel(str(e), title="NorthStar Error", border_style="red"))
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        raise typer.Exit(code=130) from None


def version_callback(value: bool) -> None:
    if value:
        console.print(f"northstar {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(None, "--version", "-v", callback=version_callback, is_eager=True),
) -> None:
    """NorthStar — The Priority Debt Engine."""


@app.command()
def init(
    goals: Optional[Path] = typer.Option(None, "--goals", "-g", help="Path to goals YAML file"),
    no_interactive: bool = typer.Option(False, "--no-interactive", help="Skip interactive prompts"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Initialize NorthStar for the current project."""
    from northstar.pipeline import PipelineManager

    async def _init() -> None:
        pm = PipelineManager()
        result = await pm.initialize(goals_path=goals, interactive=not no_interactive)
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print("[green]NorthStar initialized successfully.[/green]")

    _run(_init())


@app.command()
def analyze(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run full priority analysis."""
    from northstar.pipeline import PipelineManager

    async def _analyze() -> None:
        pm = PipelineManager()
        result = await pm.analyze()
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print("[green]Analysis complete.[/green]")

    _run(_analyze())


@app.command()
def status(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show current Priority Debt Score and top priorities."""
    from northstar.pipeline import PipelineManager

    async def _status() -> None:
        pm = PipelineManager()
        result = await pm.get_status()
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(result.get("display", "No status available."))

    _run(_status())


@app.command()
def check(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Quick drift check on current session."""
    from northstar.pipeline import PipelineManager

    async def _check() -> None:
        pm = PipelineManager()
        result = await pm.quick_check()
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(result.get("display", "No active session."))

    _run(_check())


@app.command()
def rank(
    task: Optional[str] = typer.Option(None, "--task", "-t", help="Task description to add and rank"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Add and rank a new task."""
    from northstar.pipeline import PipelineManager

    async def _rank() -> None:
        pm = PipelineManager()
        result = await pm.add_and_rank_task(task_description=task)
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print("[green]Task ranked.[/green]")

    _run(_rank())


@app.command()
def tasks(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all tasks with leverage scores."""
    from northstar.pipeline import PipelineManager

    async def _tasks() -> None:
        pm = PipelineManager()
        result = await pm.get_tasks()
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(result.get("display", "No tasks found."))

    _run(_tasks())


@app.command()
def log(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries to show"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """View recent decision log."""
    from northstar.pipeline import PipelineManager

    async def _log() -> None:
        pm = PipelineManager()
        result = await pm.get_decisions(limit=limit)
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(result.get("display", "No decisions logged."))

    _run(_log())


@app.command()
def report(
    report_type: str = typer.Argument(..., help="Report type: session, weekly, or retro"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate a priority debt report."""
    from northstar.pipeline import PipelineManager

    valid_types = ("session", "weekly", "retro")
    if report_type not in valid_types:
        console.print(f"[red]Invalid report type. Choose from: {', '.join(valid_types)}[/red]")
        raise typer.Exit(code=1)

    async def _report() -> None:
        pm = PipelineManager()
        result = await pm.generate_report(report_type=report_type)
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(f"[green]Report saved to {result.get('path', '.northstar/reports/')}[/green]")

    _run(_report())


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key to get/set"),
    value: Optional[str] = typer.Option(None, "--set", help="Value to set"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """View or edit NorthStar configuration."""
    from northstar.pipeline import PipelineManager

    async def _config() -> None:
        pm = PipelineManager()
        if value is not None and key is not None:
            await pm.set_config(key, value)
            console.print(f"[green]Set {key} = {value}[/green]")
        else:
            result = await pm.get_config(key)
            if output_json:
                console.print_json(json.dumps(result))
            else:
                console.print(result.get("display", "No configuration."))

    _run(_config())


@app.command(name="export")
def export_data(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Export all NorthStar data as JSON."""
    from northstar.pipeline import PipelineManager

    async def _export() -> None:
        pm = PipelineManager()
        result = await pm.export_all(output_path=output)
        if output_json:
            console.print_json(json.dumps(result))
        else:
            console.print(f"[green]Data exported to {result.get('path', 'northstar_export.json')}[/green]")

    _run(_export())


@app.command()
def agent(
    mode: str = typer.Argument("analyze", help="Agent mode: analyze, check, drift, or chat"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message for chat mode"),
    model: Optional[str] = typer.Option(None, "--model", help="Override LLM model ID"),
    fallback: bool = typer.Option(False, "--fallback", help="Use offline fallback (no API key needed)"),
) -> None:
    """Run the agentic priority strategist (powered by Strands Agents)."""
    from northstar.agent import NorthStarAgent

    async def _agent() -> None:
        async with NorthStarAgent(model_id=model, fallback=fallback) as ns_agent:
            if mode == "analyze":
                result = await ns_agent.analyze()
            elif mode == "check":
                result = await ns_agent.quick_check()
            elif mode == "drift":
                result = await ns_agent.drift_check()
            elif mode == "chat":
                if not message:
                    console.print("[red]Chat mode requires --message / -m flag.[/red]")
                    raise typer.Exit(code=1)
                result = await ns_agent.chat(message)
            else:
                console.print(f"[red]Unknown mode '{mode}'. Use: analyze, check, drift, chat[/red]")
                raise typer.Exit(code=1)
            console.print(result)

    _run(_agent())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8765, "--port", "-p", help="Bind port"),
) -> None:
    """Launch the NorthStar web dashboard."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]Web dependencies not installed. Run: pip install northstar[web][/red]"
        )
        raise typer.Exit(code=1) from None

    from northstar.web.server import create_app

    app_instance = create_app()
    console.print(f"[green]NorthStar dashboard starting at http://{host}:{port}[/green]")
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


@app.command()
def reset(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Clear all NorthStar data for this project."""
    from northstar.pipeline import PipelineManager

    if not confirm:
        confirmed = typer.confirm("This will delete all NorthStar data. Continue?")
        if not confirmed:
            raise typer.Exit()

    async def _reset() -> None:
        pm = PipelineManager()
        await pm.reset()
        console.print("[green]NorthStar data has been reset.[/green]")

    _run(_reset())


if __name__ == "__main__":
    app()
