"""Tests for NorthStar configuration."""

from pathlib import Path

import yaml

from northstar.config import (
    DriftConfig,
    LLMConfig,
    NorthStarConfig,
    ScanConfig,
    ScoringConfig,
    ReportingConfig,
)


class TestDefaults:
    def test_default_config(self) -> None:
        cfg = NorthStarConfig()
        assert cfg.project_name == ""
        assert cfg.project_root == "."
        assert isinstance(cfg.llm, LLMConfig)
        assert isinstance(cfg.drift, DriftConfig)
        assert isinstance(cfg.scan, ScanConfig)
        assert isinstance(cfg.scoring, ScoringConfig)
        assert isinstance(cfg.reporting, ReportingConfig)

    def test_llm_defaults(self) -> None:
        llm = LLMConfig()
        assert llm.provider == "anthropic"
        assert llm.temperature == 0.0
        assert llm.cache_enabled is True

    def test_drift_defaults(self) -> None:
        drift = DriftConfig()
        assert drift.high_ratio == 0.3
        assert drift.high_minutes == 30
        assert drift.snooze_minutes == 15

    def test_scoring_defaults(self) -> None:
        scoring = ScoringConfig()
        assert scoring.blocking_multiplier == 3.0
        assert scoring.min_effort == 0.5
        assert scoring.max_score == 10000

    def test_scan_defaults(self) -> None:
        scan = ScanConfig()
        assert "python" in scan.languages
        assert "node_modules" in scan.ignore_patterns


class TestYAMLLoading:
    def test_load_from_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        config_data = {
            "project_name": "my-project",
            "llm": {"model": "claude-haiku-4-5-20251001", "temperature": 0.1},
        }
        config_path.write_text(yaml.dump(config_data))
        cfg = NorthStarConfig.load(config_path)
        assert cfg.project_name == "my-project"
        assert cfg.llm.model == "claude-haiku-4-5-20251001"
        assert cfg.llm.temperature == 0.1
        # Non-specified fields keep defaults
        assert cfg.drift.high_ratio == 0.3

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        cfg = NorthStarConfig.load(tmp_path / "nonexistent.yaml")
        assert cfg.project_name == ""
        assert cfg.llm.provider == "anthropic"

    def test_save_and_reload(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.yaml"
        cfg = NorthStarConfig(project_name="roundtrip-test")
        cfg.save(config_path)
        reloaded = NorthStarConfig.load(config_path)
        assert reloaded.project_name == "roundtrip-test"
        assert reloaded.llm.model == cfg.llm.model

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        config_path = tmp_path / "deep" / "nested" / "config.yaml"
        cfg = NorthStarConfig(project_name="nested")
        cfg.save(config_path)
        assert config_path.exists()

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")
        cfg = NorthStarConfig.load(config_path)
        assert cfg.project_name == ""
