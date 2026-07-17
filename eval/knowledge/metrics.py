"""Lightweight metrics for Living Knowledge DoD gates."""

from __future__ import annotations

from collections.abc import Iterable


def entity_f1(
    predicted: Iterable[tuple[str, str]],
    gold: Iterable[tuple[str, str]],
) -> dict[str, float]:
    """Micro F1 over (kind, normalized) pairs."""
    pred = {(k.lower(), n.lower()) for k, n in predicted if k and n}
    truth = {(k.lower(), n.lower()) for k, n in gold if k and n}
    if not pred and not truth:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(pred & truth)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(truth) if truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": float(tp),
        "fp": float(len(pred - truth)),
        "fn": float(len(truth - pred)),
    }


def citation_groundedness(
    answer: str,
    citations: list[dict],
    *,
    min_overlap: int = 2,
) -> dict[str, float | bool]:
    """Answer is grounded when it has citations and shares tokens with an excerpt."""
    if not answer.strip():
        return {"grounded": False, "citationCount": 0.0, "overlap": 0.0}
    if not citations:
        return {"grounded": False, "citationCount": 0.0, "overlap": 0.0}
    ans_toks = {t for t in answer.lower().split() if len(t) > 3}
    best = 0
    for c in citations:
        excerpt = (c.get("excerpt") or "").lower()
        ex_toks = {t for t in excerpt.split() if len(t) > 3}
        best = max(best, len(ans_toks & ex_toks))
    grounded = best >= min_overlap
    return {
        "grounded": grounded,
        "citationCount": float(len(citations)),
        "overlap": float(best),
    }
