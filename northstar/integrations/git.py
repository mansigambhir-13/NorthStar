"""Git repository analyzer — extracts commit history, branches, velocity, and focus areas."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from northstar.analysis.models import GitProfile

logger = logging.getLogger(__name__)


class GitAnalyzer:
    """Analyzes a Git repository to produce a GitProfile."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    async def analyze(self) -> GitProfile:
        """Analyze the git repository and return a GitProfile.

        Returns an empty GitProfile if the directory is not a git repo.
        """
        # Check if this is a git repository
        if not (self.root / ".git").exists():
            is_repo = await self._run("git", "rev-parse", "--is-inside-work-tree")
            if is_repo.strip() != "true":
                logger.info(f"{self.root} is not a git repository")
                return GitProfile()

        try:
            branch = await self._run("git", "rev-parse", "--abbrev-ref", "HEAD")
            recent_commits = await self._get_recent_commits()
            active_branches = await self._get_branches()
            velocity = await self._get_velocity()
            focus_areas = await self._get_focus_areas()
            contributors = await self._get_contributors()
            total_commits = await self._get_total_commits()

            return GitProfile(
                branch=branch.strip() or "main",
                total_commits=total_commits,
                recent_commits=recent_commits,
                active_branches=active_branches,
                commit_velocity=velocity,
                focus_areas=focus_areas,
                contributors=contributors,
            )

        except Exception as e:
            logger.warning(f"Git analysis failed: {e}; returning empty GitProfile")
            return GitProfile()

    async def _run(self, *cmd: str) -> str:
        """Run a git command and return its stdout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                err_msg = stderr.decode(errors="replace").strip()
                logger.debug(f"{' '.join(cmd)} failed: {err_msg}")
                return ""

            return stdout.decode("utf-8", errors="replace")

        except asyncio.TimeoutError:
            logger.warning(f"git command timed out: {' '.join(cmd)}")
            return ""
        except FileNotFoundError:
            logger.warning("git command not found")
            return ""
        except Exception as e:
            logger.debug(f"git command error: {e}")
            return ""

    async def _get_recent_commits(self) -> list[dict[str, str]]:
        """Get the last 50 commits as a list of dicts."""
        output = await self._run("git", "log", "--oneline", "-50")
        commits: list[dict[str, str]] = []
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append({"hash": parts[0], "message": parts[1]})
            elif parts:
                commits.append({"hash": parts[0], "message": ""})
        return commits

    async def _get_branches(self) -> list[str]:
        """Get all branch names (local and remote)."""
        output = await self._run("git", "branch", "-a")
        branches: list[str] = []
        for line in output.strip().splitlines():
            branch = line.strip().lstrip("* ").strip()
            # Skip HEAD references
            if "->" in branch:
                continue
            if branch:
                branches.append(branch)
        return branches

    async def _get_velocity(self) -> float:
        """Calculate commits per day over the last 30 days."""
        output = await self._run(
            "git", "log", "--format=%H", "--since=30 days ago"
        )
        lines = [line for line in output.strip().splitlines() if line.strip()]
        commit_count = len(lines)
        return round(commit_count / 30.0, 2)

    async def _get_focus_areas(self) -> list[str]:
        """Get the most frequently modified files/directories."""
        output = await self._run(
            "git", "log", "--format=", "--name-only", "-100"
        )
        # Count file occurrences by top-level directory
        file_counts: dict[str, int] = {}
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("/")
            area = parts[0] if len(parts) > 1 else line
            file_counts[area] = file_counts.get(area, 0) + 1

        # Sort by count descending, take top 10
        sorted_areas = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        return [area for area, _ in sorted_areas[:10]]

    async def _get_contributors(self) -> list[str]:
        """Get unique contributor names."""
        output = await self._run("git", "log", "--format=%aN")
        names: set[str] = set()
        for line in output.strip().splitlines():
            name = line.strip()
            if name:
                names.add(name)
        return sorted(names)

    async def _get_total_commits(self) -> int:
        """Get total number of commits."""
        output = await self._run("git", "rev-list", "--count", "HEAD")
        try:
            return int(output.strip())
        except (ValueError, TypeError):
            return 0
