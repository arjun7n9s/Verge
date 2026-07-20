"""Live camera snapshot / MJPEG grabbers for the console Live Ops wall.

Sources come from the vision camera registry. ``demo`` generates a labeled
pattern still (not plant CCTV fiction). Real RTSP/file/device use OpenCV when
installed; otherwise honest degrade.
"""

from __future__ import annotations

import io
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from verge_vision.cameras import CameraZone, camera_registry_from_env


@dataclass
class SnapshotResult:
    ok: bool
    jpeg: bytes | None = None
    reason: str = ""
    camera_id: str = ""
    zone_id: str = ""
    demo: bool = False


_lock = threading.Lock()
_caps: dict[str, Any] = {}
_last_jpeg: dict[str, tuple[float, bytes]] = {}
_CACHE_TTL_S = 0.35


def list_cameras(env: dict[str, str] | None = None) -> list[dict[str, Any]]:
    env = env or dict(os.environ)
    reg = camera_registry_from_env(env)
    rows = []
    for cam_id, cz in sorted(reg.items()):
        rows.append({
            "cameraId": cam_id,
            "zoneId": cz.zone_id,
            "restricted": cz.restricted,
            "hasSource": bool(cz.source),
            "sourceKind": _source_kind(cz.source),
            "streamPath": f"/api/cameras/{cam_id}/mjpeg" if cz.source else None,
            "snapshotPath": f"/api/cameras/{cam_id}/snapshot" if cz.source else None,
        })
    return rows


def _source_kind(source: str | None) -> str:
    if not source:
        return "none"
    s = source.strip().lower()
    if s == "demo":
        return "demo"
    if s.startswith("rtsp://") or s.startswith("rtsps://"):
        return "rtsp"
    if s.lstrip("-").isdigit():
        return "device"
    return "file"


def get_camera(camera_id: str, env: dict[str, str] | None = None) -> CameraZone | None:
    return camera_registry_from_env(env or dict(os.environ)).get(camera_id)


def grab_snapshot(camera_id: str, env: dict[str, str] | None = None) -> SnapshotResult:
    env = env or dict(os.environ)
    cz = get_camera(camera_id, env)
    if cz is None:
        return SnapshotResult(ok=False, reason="unknown-camera", camera_id=camera_id)
    if not cz.source:
        return SnapshotResult(
            ok=False,
            reason="no-source-configured",
            camera_id=camera_id,
            zone_id=cz.zone_id,
        )
    if cz.source.strip().lower() == "demo":
        jpeg = _demo_jpeg(camera_id, cz.zone_id)
        return SnapshotResult(
            ok=True,
            jpeg=jpeg,
            camera_id=camera_id,
            zone_id=cz.zone_id,
            demo=True,
        )

    now = time.monotonic()
    with _lock:
        cached = _last_jpeg.get(camera_id)
        if cached and now - cached[0] < _CACHE_TTL_S:
            return SnapshotResult(
                ok=True,
                jpeg=cached[1],
                camera_id=camera_id,
                zone_id=cz.zone_id,
            )

    jpeg, reason = _grab_opencv(camera_id, cz.source)
    if jpeg is None:
        return SnapshotResult(
            ok=False,
            reason=reason or "grab-failed",
            camera_id=camera_id,
            zone_id=cz.zone_id,
        )
    with _lock:
        _last_jpeg[camera_id] = (time.monotonic(), jpeg)
    return SnapshotResult(
        ok=True,
        jpeg=jpeg,
        camera_id=camera_id,
        zone_id=cz.zone_id,
    )


def _demo_jpeg(camera_id: str, zone_id: str) -> bytes:
    """Labeled demo still — clearly not a live plant feed (P4)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        # Minimal JPEG header-ish fallback via opencv if PIL missing.
        return _demo_jpeg_cv2(camera_id, zone_id)

    w, h = 640, 360
    t = time.time()
    # Subtle motion so MJPEG looks alive without faking CCTV content.
    shade = int(40 + 20 * abs((t % 4) - 2))
    img = Image.new("RGB", (w, h), (shade, shade + 8, shade + 4))
    draw = ImageDraw.Draw(img)
    # Scan line
    y = int((t * 40) % h)
    draw.line([(0, y), (w, y)], fill=(90, 110, 100), width=2)
    title = f"DEMO STREAM · {camera_id}"
    sub = f"zone {zone_id} · not plant CCTV · {time.strftime('%H:%M:%S')}"
    draw.rectangle([(16, 16), (w - 16, 88)], fill=(18, 20, 23))
    draw.text((28, 28), title, fill=(240, 241, 239))
    draw.text((28, 54), sub, fill=(180, 185, 178))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


def _demo_jpeg_cv2(camera_id: str, zone_id: str) -> bytes:
    try:
        import cv2
        import numpy as np
    except ImportError:
        # Last resort: tiny valid JPEG bytes (1x1) — UI still shows broken honestly
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.7"
            b"111\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
            b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4"
            b"\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00"
            b"\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q"
            b"\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17"
            b"\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83"
            b"\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99"
            b"\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6"
            b"\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3"
            b"\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8"
            b"\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08"
            b"\x01\x01\x00\x00?\x00\xfb\xd5\x1f\xff\xd9"
        )
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (40, 48, 44)
    cv2.putText(
        frame,
        f"DEMO {camera_id}",
        (24, 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (240, 241, 239),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"zone {zone_id} — not plant CCTV",
        (24, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (180, 185, 178),
        1,
        cv2.LINE_AA,
    )
    ok, buf = cv2.imencode(".jpg", frame)
    return bytes(buf) if ok else b""


def _grab_opencv(camera_id: str, source: str) -> tuple[bytes | None, str]:
    try:
        import cv2
    except ImportError:
        return None, "opencv-not-installed"

    device: int | str = int(source) if source.lstrip("-").isdigit() else source
    with _lock:
        cap = _caps.get(camera_id)
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(device)
            _caps[camera_id] = cap
        if not cap.isOpened():
            return None, "source-open-failed"
        ok, frame = cap.read()
        if not ok or frame is None:
            # One reconnect attempt
            cap.release()
            cap = cv2.VideoCapture(device)
            _caps[camera_id] = cap
            ok, frame = cap.read()
            if not ok or frame is None:
                return None, "frame-read-failed"
        ok, buf = cv2.imencode(".jpg", frame)
        if not ok:
            return None, "jpeg-encode-failed"
        return bytes(buf), ""


def mjpeg_frames(camera_id: str, *, interval_s: float = 0.4):
    """Yield JPEG bytes for multipart MJPEG until the client disconnects."""
    while True:
        snap = grab_snapshot(camera_id)
        if snap.ok and snap.jpeg:
            yield snap.jpeg
        else:
            # Labeled still — honest about failure, keeps <img> alive
            yield _demo_jpeg(camera_id, snap.zone_id or "?")
        time.sleep(max(0.15, interval_s))
