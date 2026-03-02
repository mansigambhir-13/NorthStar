"""Tests for the codebase scanner."""

from pathlib import Path

from northstar.config import ScanConfig
from northstar.ingestion.codebase_scanner import CodebaseScanner


class TestCodebaseScanner:
    async def test_scan_python_project(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def main():\n    print('hello')\n\ndef helper():\n    pass\n")
        (src / "utils.py").write_text("# TODO: Refactor this\ndef compute():\n    return 42\n")
        (tmp_path / "README.md").write_text("# Project\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert profile.total_files >= 2
        assert profile.total_loc > 0
        assert profile.primary_language == "python"
        assert "python" in profile.languages

    async def test_todo_extraction(self, tmp_path: Path) -> None:
        (tmp_path / "code.py").write_text(
            "# TODO: Fix this bug\ndef broken():\n    # FIXME: Memory leak\n    pass\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert len(profile.todos) >= 1
        texts = [t.get("text", "") for t in profile.todos]
        assert any("Fix this bug" in t for t in texts)

    async def test_todo_has_file_and_line(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n# TODO: Add logging\ny = 2\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert len(profile.todos) == 1
        todo = profile.todos[0]
        assert todo["file"] == "app.py"
        assert todo["line"] == 2
        assert todo["type"] == "TODO"
        assert "Add logging" in todo["text"]

    async def test_language_detection(self, tmp_path: Path) -> None:
        (tmp_path / "app.js").write_text("function main() { console.log('hi'); }\n")
        (tmp_path / "server.py").write_text("from flask import Flask\napp = Flask(__name__)\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert "python" in profile.languages
        assert "javascript" in profile.languages

    async def test_typescript_detection(self, tmp_path: Path) -> None:
        (tmp_path / "index.ts").write_text("const x: number = 1;\n")
        (tmp_path / "comp.tsx").write_text("function App() { return null; }\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert "typescript" in profile.languages

    async def test_respects_ignore_patterns(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text("x = 1\n")
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "dep.js").write_text("module.exports = {}\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        scanned_paths = [m.path for m in profile.modules]
        assert not any("node_modules" in p for p in scanned_paths)

    async def test_respects_gitignore(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("x = 1\n")
        (tmp_path / "secret.py").write_text("password = 'hunter2'\n")
        (tmp_path / ".gitignore").write_text("secret.py\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        scanned_files = set(profile.file_hashes.keys())
        assert "app.py" in scanned_files
        assert "secret.py" not in scanned_files

    async def test_empty_directory(self, tmp_path: Path) -> None:
        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert profile.total_files == 0
        assert profile.total_loc == 0

    async def test_file_hashes(self, tmp_path: Path) -> None:
        (tmp_path / "test.py").write_text("x = 1\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert len(profile.file_hashes) >= 1
        for _path, hash_val in profile.file_hashes.items():
            assert len(hash_val) == 32  # MD5 hex digest

    async def test_loc_skips_blanks_and_comments(self, tmp_path: Path) -> None:
        (tmp_path / "code.py").write_text(
            "# A comment\n"
            "\n"
            "x = 1\n"
            "\n"
            "# Another comment\n"
            "y = 2\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        # Only 'x = 1' and 'y = 2' count as LOC
        assert profile.languages["python"] == 2

    async def test_framework_detection(self, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text(
            "from flask import Flask\napp = Flask(__name__)\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert "flask" in profile.frameworks

    async def test_framework_detection_react(self, tmp_path: Path) -> None:
        (tmp_path / "app.jsx").write_text(
            "import React from 'react';\n"
            "function App() { return <div/>; }\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert "react" in profile.frameworks

    async def test_dependency_extraction_requirements(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("x = 1\n")
        (tmp_path / "requirements.txt").write_text(
            "flask>=2.0\nrequests\n# comment\npydantic>=2.0\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        all_deps: set[str] = set()
        for module in profile.modules:
            all_deps.update(module.dependencies)

        assert "flask" in all_deps
        assert "requests" in all_deps
        assert "pydantic" in all_deps

    async def test_dependency_extraction_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "index.js").write_text("const x = 1;\n")
        (tmp_path / "package.json").write_text(
            '{"name": "test", "dependencies": {"express": "^4.0"}, '
            '"devDependencies": {"jest": "^29.0"}}'
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        all_deps: set[str] = set()
        for module in profile.modules:
            all_deps.update(module.dependencies)

        assert "express" in all_deps
        assert "jest" in all_deps

    async def test_js_todo_extraction(self, tmp_path: Path) -> None:
        (tmp_path / "app.js").write_text(
            "// TODO: implement auth\n"
            "function login() {}\n"
            "// FIXME: security issue\n"
        )

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert len(profile.todos) == 2
        types = {t["type"] for t in profile.todos}
        assert "TODO" in types
        assert "FIXME" in types

    async def test_max_file_size(self, tmp_path: Path) -> None:
        config = ScanConfig(max_file_size_kb=1)
        (tmp_path / "small.py").write_text("x = 1\n")
        (tmp_path / "big.py").write_text("x = 1\n" * 500)

        scanner = CodebaseScanner(config, tmp_path)
        profile = await scanner.scan()

        assert "small.py" in profile.file_hashes
        assert "big.py" not in profile.file_hashes

    async def test_module_aggregation(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def foo():\n    pass\n")
        (src / "b.py").write_text("def bar():\n    pass\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        src_modules = [m for m in profile.modules if m.path == "src"]
        assert len(src_modules) == 1
        assert src_modules[0].num_files == 2

    async def test_scan_root_path_set(self, tmp_path: Path) -> None:
        (tmp_path / "x.py").write_text("a = 1\n")

        config = ScanConfig()
        scanner = CodebaseScanner(config=config, root=tmp_path)
        profile = await scanner.scan()

        assert str(tmp_path.resolve()) in profile.root_path
