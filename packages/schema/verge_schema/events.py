"""Cross-plane live events that can contribute to compound risk (Phase 2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ._base import VergeModel


class VoiceEvent(VergeModel):
    event_id: str
    ts: datetime
    transcript: str = ""  # English ops text (canonical for fusion/agents)
    transcript_original: str | None = None  # Melia original when non-English
    languages_detected: list[str] = Field(default_factory=list)
    zone_id: str | None = None
    hazards: list[str] = Field(default_factory=list)
    equipment_ids: list[str] = Field(default_factory=list)
    source: str = "radio"  # radio | handover | near-miss | manual | transcribe
    # Browser path when raw audio was retained (e.g. /api/voice/clips/{id})
    audio_clip_uri: str | None = None


class VisionDetection(VergeModel):
    detection_id: str
    ts: datetime
    camera_id: str
    zone_id: str
    label: str  # person | no-hardhat | smoke | vehicle | …
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    frame_uri: str | None = None
