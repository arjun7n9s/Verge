"""Knowledge eval gates — entity F1 on gold + citation groundedness."""

from __future__ import annotations

import json
from pathlib import Path

from verge_docintel import extract_entities

from eval.knowledge.metrics import citation_groundedness, entity_f1

GOLD = Path(__file__).resolve().parents[1] / "gold" / "entities.json"


def test_entity_f1_on_gold_set() -> None:
    docs = json.loads(GOLD.read_text(encoding="utf-8"))["docs"]
    scores = []
    for doc in docs:
        pred = [
            (str(e.kind), e.normalized or e.raw)
            for e in extract_entities(doc["text"], document_id=doc["id"])
        ]
        gold = [(e["kind"], e["normalized"]) for e in doc["entities"]]
        scores.append(entity_f1(pred, gold)["f1"])
    mean_f1 = sum(scores) / len(scores)
    # Starter regex extractor DoD ramp — raise toward 0.85 as extractors improve.
    assert mean_f1 >= 0.55, f"mean entity F1 too low: {mean_f1}"


def test_citation_groundedness_metric() -> None:
    answer = "Confirm gas detector LEL-04 in zone B-04 before welding."
    citations = [
        {
            "excerpt": "Confirm gas detector LEL-04 in zone B-04 is live and trending.",
            "documentId": "DOC-1",
        }
    ]
    m = citation_groundedness(answer, citations)
    assert m["grounded"] is True
    assert m["citationCount"] == 1


def test_ungrounded_without_citations() -> None:
    m = citation_groundedness("Anything", [])
    assert m["grounded"] is False
