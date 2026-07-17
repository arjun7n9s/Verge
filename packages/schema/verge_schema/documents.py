"""Industrial document assets + extracted entities (Knowledge wedge)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from ._base import VergeModel


class DocumentKind(StrEnum):
    SOP = "sop"
    WORK_ORDER = "work-order"
    INSPECTION = "inspection"
    REGULATION = "regulation"
    PID = "pid"
    MANUAL = "manual"
    NCR = "ncr"
    EMAIL = "email"
    OTHER = "other"


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class EntityKind(StrEnum):
    EQUIPMENT = "equipment"
    ZONE = "zone"
    PERMIT = "permit"
    CLAUSE = "clause"
    PERSON = "person"
    FAILURE_CODE = "failure-code"
    PARAMETER = "parameter"
    DATE = "date"


class DocumentAsset(VergeModel):
    document_id: str
    title: str
    kind: DocumentKind = DocumentKind.OTHER
    status: DocumentStatus = DocumentStatus.QUEUED
    source_name: str = ""
    mime_type: str = "application/octet-stream"
    page_count: int = 0
    text_chars: int = 0
    created_at: datetime
    error: str | None = None
    plant_pack: str | None = None


class DocumentChunk(VergeModel):
    chunk_id: str
    document_id: str
    page: int | None = None
    section: str | None = None
    text: str
    order: int = 0


class EntityMention(VergeModel):
    entity_id: str
    document_id: str
    kind: EntityKind
    raw: str
    normalized: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    page: int | None = None
    resolved_ref: str | None = None  # twin equipment id / zone id when linked
