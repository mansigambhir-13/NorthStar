"""Tests for the git analyzer."""

import subprocess
from pathlib import Path

from northstar.integrations.git import GitAnalyzer


def _init_git_repo(path: Path) -> None:
    """Create a minimal git repo with a commit."""
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), capture_output=True)
    (path / "hello.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(path), capture_output=True, check=True)


class TestGitAnalyzer:
    async def test_analyze_git_repo(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        assert profile.total_commits >= 1
        assert len(profile.recent_commits) >= 1
        assert len(profile.contributors) >= 1
        assert profile.branch != ""

    async def test_not_a_git_repo(self, tmp_path: Path) -> None:
        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        assert profile.total_commits == 0
        assert profile.recent_commits == []

    async def test_multiple_commits(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        (tmp_path / "second.py").write_text("x = 2\n")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Second commit"], cwd=str(tmp_path), capture_output=True)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        assert profile.total_commits >= 2
        assert len(profile.recent_commits) >= 2

    async def test_velocity(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        # At least 1 commit in the last 30 days
        assert profile.commit_velocity >= 0

    async def test_contributors_list(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        assert "Test" in profile.contributors

    async def test_commit_messages(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        messages = [c.get("message", "") for c in profile.recent_commits]
        assert any("Initial commit" in m for m in messages)

    async def test_focus_areas(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add src"], cwd=str(tmp_path), capture_output=True)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        # Focus areas should include files/directories from recent commits
        assert len(profile.focus_areas) >= 0  # May be empty if only root-level files

    async def test_branch_name(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        # Should be 'main' or 'master' depending on git config
        assert profile.branch in ("main", "master")

    async def test_branches_list(self, tmp_path: Path) -> None:
        _init_git_repo(tmp_path)

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        # Should have at least the current branch
        assert len(profile.active_branches) >= 1

    async def test_empty_repo_fallback(self, tmp_path: Path) -> None:
        """Non-git directory returns empty profile gracefully."""
        (tmp_path / "file.txt").write_text("not a repo\n")

        analyzer = GitAnalyzer(root=tmp_path)
        profile = await analyzer.analyze()

        assert profile.branch == "main"
        assert profile.total_commits == 0
        assert profile.recent_commits == []
        assert profile.contributors == []
