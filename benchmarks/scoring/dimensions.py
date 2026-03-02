"""Implements each of the 5 scoring dimensions for NorthStar benchmarks.

All functions return a float in [0, 1] (or [-1, 1] for Kendall's tau)
suitable for weighted aggregation.
"""

from __future__ import annotations

import math
import re


def kendalls_tau(predicted: list[str], expert: list[str]) -> float:
    """Compute Kendall's tau rank correlation between two orderings.

    Parameters
    ----------
    predicted : list[str]
        Task IDs in NorthStar's predicted order (highest leverage first).
    expert : list[str]
        Task IDs in expert-determined optimal order.

    Returns
    -------
    float
        Correlation coefficient in [-1, 1]. 1.0 = perfect agreement,
        -1.0 = perfectly reversed, 0.0 = no correlation.
    """
    if not predicted or not expert:
        return 0.0

    # Build rank maps (only for IDs present in both lists)
    common = set(predicted) & set(expert)
    if len(common) < 2:
        return 0.0

    pred_rank = {item: i for i, item in enumerate(predicted) if item in common}
    exp_rank = {item: i for i, item in enumerate(expert) if item in common}

    items = sorted(common)
    n = len(items)

    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            pred_diff = pred_rank[items[i]] - pred_rank[items[j]]
            exp_diff = exp_rank[items[i]] - exp_rank[items[j]]
            product = pred_diff * exp_diff
            if product > 0:
                concordant += 1
            elif product < 0:
                discordant += 1
            # ties (product == 0) are ignored

    total_pairs = n * (n - 1) / 2
    if total_pairs == 0:
        return 0.0

    return (concordant - discordant) / total_pairs


def f1_score(predicted_alerts: list[bool], actual_alerts: list[bool]) -> float:
    """Compute F1 score for drift detection accuracy.

    Parameters
    ----------
    predicted_alerts : list[bool]
        Whether NorthStar fired a drift alert for each scenario.
    actual_alerts : list[bool]
        Ground-truth: whether a drift alert should have been fired.

    Returns
    -------
    float
        F1 score in [0, 1]. 1.0 = perfect precision and recall.
    """
    if len(predicted_alerts) != len(actual_alerts):
        raise ValueError(
            f"Length mismatch: predicted={len(predicted_alerts)}, "
            f"actual={len(actual_alerts)}"
        )

    if not predicted_alerts:
        return 0.0

    tp = sum(1 for p, a in zip(predicted_alerts, actual_alerts) if p and a)
    fp = sum(1 for p, a in zip(predicted_alerts, actual_alerts) if p and not a)
    fn = sum(1 for p, a in zip(predicted_alerts, actual_alerts) if not p and a)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def completeness_score(extracted_signals: int, total_signals: int) -> float:
    """Compute signal extraction completeness.

    Parameters
    ----------
    extracted_signals : int
        Number of relevant signals NorthStar successfully extracted
        (e.g., goal alignment detected, urgency parsed, dependencies mapped).
    total_signals : int
        Total number of relevant signals present in the test case.

    Returns
    -------
    float
        Score in [0, 1]. 1.0 = all signals captured.
    """
    if total_signals <= 0:
        return 0.0
    return max(0.0, min(1.0, extracted_signals / total_signals))


def speed_score(seconds: float, target: float = 60.0) -> float:
    """Compute speed score with exponential decay past target.

    Parameters
    ----------
    seconds : float
        Actual wall-clock time for the analysis run.
    target : float
        Target time in seconds. Scores 1.0 if under this threshold.

    Returns
    -------
    float
        Score in [0, 1]. 1.0 if seconds <= target, decays exponentially
        for longer durations.
    """
    if seconds <= 0:
        return 1.0
    if seconds <= target:
        return 1.0
    # Exponential decay: halves every `target` seconds past the threshold
    overshoot = (seconds - target) / target
    return max(0.0, math.exp(-0.693 * overshoot))  # ln(2) ~ 0.693


def actionability_score(recommendations: list[str]) -> float:
    """Heuristic score for recommendation actionability.

    Evaluates recommendations based on:
    - Non-trivial length (>20 chars each)
    - Specificity: contains task names, numbers, or concrete verbs
    - Quantity: at least 1 recommendation expected

    Parameters
    ----------
    recommendations : list[str]
        List of recommendation strings from NorthStar output.

    Returns
    -------
    float
        Score in [0, 1]. Higher means more actionable recommendations.
    """
    if not recommendations:
        return 0.0

    # Concrete action verbs that indicate specificity
    action_verbs = re.compile(
        r"\b(complete|implement|fix|refactor|prioritize|remove|add|migrate|"
        r"deploy|test|review|update|replace|split|merge|pause|resume)\b",
        re.IGNORECASE,
    )

    # Patterns indicating specificity (task IDs, numbers, quoted names)
    specificity_patterns = re.compile(
        r"(?:'[^']+')|\b\d+\.?\d*\b|(?:task[_-]?\w+)",
        re.IGNORECASE,
    )

    total_score = 0.0
    for rec in recommendations:
        item_score = 0.0

        # Length component: 0.0 to 0.4
        if len(rec) > 20:
            item_score += 0.2
        if len(rec) > 50:
            item_score += 0.2

        # Action verb component: 0.0 to 0.3
        verb_matches = action_verbs.findall(rec)
        item_score += min(0.3, len(verb_matches) * 0.15)

        # Specificity component: 0.0 to 0.3
        spec_matches = specificity_patterns.findall(rec)
        item_score += min(0.3, len(spec_matches) * 0.15)

        total_score += min(1.0, item_score)

    # Average across all recommendations
    avg = total_score / len(recommendations)

    # Small bonus for providing multiple recommendations (up to 3)
    quantity_bonus = min(0.1, (len(recommendations) - 1) * 0.05)

    return min(1.0, avg + quantity_bonus)
