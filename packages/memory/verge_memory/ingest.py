"""Ingestion helpers for Cognee-backed memory.

Per Cognee Cloud docs: ``add`` loads raw data; ``cognify`` builds the graph.
``remember`` does both — we use add+cognify explicitly so plant SOPs land in
searchable memory (Phase 2.5 Knowledge Specialist).
"""

from __future__ import annotations

from datetime import UTC, datetime

from verge_schema.findings import RiskFinding

from .client import CogneeClient, CogneeResult


def ingest_document(client: CogneeClient, dataset: str, title: str, body: str) -> CogneeResult:
    """Add a markdown document to a dataset (no cognify)."""
    filename = f"{title.lower().replace(' ', '-')}.md"
    return client.add_text(dataset, f"# {title}\n\n{body.strip()}\n", filename=filename)


def ingest_and_cognify(
    client: CogneeClient,
    dataset: str,
    title: str,
    body: str,
    *,
    ensure_dataset: bool = True,
) -> CogneeResult:
    """Create dataset (idempotent) → add text → cognify. Used by doc ingest hooks."""
    if ensure_dataset:
        created = client.create_dataset(dataset)
        if not created.ok:
            return created
    added = ingest_document(client, dataset, title, body)
    if not added.ok:
        return added
    return client.cognify(dataset)


def ingest_closed_finding(client: CogneeClient, dataset: str, finding: RiskFinding) -> CogneeResult:
    closed_at = datetime.now(UTC).isoformat()
    signals = "\n".join(
        f"- {s.kind}:{s.ref_id} - {s.summary}" for s in finding.contributing_signals
    )
    body = (
        f"Finding ID: {finding.finding_id}\n"
        f"Closed at: {closed_at}\n"
        f"Zone: {finding.zone_id}\n"
        f"Title: {finding.title}\n"
        f"Lead-time band: {finding.lead_time_band}\n"
        f"Confidence: {finding.confidence}\n\n"
        f"Contributing signals:\n{signals or '- none recorded'}\n\n"
        f"Lineage: {', '.join(finding.lineage)}\n"
    )
    return ingest_and_cognify(client, dataset, f"Closed finding {finding.finding_id}", body)


def ingest_open_finding(client: CogneeClient, dataset: str, finding: RiskFinding) -> CogneeResult:
    """Live finding → Cognee so the agent can recall open risk, not only closed."""
    seen_at = datetime.now(UTC).isoformat()
    signals = "\n".join(
        f"- {s.kind}:{s.ref_id} - {s.summary}" for s in finding.contributing_signals
    )
    body = (
        f"Finding ID: {finding.finding_id}\n"
        f"Observed at: {seen_at}\n"
        f"State: {finding.state}\n"
        f"Zone: {finding.zone_id}\n"
        f"Title: {finding.title}\n"
        f"Lead-time band: {finding.lead_time_band}\n"
        f"Confidence: {finding.confidence}\n\n"
        f"Contributing signals:\n{signals or '- none recorded'}\n\n"
        f"Lineage: {', '.join(finding.lineage)}\n"
    )
    return ingest_and_cognify(client, dataset, f"Open finding {finding.finding_id}", body)


def ingest_vision_watch(
    client: CogneeClient,
    dataset: str,
    *,
    camera_id: str,
    zone_id: str,
    labels: list[str],
    detection_count: int,
) -> CogneeResult:
    """Periodic vision summary for continuous watch → searchable memory."""
    seen_at = datetime.now(UTC).isoformat()
    label_txt = ", ".join(labels) if labels else "none"
    body = (
        f"Watch vision update at {seen_at}\n"
        f"Camera: {camera_id}\n"
        f"Zone: {zone_id}\n"
        f"Detections: {detection_count}\n"
        f"Labels: {label_txt}\n"
    )
    return ingest_and_cognify(
        client, dataset, f"Vision watch {camera_id} {seen_at[:16]}", body
    )


def ingest_feedback(
    client: CogneeClient,
    dataset: str,
    finding: RiskFinding,
    *,
    verdict: str,
    reason_code: str | None = None,
    reason_text: str | None = None,
) -> CogneeResult:
    body = (
        f"Finding ID: {finding.finding_id}\n"
        f"Zone: {finding.zone_id}\n"
        f"Title: {finding.title}\n"
        f"Verdict: {verdict}\n"
        f"Reason code: {reason_code or 'none'}\n"
        f"Reason text: {reason_text or 'none'}\n"
        f"Lineage: {', '.join(finding.lineage)}\n"
    )
    return ingest_and_cognify(
        client, dataset, f"Feedback {finding.finding_id} {verdict}", body
    )
