"""NorthStar configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    model_config = ConfigDict(from_attributes=True)

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_tokens: int = 4096
    api_key_env: str = "ANTHROPIC_API_KEY"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


class DriftConfig(BaseModel):
    """Drift detection thresholds."""

    model_config = ConfigDict(from_attributes=True)

    high_ratio: float = 0.3
    high_minutes: int = 30
    medium_ratio: float = 0.6
    medium_minutes: int = 45
    low_ratio: float = 0.8
    low_minutes: int = 60
    snooze_minutes: int = 15


class ScanConfig(BaseModel):
    """Codebase scanning configuration."""

    model_config = ConfigDict(from_attributes=True)

    max_file_size_kb: int = 500
    max_files: int = 10000
    languages: list[str] = Field(default_factory=lambda: ["python", "javascript", "typescript", "go", "rust"])
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "dist",
            "build",
            ".northstar",
        ]
    )


class ScoringConfig(BaseModel):
    """Leverage scoring configuration."""

    model_config = ConfigDict(from_attributes=True)

    blocking_multiplier: float = 3.0
    deadline_48h_multiplier: float = 2.5
    deadline_1w_multiplier: float = 1.5
    no_deadline_multiplier: float = 1.0
    dependency_unlock_factor: float = 0.5
    min_effort: float = 0.5
    max_score: int = 10000


class ReportingConfig(BaseModel):
    """Reporting configuration."""

    model_config = ConfigDict(from_attributes=True)

    output_dir: str = ".northstar/reports"
    include_llm_insights: bool = True
    max_log_size_mb: int = 50
    archive_after_days: int = 90


class NorthStarConfig(BaseModel):
    """Root configuration for NorthStar."""

    model_config = ConfigDict(from_attributes=True)

    project_name: str = ""
    project_root: str = "."
    llm: LLMConfig = Field(default_factory=LLMConfig)
    drift: DriftConfig = Field(default_factory=DriftConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)

    @classmethod
    def load(cls, path: Path | str | None = None) -> NorthStarConfig:
        """Load configuration from YAML file, falling back to defaults."""
        if path is None:
            path = Path(".northstar/config.yaml")
        path = Path(path)
        if path.exists():
            with open(path) as f:
                data: dict[str, Any] = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

    def save(self, path: Path | str | None = None) -> None:
        """Save configuration to YAML file."""
        if path is None:
            path = Path(".northstar/config.yaml")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
