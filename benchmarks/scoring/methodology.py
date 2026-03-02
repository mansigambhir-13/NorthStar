"""Defines the 5-dimension scoring methodology for NorthStar benchmarks.

Each dimension measures a distinct aspect of prioritization quality.
Weights sum to 1.0 and reflect relative importance for developer productivity.
"""

from __future__ import annotations

SCORING_DIMENSIONS: dict[str, dict[str, object]] = {
    "ranking_accuracy": {
        "name": "Ranking Accuracy",
        "weight": 0.30,
        "description": (
            "How well NorthStar's task ordering matches expert-determined "
            "optimal ordering. Measured via Kendall's tau rank correlation."
        ),
        "metric": "kendalls_tau",
    },
    "drift_detection": {
        "name": "Drift Detection",
        "weight": 0.20,
        "description": (
            "Ability to correctly identify when a developer is working on "
            "a low-leverage task and should be alerted. Measured via F1 score "
            "across drift scenario ground-truth labels."
        ),
        "metric": "f1_score",
    },
    "completeness": {
        "name": "Signal Completeness",
        "weight": 0.20,
        "description": (
            "Fraction of relevant signals (goal alignment, urgency, "
            "dependencies, effort) that NorthStar successfully extracts "
            "and incorporates into scoring."
        ),
        "metric": "completeness_score",
    },
    "speed": {
        "name": "Analysis Speed",
        "weight": 0.15,
        "description": (
            "Time taken to produce a full ranking and PDS from raw inputs. "
            "Target is under 60 seconds for a typical project with "
            "10-50 tasks."
        ),
        "metric": "speed_score",
    },
    "actionability": {
        "name": "Actionability",
        "weight": 0.15,
        "description": (
            "Quality of recommendations and diagnosis text. Measures whether "
            "outputs are specific, concrete, and directly usable by a developer "
            "without further interpretation."
        ),
        "metric": "actionability_score",
    },
}


def get_dimension_weights() -> dict[str, float]:
    """Return a mapping of dimension key to its weight."""
    return {
        key: float(dim["weight"])
        for key, dim in SCORING_DIMENSIONS.items()
    }


def validate_weights() -> bool:
    """Confirm all weights sum to 1.0 (within floating-point tolerance)."""
    total = sum(float(dim["weight"]) for dim in SCORING_DIMENSIONS.values())
    return abs(total - 1.0) < 1e-9
