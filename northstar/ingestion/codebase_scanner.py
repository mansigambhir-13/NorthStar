"""Codebase scanner — walks directories, detects languages, counts LOC, extracts metadata."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from northstar.analysis.models import CodebaseProfile, ModuleInfo
from northstar.config import ScanConfig
from northstar.exceptions import ScanError

logger = logging.getLogger(__name__)

# ── Language detection by extension ───────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
}

# ── Framework detection patterns ──────────────────────────────────────

FRAMEWORK_PATTERNS: dict[str, list[str]] = {
    "flask": ["flask", "Flask"],
    "django": ["django", "Django"],
    "fastapi": ["fastapi", "FastAPI"],
    "express": ["express", "require('express')", 'require("express")'],
    "react": ["react", "React", "from 'react'", 'from "react"'],
    "nextjs": ["next", "next/"],
    "vue": ["vue", "Vue"],
    "angular": ["@angular"],
    "gin": ["github.com/gin-gonic/gin"],
    "actix": ["actix_web", "actix-web"],
    "spring": ["org.springframework"],
    "rails": ["rails", "Rails"],
    "pytest": ["pytest", "import pytest"],
}

# ── Dependency file names ─────────────────────────────────────────────

DEPENDENCY_FILES = [
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
]

# ── Comment patterns for LOC counting ─────────────────────────────────

SINGLE_LINE_COMMENT: dict[str, str] = {
    "python": "#",
    "javascript": "//",
    "typescript": "//",
    "go": "//",
    "rust": "//",
    "java": "//",
    "ruby": "#",
}

# ── Regex patterns for function/class extraction ──────────────────────

FUNCTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"),
    "javascript": re.compile(r"(?:function|class)\s+(\w+)"),
    "typescript": re.compile(r"(?:function|class)\s+(\w+)"),
}

CLASS_PATTERNS: dict[str, re.Pattern[str]] = {
    "python": re.compile(r"^\s*class\s+(\w+)"),
    "javascript": re.compile(r"class\s+(\w+)"),
    "typescript": re.compile(r"class\s+(\w+)"),
}

TODO_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)[:\s]+(.+)", re.IGNORECASE)
TODO_PATTERN_SLASH = re.compile(r"//\s*(TODO|FIXME|HACK|XXX)[:\s]+(.+)", re.IGNORECASE)


class CodebaseScanner:
    """Scans a project directory to produce a CodebaseProfile."""

    def __init__(self, config: ScanConfig, root: Path) -> None:
        self.config = config
        self.root = Path(root).resolve()
        self._gitignore_spec: Any | None = None

    async def scan(self) -> CodebaseProfile:
        """Main entry point — scans the codebase and returns a CodebaseProfile."""
        try:
            self._load_gitignore()
            files = self._collect_files()

            languages: dict[str, int] = {}
            todos: list[dict[str, Any]] = []
            file_hashes: dict[str, str] = {}
            modules: dict[str, ModuleInfo] = {}
            all_frameworks: set[str] = set()
            all_functions: dict[str, list[str]] = {}  # file -> functions
            total_loc = 0
            total_files = 0

            for filepath in files:
                if total_files >= self.config.max_files:
                    break

                rel = filepath.relative_to(self.root)
                ext = filepath.suffix.lower()
                lang = EXTENSION_MAP.get(ext, "")
                if not lang:
                    continue

                # Check file size
                try:
                    size_kb = filepath.stat().st_size / 1024
                except OSError:
                    continue
                if size_kb > self.config.max_file_size_kb:
                    continue

                total_files += 1

                # Read and hash
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue

                file_hash = hashlib.md5(content.encode()).hexdigest()
                file_hashes[str(rel)] = file_hash

                # Count LOC
                loc = self._count_loc(content, lang)
                total_loc += loc
                languages[lang] = languages.get(lang, 0) + loc

                # Extract TODOs
                file_todos = self._extract_todos(content, str(rel))
                todos.extend(file_todos)

                # Extract functions/classes
                funcs = self._extract_functions(content, lang)
                if funcs:
                    all_functions[str(rel)] = funcs

                # Detect frameworks
                frameworks = self._detect_frameworks(content)
                all_frameworks.update(frameworks)

                # Module aggregation (by top-level directory)
                module_key = str(rel.parts[0]) if len(rel.parts) > 1 else "."
                if module_key not in modules:
                    modules[module_key] = ModuleInfo(
                        path=module_key,
                        language=lang,
                        loc=0,
                        num_files=0,
                        complexity_score=0.0,
                        frameworks=[],
                        dependencies=[],
                    )
                mod = modules[module_key]
                mod.loc += loc
                mod.num_files += 1

            # Compute complexity for each module
            for module_key, mod in modules.items():
                func_count = sum(
                    len(fns)
                    for fpath, fns in all_functions.items()
                    if fpath.startswith(module_key + "/") or module_key == "."
                )
                if mod.num_files > 0:
                    mod.complexity_score = round(func_count / mod.num_files, 2)

            # Detect primary language
            primary_language = "unknown"
            if languages:
                primary_language = max(languages, key=lambda k: languages[k])

            # Extract dependencies
            deps = self._extract_dependencies()
            for module_key, mod in modules.items():
                mod.dependencies = deps
                mod.frameworks = list(all_frameworks)

            return CodebaseProfile(
                root_path=str(self.root),
                primary_language=primary_language,
                total_files=total_files,
                total_loc=total_loc,
                modules=list(modules.values()),
                languages=languages,
                frameworks=sorted(all_frameworks),
                todos=todos,
                file_hashes=file_hashes,
            )

        except Exception as e:
            if isinstance(e, ScanError):
                raise
            raise ScanError(f"Codebase scan failed: {e}") from e

    def _load_gitignore(self) -> None:
        """Load .gitignore patterns using pathspec."""
        try:
            import pathspec

            gitignore_path = self.root / ".gitignore"
            patterns = list(self.config.ignore_patterns)  # Start with config ignores
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding="utf-8", errors="replace")
                patterns.extend(content.splitlines())
            self._gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except ImportError:
            logger.warning("pathspec not installed; falling back to config ignore_patterns only")
            self._gitignore_spec = None

    def _is_ignored(self, rel_path: str) -> bool:
        """Check whether a relative path should be ignored."""
        if self._gitignore_spec is not None:
            return self._gitignore_spec.match_file(rel_path)
        # Fallback: check against config ignore_patterns
        for pattern in self.config.ignore_patterns:
            if pattern in rel_path:
                return True
        return False

    def _collect_files(self) -> list[Path]:
        """Walk directory tree, respecting ignore patterns."""
        files: list[Path] = []
        for filepath in self.root.rglob("*"):
            if not filepath.is_file():
                continue
            try:
                rel = str(filepath.relative_to(self.root))
            except ValueError:
                continue
            if self._is_ignored(rel):
                continue
            files.append(filepath)
        return sorted(files)

    def _count_loc(self, content: str, lang: str) -> int:
        """Count lines of code, skipping blank lines and single-line comments."""
        comment_prefix = SINGLE_LINE_COMMENT.get(lang, "")
        loc = 0
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if comment_prefix and stripped.startswith(comment_prefix):
                continue
            loc += 1
        return loc

    def _extract_todos(self, content: str, filepath: str) -> list[dict[str, Any]]:
        """Extract TODO/FIXME comments with file path and line number."""
        todos: list[dict[str, Any]] = []
        for i, line in enumerate(content.splitlines(), start=1):
            match = TODO_PATTERN.search(line) or TODO_PATTERN_SLASH.search(line)
            if match:
                todos.append(
                    {
                        "type": match.group(1).upper(),
                        "text": match.group(2).strip(),
                        "file": filepath,
                        "line": i,
                    }
                )
        return todos

    def _extract_functions(self, content: str, lang: str) -> list[str]:
        """Extract function and class names from source code.

        Uses tree-sitter AST parsing if available, falling back to regex.
        """
        names: list[str] = []

        # Try tree-sitter first
        try:
            names = self._extract_with_tree_sitter(content, lang)
            if names:
                return names
        except ImportError:
            pass

        # Regex fallback
        func_pat = FUNCTION_PATTERNS.get(lang)
        class_pat = CLASS_PATTERNS.get(lang)

        if func_pat:
            for match in func_pat.finditer(content):
                names.append(match.group(1))
        if class_pat:
            for match in class_pat.finditer(content):
                name = match.group(1)
                if name not in names:
                    names.append(name)

        return names

    def _extract_with_tree_sitter(self, content: str, lang: str) -> list[str]:
        """Extract symbols using tree-sitter AST (raises ImportError if unavailable)."""
        import tree_sitter  # noqa: F401

        names: list[str] = []
        if lang == "python":
            import tree_sitter_python as tspython

            parser = tree_sitter.Parser(tree_sitter.Language(tspython.language()))
            tree = parser.parse(content.encode())
            self._walk_ts_tree(tree.root_node, names, {"function_definition", "class_definition"})
        elif lang in ("javascript", "typescript"):
            import tree_sitter_javascript as tsjs

            parser = tree_sitter.Parser(tree_sitter.Language(tsjs.language()))
            tree = parser.parse(content.encode())
            self._walk_ts_tree(
                tree.root_node,
                names,
                {"function_declaration", "class_declaration", "method_definition"},
            )
        return names

    def _walk_ts_tree(self, node: Any, names: list[str], target_types: set[str]) -> None:
        """Recursively walk tree-sitter AST and collect names."""
        if node.type in target_types:
            for child in node.children:
                if child.type in ("identifier", "property_identifier"):
                    names.append(child.text.decode())
                    break
        for child in node.children:
            self._walk_ts_tree(child, names, target_types)

    def _detect_frameworks(self, content: str) -> set[str]:
        """Check content for known framework imports/references."""
        detected: set[str] = set()
        for framework, patterns in FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if pattern in content:
                    detected.add(framework)
                    break
        return detected

    def _extract_dependencies(self) -> list[str]:
        """Extract dependency names from common dependency files."""
        deps: list[str] = []

        # pyproject.toml
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8", errors="replace")
                # Simple regex extraction for dependencies
                in_deps = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("dependencies") and "=" in stripped:
                        in_deps = True
                        continue
                    if in_deps:
                        if stripped.startswith("]"):
                            in_deps = False
                            continue
                        # Extract package name from "package>=1.0"
                        match = re.match(r'"([a-zA-Z0-9_-]+)', stripped)
                        if match:
                            deps.append(match.group(1))
            except OSError:
                pass

        # requirements.txt
        reqs = self.root / "requirements.txt"
        if reqs.exists():
            try:
                for line in reqs.read_text(encoding="utf-8", errors="replace").splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                        name = re.split(r"[>=<!\[\]]", stripped)[0].strip()
                        if name and name not in deps:
                            deps.append(name)
            except OSError:
                pass

        # package.json
        pkg_json = self.root / "package.json"
        if pkg_json.exists():
            try:
                import json

                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="replace"))
                for section in ("dependencies", "devDependencies"):
                    if section in data and isinstance(data[section], dict):
                        for name in data[section]:
                            if name not in deps:
                                deps.append(name)
            except (OSError, ValueError):
                pass

        # go.mod
        gomod = self.root / "go.mod"
        if gomod.exists():
            try:
                in_require = False
                for line in gomod.read_text(encoding="utf-8", errors="replace").splitlines():
                    stripped = line.strip()
                    if stripped.startswith("require"):
                        in_require = True
                        continue
                    if in_require:
                        if stripped == ")":
                            in_require = False
                            continue
                        parts = stripped.split()
                        if parts:
                            deps.append(parts[0])
            except OSError:
                pass

        # Cargo.toml
        cargo = self.root / "Cargo.toml"
        if cargo.exists():
            try:
                in_deps_section = False
                for line in cargo.read_text(encoding="utf-8", errors="replace").splitlines():
                    stripped = line.strip()
                    if stripped in ("[dependencies]", "[dev-dependencies]"):
                        in_deps_section = True
                        continue
                    if stripped.startswith("[") and in_deps_section:
                        in_deps_section = False
                        continue
                    if in_deps_section and "=" in stripped:
                        name = stripped.split("=")[0].strip()
                        if name and name not in deps:
                            deps.append(name)
            except OSError:
                pass

        return deps
