"""Tests for the document reader."""

from pathlib import Path

from northstar.ingestion.doc_reader import DocReader
from northstar.integrations.llm import NullLLMClient


class TestDocReader:
    async def test_reads_readme(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# My App\nA web application for managing tasks.\n")
        llm = NullLLMClient(default_json={
            "project_type": "web_app",
            "project_stage": "mvp",
            "target_users": ["developers"],
            "key_features": ["task management"],
            "tech_stack": ["python"],
            "priorities_mentioned": [],
            "raw_summary": "A task management app.",
        })
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        assert insights.project_type == "web_app"
        assert insights.project_stage == "mvp"
        assert "developers" in insights.target_users
        assert len(llm.calls) == 1

    async def test_no_docs_returns_empty(self, tmp_path: Path) -> None:
        llm = NullLLMClient()
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        assert insights.project_type == ""
        assert len(llm.calls) == 0

    async def test_reads_docs_directory(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "guide.md").write_text("# Guide\nHow to use this app.\n")
        llm = NullLLMClient(default_json={
            "project_type": "library",
            "raw_summary": "A library with docs.",
        })
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        assert insights.project_type == "library"

    async def test_reads_changelog(self, tmp_path: Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text("# v1.0\n- Initial release\n")
        llm = NullLLMClient(default_json={
            "project_type": "api_service",
            "raw_summary": "Service with changelog.",
        })
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        assert insights.project_type == "api_service"
        assert len(llm.calls) == 1

    async def test_llm_error_returns_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test\n")

        class FailingLLM:
            async def query(self, *args, **kwargs):
                raise Exception("API error")

        reader = DocReader(llm_client=FailingLLM(), root=tmp_path)
        insights = await reader.read()

        assert insights.raw_summary != ""

    async def test_multiple_doc_files(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Project\nDescription.\n")
        (tmp_path / "CONTRIBUTING.md").write_text("# Contributing\nFork and PR.\n")
        llm = NullLLMClient(default_json={
            "project_type": "open_source",
            "raw_summary": "Multi-doc project.",
        })
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        # Should make exactly one LLM call with concatenated content
        assert len(llm.calls) == 1
        prompt_text = llm.calls[0]["prompt"]
        assert "README.md" in prompt_text
        assert "CONTRIBUTING.md" in prompt_text

    async def test_parse_json_flag_sent(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test\n")
        llm = NullLLMClient(default_json={"project_type": "test"})
        reader = DocReader(llm_client=llm, root=tmp_path)
        await reader.read()

        assert len(llm.calls) == 1
        assert llm.calls[0]["parse_json"] is True

    async def test_missing_fields_handled_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# Test\n")
        # Return partial JSON missing most fields
        llm = NullLLMClient(default_json={"project_type": "cli_tool"})
        reader = DocReader(llm_client=llm, root=tmp_path)
        insights = await reader.read()

        assert insights.project_type == "cli_tool"
        assert insights.target_users == []
        assert insights.key_features == []
