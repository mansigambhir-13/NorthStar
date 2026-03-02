#!/usr/bin/env python3
"""NorthStar Benchmark Runner and Demo.

Entry point for running the full benchmark suite or individual demo cases.

Usage:
    python -m benchmarks.run_demos --benchmark     # Run all 5 cases, print scorecard
    python -m benchmarks.run_demos --demo           # Run all demos with rich output
    python -m benchmarks.run_demos --case 1         # Run a specific demo case (1-5)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any

from northstar.analysis.leverage_ranker import LeverageRanker
from northstar.analysis.models import (
    Goal,
    GoalSet,
    PriorityStack,
    Task,
    UrgencyLevel,
)
from northstar.analysis.priority_debt import PriorityDebtCalculator
from northstar.config import ScoringConfig

from benchmarks.baselines.human_expert import EXPERT_PDS, EXPERT_RANKINGS
from benchmarks.baselines.vanilla_cursor import VANILLA_PDS, VANILLA_RANKINGS
from benchmarks.scoring.calculator import BenchmarkCalculator
from benchmarks.scoring.dimensions import kendalls_tau
from benchmarks.test_cases import ALL_CASES


# ── Helpers ───────────────────────────────────────────────────────────────

URGENCY_MAP: dict[str, UrgencyLevel] = {
    "blocking": UrgencyLevel.BLOCKING,
    "deadline_48h": UrgencyLevel.DEADLINE_48H,
    "deadline_1w": UrgencyLevel.DEADLINE_1W,
    "normal": UrgencyLevel.NORMAL,
}


def _build_goals(raw_goals: list[dict]) -> GoalSet:
    """Convert raw goal dicts into a GoalSet."""
    goals = []
    for g in raw_goals:
        goals.append(
            Goal(
                id=g["id"],
                title=g["title"],
                priority=g["priority"],
                description=g.get("description", ""),
            )
        )
    return GoalSet(goals=goals)


def _build_tasks(raw_tasks: list[dict]) -> list[Task]:
    """Convert raw task dicts into Task model instances."""
    tasks = []
    for t in raw_tasks:
        tasks.append(
            Task(
                id=t["id"],
                title=t["title"],
                description=t.get("description", ""),
                goal_alignment=t["goal_alignment"],
                impact=t["impact"],
                urgency=URGENCY_MAP.get(t["urgency"], UrgencyLevel.NORMAL),
                effort_hours=t["effort_hours"],
                blocks=t.get("blocks", []),
            )
        )
    return tasks


def _count_signals(tasks: list[Task]) -> tuple[int, int]:
    """Count extracted vs total possible signals for completeness scoring.

    Signals checked per task:
    - goal_alignment > 0
    - impact > 0
    - urgency != NORMAL (explicit urgency set)
    - blocks is non-empty (dependency info)
    - effort_hours != default (1.0)
    """
    total = 0
    extracted = 0
    for task in tasks:
        total += 5
        if task.goal_alignment > 0:
            extracted += 1
        if task.impact > 0:
            extracted += 1
        if task.urgency != UrgencyLevel.NORMAL:
            extracted += 1
        if task.blocks:
            extracted += 1
        if task.effort_hours != 1.0:
            extracted += 1
    return extracted, total


# ── Core benchmark logic ──────────────────────────────────────────────────

async def _run_single_case(case: dict) -> dict:
    """Run NorthStar analysis on a single test case and return results."""
    goals = _build_goals(case["goals"])
    tasks = _build_tasks(case["tasks"])

    config = ScoringConfig()

    # Use NullLLMClient (None) -- no LLM calls during benchmarks
    ranker = LeverageRanker(config=config, llm_client=None)
    pds_calc = PriorityDebtCalculator(llm_client=None)

    # Time the analysis
    start = time.monotonic()
    stack: PriorityStack = await ranker.rank(tasks, goals)
    pds_result = await pds_calc.calculate(stack.tasks)
    elapsed = time.monotonic() - start

    predicted_ranking = [t.id for t in stack.tasks]
    expert_ranking = case["expert_ranking"]

    # Simulate drift detection for scoring
    predicted_alerts: list[bool] = []
    actual_alerts: list[bool] = []
    for scenario in case["drift_scenarios"]:
        actual_alerts.append(scenario["should_alert"])
        # Heuristic: alert if current task is not in top 2 of ranking
        current_id = scenario["current_task_id"]
        top_ids = predicted_ranking[:2]
        should_fire = current_id not in top_ids
        predicted_alerts.append(should_fire)

    extracted, total = _count_signals(stack.tasks)

    return {
        "case_name": case["name"],
        "predicted_ranking": predicted_ranking,
        "expert_ranking": expert_ranking,
        "predicted_alerts": predicted_alerts,
        "actual_alerts": actual_alerts,
        "extracted_signals": extracted,
        "total_signals": total,
        "analysis_seconds": elapsed,
        "recommendations": pds_result.recommendations,
        "pds_score": pds_result.score,
        "pds_severity": pds_result.severity,
        "stack": stack,
        "pds_result": pds_result,
    }


# ── Public entry points ──────────────────────────────────────────────────

async def _run_benchmark_async() -> None:
    """Load all 5 test cases, run analysis, compute scores, print scorecard."""
    calculator = BenchmarkCalculator()
    all_scores: list[dict] = []

    print("=" * 70)
    print("  NorthStar Benchmark Suite")
    print("=" * 70)
    print()

    for i, case in enumerate(ALL_CASES, 1):
        print(f"  [{i}/5] Running: {case['name']}...", end=" ", flush=True)
        results = await _run_single_case(case)
        scores = calculator.score_test_case(results)
        all_scores.append(scores)

        tau = scores["ranking_accuracy"]
        total = scores["weighted_total"]
        print(f"tau={tau:+.3f}  score={total:.3f}")

    print()
    aggregated = calculator.aggregate_scores(all_scores)
    scorecard = calculator.format_scorecard(aggregated)
    print(scorecard)

    # Comparison with baselines
    print("-" * 70)
    print("  Baseline Comparison")
    print("-" * 70)
    print()

    for case in ALL_CASES:
        name = case["name"]
        expert = case["expert_ranking"]
        vanilla = VANILLA_RANKINGS.get(name, [])
        vanilla_tau = kendalls_tau(vanilla, expert)
        vanilla_pds = VANILLA_PDS.get(name, 0.0)
        expert_pds = EXPERT_PDS.get(name, 0.0)
        print(f"  {name}:")
        print(f"    Vanilla Cursor:  tau={vanilla_tau:+.3f}  PDS={vanilla_pds:.0f}")
        print(f"    Expert Panel:    tau=+1.000  PDS={expert_pds:.0f}")
        print()


def run_benchmark() -> None:
    """Synchronous wrapper for the benchmark suite."""
    asyncio.run(_run_benchmark_async())


async def _run_demo_async(case_num: int) -> None:
    """Run a single demo case with rich output."""
    if case_num < 1 or case_num > len(ALL_CASES):
        print(f"Error: case number must be 1-{len(ALL_CASES)}, got {case_num}")
        sys.exit(1)

    case = ALL_CASES[case_num - 1]
    results = await _run_single_case(case)

    print("=" * 70)
    print(f"  Demo Case {case_num}: {case['name']}")
    print("=" * 70)
    print()

    # Goals
    print("  GOALS:")
    for g in case["goals"]:
        print(f"    [{g['id']}] P{g['priority']}: {g['title']}")
        print(f"      {g['description']}")
    print()

    # Tasks with leverage scores
    print("  TASKS (NorthStar ranking):")
    stack: PriorityStack = results["stack"]
    for rank, task in enumerate(stack.tasks, 1):
        print(f"    #{rank}  {task.id}: {task.title}")
        print(f"        leverage={task.leverage_score:.0f}  "
              f"alignment={task.goal_alignment:.2f}  "
              f"impact={task.impact}  "
              f"urgency={task.urgency.value}  "
              f"effort={task.effort_hours}h  "
              f"blocks={len(task.blocks)}")
    print()

    # Expert comparison
    expert = case["expert_ranking"]
    predicted = results["predicted_ranking"]
    tau = kendalls_tau(predicted, expert)
    print(f"  RANKING ACCURACY:")
    print(f"    NorthStar:  {' -> '.join(predicted)}")
    print(f"    Expert:     {' -> '.join(expert)}")
    print(f"    Kendall's tau: {tau:+.3f}")
    print()

    # PDS
    pds = results["pds_result"]
    print(f"  PRIORITY DEBT SCORE:")
    print(f"    Score: {pds.score:.0f} / 10000  ({pds.severity})")
    expected = case["expected_pds_range"]
    in_range = expected[0] <= pds.score <= expected[1]
    print(f"    Expected range: {expected[0]:.0f} - {expected[1]:.0f}  "
          f"{'[OK]' if in_range else '[OUT OF RANGE]'}")
    print(f"    Diagnosis: {pds.diagnosis}")
    print()

    # Recommendations
    if pds.recommendations:
        print("  RECOMMENDATIONS:")
        for rec in pds.recommendations:
            print(f"    - {rec}")
        print()

    # Drift scenarios
    print("  DRIFT SCENARIOS:")
    for j, scenario in enumerate(case["drift_scenarios"]):
        predicted_alert = results["predicted_alerts"][j]
        actual_alert = scenario["should_alert"]
        match = "CORRECT" if predicted_alert == actual_alert else "WRONG"
        print(f"    Task {scenario['current_task_id']} "
              f"({scenario['session_minutes']}min): "
              f"predicted={'ALERT' if predicted_alert else 'OK':>5s}  "
              f"expected={'ALERT' if actual_alert else 'OK':>5s}  "
              f"[{match}]")
        print(f"      Reason: {scenario['reason']}")
    print()


def run_demo(case_num: int) -> None:
    """Synchronous wrapper for a single demo case."""
    asyncio.run(_run_demo_async(case_num))


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point with argparse."""
    parser = argparse.ArgumentParser(
        description="NorthStar Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m benchmarks.run_demos --benchmark\n"
            "  python -m benchmarks.run_demos --demo\n"
            "  python -m benchmarks.run_demos --case 3\n"
        ),
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run full benchmark suite across all 5 test cases",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run all demo cases with detailed output",
    )
    parser.add_argument(
        "--case",
        type=int,
        metavar="N",
        help="Run a specific demo case (1-5)",
    )

    args = parser.parse_args()

    if not any([args.benchmark, args.demo, args.case]):
        parser.print_help()
        sys.exit(0)

    if args.benchmark:
        run_benchmark()

    if args.demo:
        for i in range(1, len(ALL_CASES) + 1):
            run_demo(i)

    if args.case:
        run_demo(args.case)


if __name__ == "__main__":
    main()
