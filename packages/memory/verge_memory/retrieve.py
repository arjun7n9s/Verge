"""Retrieve context for a finding from Cognee memory."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from verge_schema.findings import RiskFinding

from .client import CogneeClient, CogneeResult
from .datasets import dataset_name
from .ingest import ingest_document

CORPUS = Path(__file__).parent / "corpus"
_SEEDED: set[str] = set()


def _empty(finding_id: str, *, degraded: bool, reason: str | None = None) -> dict:
    body = {
        "findingId": finding_id,
        "similarIncidents": [],
        "regulatoryClauses": [],
        "plantHistory": [],
        "degraded": degraded,
    }
    if reason:
        body["reason"] = reason
    return body


def _text_from_result(item: Any) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in (
            "search_result",
            "text",
            "content",
            "context",
            "result",
            "summary",
            "text_result",
        ):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return json.dumps(item, sort_keys=True)
    return str(item)


def _result_items(result: CogneeResult) -> list[Any]:
    data = result.data
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "data", "items", "context"):
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [value]
    if isinstance(data, str):
        return [data]
    return []


def _excerpt(text: str, limit: int = 360) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else f"{clean[: limit - 1].rstrip()}..."


def _similar(items: list[Any]) -> list[dict]:
    out = []
    for item in items[:3]:
        text = _text_from_result(item)
        out.append(
            {
                "title": "Cognee memory result",
                "year": None,
                "excerpt": _excerpt(text),
                "source": "cognee",
            }
        )
    return out


def _clauses(items: list[Any]) -> list[dict]:
    out = []
    for i, item in enumerate(items[:5], start=1):
        text = _text_from_result(item)
        out.append(
            {"id": f"COGNEE-{i}", "title": "Relevant safety clause", "excerpt": _excerpt(text)}
        )
    return out


def _history(items: list[Any]) -> list[dict]:
    out = []
    for item in items[:3]:
        text = _text_from_result(item)
        out.append({"findingId": "unknown", "summary": _excerpt(text), "closedAt": None})
    return out


def _corpus_docs() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for summary in sorted(CORPUS.glob("*-summary.md")):
        docs.append((summary.stem, summary.read_text(encoding="utf-8")))
    clauses = CORPUS / "oisd-stubs.json"
    if clauses.exists():
        raw = json.loads(clauses.read_text(encoding="utf-8"))
        docs.append(("oisd-stubs", json.dumps(raw, indent=2)))
    return docs


def ensure_seeded(client: CogneeClient, dataset: str) -> CogneeResult:
    if dataset in _SEEDED:
        return CogneeResult.success({"seeded": True, "cached": True})

    created = client.create_dataset(dataset)
    if not created.ok:
        return created

    for title, body in _corpus_docs():
        added = ingest_document(client, dataset, title, body)
        if not added.ok:
            return added

    cognified = client.cognify(dataset)
    if not cognified.ok:
        return cognified

    _SEEDED.add(dataset)
    return CogneeResult.success({"seeded": True})


def context_for_finding(
    finding: RiskFinding,
    *,
    client: CogneeClient | None = None,
    env: dict[str, str] | None = None,
) -> dict:
    env = env or dict(os.environ)
    dataset = dataset_name(env)
    client = client or CogneeClient.from_env(env)

    seeded = ensure_seeded(client, dataset)
    if not seeded.ok:
        return _empty(finding.finding_id, degraded=True, reason=seeded.reason)

    lineage = ", ".join(finding.lineage)
    signals = "; ".join(s.summary for s in finding.contributing_signals)
    base = (
        f"Finding {finding.finding_id} in zone {finding.zone_id}: {finding.title}. "
        f"Lead-time band {finding.lead_time_band}. Lineage: {lineage}. Signals: {signals}."
    )

    similar = client.search(dataset, f"Similar industrial incidents and near misses for: {base}")
    clauses = client.search(dataset, f"Applicable OISD or industrial safety clauses for: {base}")
    history = client.search(dataset, f"Closed Verge plant findings similar to: {base}")
    results = [similar, clauses, history]
    failed = next((r for r in results if not r.ok), None)
    if failed:
        return _empty(finding.finding_id, degraded=True, reason=failed.reason)

    return {
        "findingId": finding.finding_id,
        "similarIncidents": _similar(_result_items(similar)),
        "regulatoryClauses": _clauses(_result_items(clauses)),
        "plantHistory": _history(_result_items(history)),
        "degraded": False,
    }
