"""Tests for CLI commands."""

from typer.testing import CliRunner

from northstar.cli import app

runner = CliRunner()


class TestCLIHelp:
    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "NorthStar" in result.output
        assert "Priority Debt Engine" in result.output

    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_init_help(self) -> None:
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "--goals" in result.output
        assert "--no-interactive" in result.output

    def test_analyze_help(self) -> None:
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_status_help(self) -> None:
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_check_help(self) -> None:
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0

    def test_rank_help(self) -> None:
        result = runner.invoke(app, ["rank", "--help"])
        assert result.exit_code == 0
        assert "--task" in result.output

    def test_tasks_help(self) -> None:
        result = runner.invoke(app, ["tasks", "--help"])
        assert result.exit_code == 0

    def test_log_help(self) -> None:
        result = runner.invoke(app, ["log", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output

    def test_report_help(self) -> None:
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0

    def test_config_help(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_export_help(self) -> None:
        result = runner.invoke(app, ["export", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_reset_help(self) -> None:
        result = runner.invoke(app, ["reset", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.output

    def test_all_commands_present(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        commands = ["init", "analyze", "status", "check", "rank", "tasks", "log", "report", "config", "export", "reset", "agent", "serve"]
        for cmd in commands:
            assert cmd in result.output, f"Command '{cmd}' missing from help output"

    def test_serve_help(self) -> None:
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
