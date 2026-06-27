"""Audit, evidence, alerts, actions (spec 4.4, P6)."""

from datetime import datetime

from pydantic import Field

from ._base import VergeModel


class Alert(VergeModel):
    alert_id: str
    finding_id: str
    channels: list[str] = Field(default_factory=list)  # sms/ivr/pa/app/console
    languages: list[str] = Field(default_factory=list)
    body: str
    issued_at: datetime


class Action(VergeModel):
    action_id: str
    finding_id: str
    kind: str  # recommend-permit-pause | evacuate | ...
    advisory: bool = True  # Verge never writes to OT/control (P8)
    actor: str | None = None
    timestamp: datetime


class EvidencePack(VergeModel):
    pack_id: str
    finding_id: str
    items: list[str] = Field(default_factory=list)  # object-store keys
    manifest_hash: str
    created_at: datetime


class AuditEntry(VergeModel):
    """Append-only, hash-chained, attributable (P6)."""

    entry_id: str
    timestamp: datetime
    actor: str
    kind: str  # finding-event | action | alert | feedback | ...
    payload: dict = Field(default_factory=dict)
    hash: str
    prev_hash: str | None = None
