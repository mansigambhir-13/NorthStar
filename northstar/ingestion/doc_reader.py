"""Document reader — extracts insights from project documentation using LLM."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from northstar.analysis.models import DocumentInsights

logger = logging.getLogger(__name__)

# Files to scan for documentation
DOC_FILES = [
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    "CHANGELOG.md",
    "CHANGELOG.rst",
    "CHANGELOG.txt",
    "CHANGELOG",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
]

DOC_DIRS = ["docs", "doc", "documentation"]

MAX_DOC_CHARS = 30000  # Limit total doc content sent to LLM


class DocReader:
    """Reads project documentation and uses an LLM to extract structured insights."""

    def __init__(self, llm_client: Any, root: Path) -> None:
        self.llm = llm_client
        self.root = Path(root).resolve()

    async def read(self) -> DocumentInsights:
        """Read project docs and return structured DocumentInsights."""
        content = self._collect_docs()

        if not content.strip():
            logger.info("No documentation files found; returning empty DocumentInsights")
            return DocumentInsights()

        # Truncate if too large
        if len(content) > MAX_DOC_CHARS:
            content = content[:MAX_DOC_CHARS] + "\n\n... [truncated]"

        prompt = self._build_prompt(content)

        try:
            result = await self.llm.query(
                prompt=prompt,
                system=(
                    "You are a project analyst. Extract structured insights from "
                    "project documentation. Respond ONLY with valid JSON."
                ),
                parse_json=True,
            )

            return self._parse_result(result)

        except Exception as e:
            logger.warning(f"LLM doc analysis failed: {e}; returning partial insights")
            return DocumentInsights(raw_summary=content[:500])

    def _collect_docs(self) -> str:
        """Gather content from documentation files."""
        sections: list[str] = []

        # Check top-level doc files
        for filename in DOC_FILES:
            filepath = self.root / filename
            if filepath.is_file():
                try:
                    text = filepath.read_text(encoding="utf-8", errors="replace")
                    sections.append(f"--- {filename} ---\n{text}")
                except OSError:
                    continue

        # Check docs/ directories
        for dirname in DOC_DIRS:
            doc_dir = self.root / dirname
            if doc_dir.is_dir():
                for filepath in sorted(doc_dir.rglob("*")):
                    if filepath.is_file() and filepath.suffix in (".md", ".rst", ".txt", ""):
                        try:
                            text = filepath.read_text(encoding="utf-8", errors="replace")
                            rel = filepath.relative_to(self.root)
                            sections.append(f"--- {rel} ---\n{text}")
                        except (OSError, ValueError):
                            continue

        return "\n\n".join(sections)

    def _build_prompt(self, content: str) -> str:
        """Build the LLM prompt for extracting insights."""
        return (
            "Analyze the following project documentation and extract structured insights.\n\n"
            "Return a JSON object with these fields:\n"
            "- project_type: string (e.g., 'web_app', 'cli_tool', 'library', 'api_service')\n"
            "- project_stage: string (e.g., 'idea', 'mvp', 'beta', 'production')\n"
            "- target_users: list of strings\n"
            "- key_features: list of strings\n"
            "- tech_stack: list of strings\n"
            "- priorities_mentioned: list of strings\n"
            "- raw_summary: string (1-2 sentence summary)\n\n"
            f"Documentation:\n\n{content}"
        )

    def _parse_result(self, result: Any) -> DocumentInsights:
        """Parse LLM result into DocumentInsights, handling missing fields gracefully."""
        if isinstance(result, dict):
            return DocumentInsights(
                project_type=result.get("project_type", ""),
                project_stage=result.get("project_stage", ""),
                target_users=result.get("target_users", []),
                key_features=result.get("key_features", []),
                tech_stack=result.get("tech_stack", []),
                priorities_mentioned=result.get("priorities_mentioned", []),
                raw_summary=result.get("raw_summary", ""),
            )
        # If result is not a dict, return empty insights
        logger.warning(f"Unexpected LLM result type: {type(result)}")
        return DocumentInsights()
