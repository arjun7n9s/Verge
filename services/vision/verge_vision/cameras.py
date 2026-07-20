"""Camera -> zone registry for the vision plane (spec §5).

CCTV placement is fixed at commissioning time — each camera covers one zone.
Optional ``source`` (rtsp/file/device index/``demo``) powers Live Ops streams.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "samples"
DEMO_CAMERAS = SAMPLES_DIR / "vizag-cameras.json"


@dataclass(frozen=True)
class CameraZone:
    zone_id: str
    restricted: bool = False
    # rtsp://… | file path | device index string | "demo" labeled pattern
    source: str | None = None


def load_camera_registry(path: str | Path) -> dict[str, CameraZone]:
    """Parse a ``{cameraId: {zoneId, restricted, source?}}`` JSON file.

    Tolerant of malformed entries (P4 — a bad row is dropped, never crashes
    wiring); raises only if the file itself can't be read or isn't a JSON
    object, so callers can decide how to degrade.
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("camera registry must be a JSON object keyed by camera id")
    out: dict[str, CameraZone] = {}
    for camera_id, entry in raw.items():
        if not isinstance(entry, dict) or not entry.get("zoneId"):
            continue
        source = entry.get("source") or entry.get("rtspUrl") or entry.get("url")
        out[camera_id] = CameraZone(
            zone_id=str(entry["zoneId"]),
            restricted=bool(entry.get("restricted", False)),
            source=str(source).strip() if source else None,
        )
    return out


def camera_registry_from_env(env: Mapping[str, str]) -> dict[str, CameraZone]:
    """``VERGE_VISION_CAMERAS`` if set and readable, else the bundled demo registry.

    Optional: ``VERGE_VISION_RTSP_URL`` + ``VERGE_VISION_CAMERA_ID`` overlays a
    live source onto one camera id (worker + Live Ops share the same feed).
    """
    path = env.get("VERGE_VISION_CAMERAS")
    reg: dict[str, CameraZone] = {}
    if path:
        try:
            reg = load_camera_registry(path)
        except (ValueError, OSError):
            reg = {}
    if not reg and DEMO_CAMERAS.exists():
        try:
            reg = load_camera_registry(DEMO_CAMERAS)
        except (ValueError, OSError):
            reg = {}
    rtsp = (env.get("VERGE_VISION_RTSP_URL") or "").strip()
    cam_id = (env.get("VERGE_VISION_CAMERA_ID") or "CAM-B04").strip()
    if rtsp and cam_id:
        existing = reg.get(cam_id)
        reg[cam_id] = CameraZone(
            zone_id=existing.zone_id if existing else "B-04",
            restricted=existing.restricted if existing else False,
            source=rtsp,
        )
    return reg
