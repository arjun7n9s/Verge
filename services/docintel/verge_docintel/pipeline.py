"""In-memory document registry + process pipeline (Phase 1 MVP)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from verge_schema.documents import (
    DocumentAsset,
    DocumentChunk,
    DocumentKind,
    DocumentStatus,
    EntityMention,
)

from .extract import extract_entities
from .textify import textify_bytes

_KIND_HINTS: list[tuple[DocumentKind, tuple[str, ...]]] = [
    (DocumentKind.SOP, ("sop", "procedure", "operating")),
    (DocumentKind.WORK_ORDER, ("work-order", "workorder", "wo-", "cmms")),
    (DocumentKind.INSPECTION, ("inspection", "checklist")),
    (DocumentKind.REGULATION, ("oisd", "factory-act", "peso", "regulation")),
    (DocumentKind.PID, ("p&id", "pid", "drawing")),
    (DocumentKind.MANUAL, ("manual", "oem")),
    (DocumentKind.NCR, ("ncr", "non-conformance", "nonconformance")),
]


def classify_kind(filename: str, text: str) -> DocumentKind:
    blob = f"{filename}\n{text[:2000]}".lower()
    for kind, needles in _KIND_HINTS:
        if any(n in blob for n in needles):
            return kind
    return DocumentKind.OTHER


def chunk_text(document_id: str, text: str, *, max_chars: int = 1200) -> list[DocumentChunk]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        paras = [text.strip()] if text.strip() else []
    chunks: list[DocumentChunk] = []
    buf = ""
    order = 0
    for para in paras:
        if len(buf) + len(para) + 2 > max_chars and buf:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{document_id}-c{order:04d}",
                    document_id=document_id,
                    text=buf.strip(),
                    order=order,
                    page=None,
                )
            )
            order += 1
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf.strip():
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document_id}-c{order:04d}",
                document_id=document_id,
                text=buf.strip(),
                order=order,
            )
        )
    return chunks


class DocIntelStore:
    """Process-local registry — swap for Postgres/MinIO in a later phase."""

    def __init__(self) -> None:
        self.documents: dict[str, DocumentAsset] = {}
        self.chunks: dict[str, list[DocumentChunk]] = {}
        self.entities: dict[str, list[EntityMention]] = {}
        self.texts: dict[str, str] = {}

    def list_documents(self) -> list[DocumentAsset]:
        return sorted(self.documents.values(), key=lambda d: d.created_at, reverse=True)

    def get(self, document_id: str) -> DocumentAsset | None:
        return self.documents.get(document_id)


def process_bytes(
    store: DocIntelStore,
    data: bytes,
    *,
    filename: str,
    mime_type: str = "application/octet-stream",
    title: str | None = None,
    plant_pack: str | None = None,
) -> DocumentAsset:
    doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now(UTC)
    asset = DocumentAsset(
        document_id=doc_id,
        title=title or filename or doc_id,
        kind=DocumentKind.OTHER,
        status=DocumentStatus.PROCESSING,
        source_name=filename,
        mime_type=mime_type,
        created_at=now,
        plant_pack=plant_pack,
    )
    store.documents[doc_id] = asset

    result = textify_bytes(data, filename=filename, mime=mime_type)
    if not result.text.strip():
        asset.status = DocumentStatus.FAILED
        asset.error = result.reason or "empty-text"
        return asset

    asset.kind = classify_kind(filename, result.text)
    asset.page_count = result.page_count
    asset.text_chars = len(result.text)
    chunks = chunk_text(doc_id, result.text)
    entities = extract_entities(result.text, document_id=doc_id)
    store.chunks[doc_id] = chunks
    store.entities[doc_id] = entities
    store.texts[doc_id] = result.text
    asset.status = DocumentStatus.READY
    if result.degraded:
        asset.error = result.reason or result.backend
    return asset
