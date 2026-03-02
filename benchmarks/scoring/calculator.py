"""Benchmark score calculator that aggregates all 5 dimensions."""

from __future__ import annotations

from benchmarks.scoring.dimensions import (
    actionability_score,
    completeness_score,
    f1_score,
    kendalls_tau,
    speed_score,
)
from benchmarks.scoring.methodology import SCORING_DIMENSIONS, get_dimension_weights


class BenchmarkCalculator:
    """Compute, aggregate, and format NorthStar benchmark scores."""

    def __init__(self) -> None:
        self.weights = get_dimension_weights()

    def score_test_case(self, results: dict) -> dict:
        """Compute all 5 dimension scores for a single test case.

        Parameters
        ----------
        results : dict
            Must contain:
            - predicted_ranking: list[str] -- NorthStar's task ID ordering
            - expert_ranking: list[str] -- expert optimal ordering
            - predicted_alerts: list[bool] -- drift alerts fired
            - actual_alerts: list[bool] -- ground-truth drift alerts
            - extracted_signals: int -- signals NorthStar extracted
            - total_signals: int -- total available signals
            - analysis_seconds: float -- wall-clock time
            - recommendations: list[str] -- NorthStar's recommendations

        Returns
        -------
        dict
            Scores for each dimension plus a weighted_total.
        """
        scores = {
            "ranking_accuracy": kendalls_tau(
                results["predicted_ranking"],
                results["expert_ranking"],
            ),
            "drift_detection": f1_score(
                results["predicted_alerts"],
                results["actual_alerts"],
            ),
            "completeness": completeness_score(
                results["extracted_signals"],
                results["total_signals"],
            ),
            "speed": speed_score(
                results["analysis_seconds"],
            ),
            "actionability": actionability_score(
                results["recommendations"],
            ),
        }

        # Normalize ranking_accuracy from [-1, 1] to [0, 1] for aggregation
        tau_normalized = (scores["ranking_accuracy"] + 1.0) / 2.0

        weighted_total = (
            self.weights["ranking_accuracy"] * tau_normalized
            + self.weights["drift_detection"] * scores["drift_detection"]
            + self.weights["completeness"] * scores["completeness"]
            + self.weights["speed"] * scores["speed"]
            + self.weights["actionability"] * scores["actionability"]
        )

        scores["ranking_accuracy_normalized"] = tau_normalized
        scores["weighted_total"] = weighted_total

        return scores

    def aggregate_scores(self, cases: list[dict]) -> dict:
        """Compute weighted average across multiple test case score dicts.

        Parameters
        ----------
        cases : list[dict]
            Each element is a dict returned by ``score_test_case``.

        Returns
        -------
        dict
            Averaged scores for each dimension plus overall weighted_total.
        """
        if not cases:
            return {
                "ranking_accuracy": 0.0,
                "drift_detection": 0.0,
                "completeness": 0.0,
                "speed": 0.0,
                "actionability": 0.0,
                "weighted_total": 0.0,
            }

        n = len(cases)
        agg: dict[str, float] = {}
        keys = [
            "ranking_accuracy",
            "drift_detection",
            "completeness",
            "speed",
            "actionability",
            "weighted_total",
        ]
        for key in keys:
            agg[key] = sum(c.get(key, 0.0) for c in cases) / n

        return agg

    def format_scorecard(self, scores: dict) -> str:
        """Format scores as a readable markdown scorecard.

        Parameters
        ----------
        scores : dict
            Either a single test case or aggregated scores dict.

        Returns
        -------
        str
            Markdown-formatted scorecard.
        """
        lines = [
            "# NorthStar Benchmark Scorecard",
            "",
            "| Dimension | Weight | Score | Weighted |",
            "|-----------|--------|-------|----------|",
        ]

        for key, dim in SCORING_DIMENSIONS.items():
            weight = float(dim["weight"])
            raw = scores.get(key, 0.0)

            # For ranking accuracy, use normalized version if available
            if key == "ranking_accuracy":
                display_raw = raw
                norm = scores.get("ranking_accuracy_normalized", (raw + 1.0) / 2.0)
                weighted = weight * norm
            else:
                display_raw = raw
                weighted = weight * raw

            lines.append(
                f"| {dim['name']:<20s} | {weight:.2f}   | "
                f"{display_raw:>5.3f} | {weighted:>8.4f} |"
            )

        total = scores.get("weighted_total", 0.0)
        lines.append(f"|{'':20s} |        | **Total** | **{total:.4f}** |")
        lines.append("")

        # Grade
        if total >= 0.9:
            grade = "A"
        elif total >= 0.8:
            grade = "B"
        elif total >= 0.7:
            grade = "C"
        elif total >= 0.6:
            grade = "D"
        else:
            grade = "F"

        lines.append(f"**Overall Grade: {grade}** ({total:.1%})")
        lines.append("")

        return "\n".join(lines)
