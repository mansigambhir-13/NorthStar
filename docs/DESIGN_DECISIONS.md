# Key Design Decisions

This document records the significant architectural and technical decisions made in NorthStar, along with the rationale for each.

---

## 1. Flat Layout (No src/ Directory)

**Decision:** Place the `northstar/` package directly in the project root rather than inside a `src/` directory.

**Rationale:** NorthStar is a single-package project. The `src/` layout exists to prevent accidental imports of the development version in multi-package monorepos. For a single CLI tool, it adds a layer of indirection with no benefit. Flat layout means `import northstar` works from the project root during development, reducing friction.

**Trade-offs:**
- Simpler for contributors to navigate
- `pip install -e .` works without `src/` configuration
- Would need restructuring if NorthStar became a monorepo (unlikely)

---

## 2. Typer Over Click

**Decision:** Use Typer as the CLI framework instead of Click directly.

**Rationale:** Typer is built on Click but provides type-safe argument parsing through Python type hints. This eliminates the boilerplate of `@click.option()` decorators and keeps the CLI definition close to the function signature. Since NorthStar already uses type hints throughout, Typer is a natural fit.

**Trade-offs:**
- Less boilerplate than Click (type hints serve as both documentation and validation)
- Automatic `--help` generation from docstrings
- Slightly less flexible for complex Click customizations (rarely needed)
- Adds a dependency, but Typer is lightweight and stable

---

## 3. Pydantic v2

**Decision:** Use Pydantic v2 for all data models with `ConfigDict(from_attributes=True)`.

**Rationale:** Pydantic v2 is significantly faster than v1 (Rust-based core), provides native JSON serialization, and supports `from_attributes=True` for constructing models from ORM objects or database rows. This is essential for the State Manager, which converts between SQLite rows and Pydantic models.

**Trade-offs:**
- Fast validation (important for large task lists)
- Built-in JSON serialization (no custom encoders needed)
- `from_attributes=True` enables clean SQLite row to model conversion
- v2 has some breaking changes from v1, but NorthStar has no v1 legacy

---

## 4. aiosqlite with WAL Mode

**Decision:** Use aiosqlite for async SQLite access with Write-Ahead Logging (WAL) mode enabled.

**Rationale:** NorthStar's async architecture requires non-blocking database access. aiosqlite wraps sqlite3 in a thread executor, providing an async interface. WAL mode enables concurrent readers during writes, which matters when the drift monitor reads state while the analysis engine writes new scores.

**Trade-offs:**
- Non-blocking I/O aligns with async architecture
- Concurrent reads during writes (WAL mode)
- Single-file database (no server to manage, easy to backup)
- SQLite is not suitable for multi-process writes (acceptable for a CLI tool)
- WAL mode creates `-wal` and `-shm` files alongside the database

---

## 5. NullLLMClient Pattern

**Decision:** Implement a `NullLLMClient` that provides deterministic, rule-based responses as a drop-in replacement for the real LLM client.

**Rationale:** The NullLLMClient pattern serves three purposes:

1. **Testing:** Unit tests run without API keys, without network access, and without cost. Every test in CI uses NullLLMClient.
2. **Offline operation:** FDEs in air-gapped client environments can use NorthStar with rule-based scoring instead of LLM-enhanced scoring.
3. **Development:** Contributors can work on NorthStar without configuring API keys.

**Trade-offs:**
- Zero API cost in testing and development
- Deterministic outputs enable snapshot testing
- Offline operation for sensitive environments
- Rule-based scoring is less nuanced than LLM scoring (acceptable trade-off)

---

## 6. tree-sitter with Regex Fallback

**Decision:** Use tree-sitter for AST parsing of source code, with a regex-based fallback for languages where tree-sitter grammars are unavailable or parsing fails.

**Rationale:** The Ingestion Engine needs to understand codebase structure (functions, classes, modules) to build context for priority analysis. tree-sitter provides accurate, fast AST parsing for most mainstream languages. However, rather than failing on unsupported languages, a regex fallback extracts a best-effort structural summary.

**Trade-offs:**
- Accurate parsing for supported languages (Python, JavaScript, TypeScript, Go, Rust, etc.)
- Graceful degradation instead of hard failure
- Regex fallback is imprecise but sufficient for structural overview
- tree-sitter grammars add to package size (mitigated by lazy loading)

---

## 7. asyncio.run() at CLI Boundary

**Decision:** Use `asyncio.run()` in each Typer command handler to bridge from synchronous CLI to async internals.

**Rationale:** Typer (and Click) command handlers are synchronous functions. NorthStar's internals are fully async. The standard pattern is to call `asyncio.run(async_handler())` at the CLI boundary. This creates a fresh event loop for each command invocation, avoiding nested event loop issues.

**Trade-offs:**
- Standard, well-understood pattern
- Each CLI command gets a clean event loop
- No risk of nested event loops (unlike `loop.run_until_complete()` hacks)
- Slight overhead of event loop creation per command (negligible for CLI)

---

## 8. Normalized Leverage Scores (0-10000)

**Decision:** All leverage scores use an integer scale from 0 to 10000.

**Rationale:** A normalized scale provides several benefits:

- **Intuitive:** 8500 is obviously "high leverage" without needing to know the formula details.
- **Comparable:** Scores from different projects or time periods can be compared directly.
- **Display-friendly:** Integers avoid floating-point display issues (e.g., 0.8499999999).
- **Granular enough:** 10,000 levels of granularity is sufficient for distinguishing task priorities while remaining human-readable.

**Trade-offs:**
- Requires normalization step after raw score calculation
- Integer division may lose some precision (acceptable)
- 0-100 was considered but did not provide enough granularity for large task lists

---

## 9. Dual Persistence (SQLite + JSON)

**Decision:** Use both SQLite and JSON files for persistence, managed through a unified State Manager.

**Rationale:** Different data types have different storage needs:

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Tasks, scores, sessions | SQLite | Needs querying, sorting, aggregation |
| Goals, configuration | JSON | Human-readable, git-friendly, hand-editable |
| Analysis snapshots | JSON | Inspectable, diffable between runs |
| Decision log | SQLite | Time-series queries, fast inserts |

**Trade-offs:**
- Best tool for each data type
- JSON files are inspectable with any text editor
- SQLite handles structured queries efficiently
- Two persistence mechanisms to maintain (mitigated by State Manager abstraction)
- All access goes through State Manager — engines never touch storage directly

---

## 10. Hash-Based LLM Caching

**Decision:** Cache LLM responses by computing a hash of the input prompt and storing the response. Identical prompts return cached responses without an API call.

**Rationale:** LLM calls are the most expensive operation in NorthStar (in terms of both cost and latency). Many analyses produce identical prompts — re-analyzing the same codebase with the same goals should not cost another API call.

The cache key is a SHA-256 hash of the full prompt text. Cache entries include a TTL (configurable, default 24 hours) after which they are considered stale.

**Trade-offs:**
- Dramatically reduces API costs for repeated analyses
- Faster response times for cached queries
- Deterministic results for identical inputs (good for testing)
- Cache can become stale if codebase changes but prompt text does not (mitigated by TTL)
- Cache invalidation on goal changes (hash includes goal context)
