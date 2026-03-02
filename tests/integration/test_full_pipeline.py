"""End-to-end integration test for the full pipeline."""

import subprocess
from pathlib import Path

import yaml

from northstar.config import NorthStarConfig
from northstar.integrations.llm import NullLLMClient
from northstar.pipeline import PipelineManager


class TestFullPipeline:
    async def test_init_analyze_check(self, tmp_path: Path) -> None:
        """End-to-end: create temp project, init, analyze, check."""
        # Setup project
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("# TODO: Implement main\ndef main():\n    pass\n")
        (src / "auth.py").write_text("def login():\n    pass\n\ndef signup():\n    pass\n")
        (tmp_path / "README.md").write_text("# E-commerce MVP\nAn online store.\n")

        goals_file = tmp_path / "goals.yaml"
        goals_file.write_text(yaml.dump({
            "goals": [
                {"id": "g1", "title": "Launch MVP", "priority": 1, "description": "Ship to first users"},
                {"id": "g2", "title": "Payment integration", "priority": 2},
            ]
        }))

        # Init
        pm = PipelineManager(project_root=tmp_path)
        result = await pm.initialize(goals_path=goals_file, interactive=False)

        assert result["status"] == "initialized"
        assert result["goals"] == 2
        assert (tmp_path / ".northstar").exists()
        assert (tmp_path / ".northstar" / "context.json").exists()

        # Analyze
        pm2 = PipelineManager(project_root=tmp_path)
        result = await pm2.analyze()

        assert "pds" in result
        assert "top_tasks" in result

        # Check
        pm3 = PipelineManager(project_root=tmp_path)
        result = await pm3.quick_check()

        assert "pds" in result
        assert "severity" in result

    async def test_export(self, tmp_path: Path) -> None:
        """Test data export."""
        (tmp_path / "hello.py").write_text("x = 1\n")

        pm = PipelineManager(project_root=tmp_path)
        await pm.initialize(interactive=False)

        pm2 = PipelineManager(project_root=tmp_path)
        result = await pm2.export_all()

        assert "path" in result
        assert Path(result["path"]).exists()

    async def test_reset(self, tmp_path: Path) -> None:
        """Test reset clears data."""
        (tmp_path / "hello.py").write_text("x = 1\n")

        pm = PipelineManager(project_root=tmp_path)
        await pm.initialize(interactive=False)

        pm2 = PipelineManager(project_root=tmp_path)
        await pm2.reset()

        pm3 = PipelineManager(project_root=tmp_path)
        result = await pm3.get_status()
        # After reset, should indicate not initialized or empty
        assert "display" in result
