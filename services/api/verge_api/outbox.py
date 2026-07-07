"""Transactional outbox for post-commit SSE/stream notifications (audit §4)."""

from __future__ import annotations

FINDINGS_UPDATED = "findings-updated"
FINDING_TRANSITION = "finding-transition"
READING_INGESTED = "reading-ingested"
