"""Inter-rater agreement metrics (Cohen's kappa)."""

from __future__ import annotations

from collections import Counter


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Compute Cohen's kappa between two sets of categorical labels.

    Args:
        labels_a: Labels from rater/provider A.
        labels_b: Labels from rater/provider B.

    Returns:
        Cohen's kappa coefficient (-1.0 to 1.0).
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("Label lists must be the same length.")
    n = len(labels_a)
    if n == 0:
        return 0.0

    categories = sorted(set(labels_a) | set(labels_b))
    cat_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    # Build confusion matrix
    matrix = [[0] * k for _ in range(k)]
    for a, b in zip(labels_a, labels_b):
        matrix[cat_idx[a]][cat_idx[b]] += 1

    # Observed agreement
    po = sum(matrix[i][i] for i in range(k)) / n

    # Expected agreement
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[j][i] for j in range(k)) for i in range(k)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(k)) / (n * n)

    if pe == 1.0:
        return 1.0

    return (po - pe) / (1.0 - pe)


def multi_provider_agreement(
    provider_labels: dict[str, list[str]],
) -> dict[tuple[str, str], float]:
    """Compute pairwise Cohen's kappa across multiple providers."""
    providers = sorted(provider_labels.keys())
    results: dict[tuple[str, str], float] = {}

    for i, a in enumerate(providers):
        for b in providers[i + 1 :]:
            results[(a, b)] = cohens_kappa(provider_labels[a], provider_labels[b])

    return results
