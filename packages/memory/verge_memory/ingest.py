"""Ingestion helpers for Cognee-backed memory."""

from __future__ import annotations

from datetime import UTC, datetime

from verge_schema.findings import RiskFinding

from .client import CogneeClient, CogneeResult


def ingest_document(client: CogneeClient, dataset: str, title: str, body: str) -> CogneeResult:
    filename = f"{title.lower().replace(' ', '-')}.md"
    return client.add_text(dataset, f"# {title}\n\n{body.strip()}\n", filename=filename)


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
    return ingest_document(client, dataset, f"Closed finding {finding.finding_id}", body)
