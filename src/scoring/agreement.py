"""Inter-provider agreement metrics."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from ..utils.logging import get_logger

logger = get_logger("scoring.agreement")


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Compute Cohen's kappa between two label sequences.

    Args:
        labels_a: Labels from rater A.
        labels_b: Labels from rater B.

    Returns:
        Kappa statistic (-1.0 to 1.0). 1.0 = perfect agreement, 0.0 = chance.
    """
    if len(labels_a) != len(labels_b):
        raise ValueError(
            f"Label sequences must have equal length: {len(labels_a)} != {len(labels_b)}"
        )

    n = len(labels_a)
    if n == 0:
        return 0.0

    all_labels = sorted(set(labels_a) | set(labels_b))
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)

    # Observed agreement
    p_o = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n

    # Expected agreement by chance
    p_e = sum((counts_a[label] / n) * (counts_b[label] / n) for label in all_labels)

    if p_e == 1.0:
        return 1.0

    kappa = (p_o - p_e) / (1 - p_e)
    return kappa


def multi_provider_agreement(
    provider_labels: dict[str, list[str]],
) -> dict[tuple[str, str], float]:
    """Compute pairwise Cohen's kappa across all providers.

    Args:
        provider_labels: Mapping of provider name -> list of labels.

    Returns:
        Dict mapping (provider_a, provider_b) -> kappa score.
    """
    results: dict[tuple[str, str], float] = {}
    providers = sorted(provider_labels.keys())

    for a, b in combinations(providers, 2):
        kappa = cohens_kappa(provider_labels[a], provider_labels[b])
        results[(a, b)] = kappa
        logger.info(f"agreement {a}_vs_{b} kappa={kappa:.3f}")

    return results
