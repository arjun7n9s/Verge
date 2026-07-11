"""`verge vision watch` — sample a video file or webcam and POST real frames
to the vision plane's real-frame endpoint (spec §5).

This is the tool for routing real footage instead of demo-shaped annotation
replay: point it at your own clip (or a webcam device index) and the
server-side detector (``UltralyticsDetector`` when configured) runs real
CPU inference on each sampled frame — the same code path
``POST /api/vision/detect-frame`` uses for any uploaded frame. Inference
stays server-side (one place, one source of truth); this tool is only a
frame sampler + forwarder, the same shape as ``verge sim ... --post``.

    verge vision watch --source clip.mp4 --camera CAM-B04 --post http://localhost:8000
    verge vision watch --source 0 --camera CAM-B04 --interval-s 1 --post http://localhost:8000
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class WatchResult:
    frames_sent: int
    frames_failed: int


def _open_source(source: str):
    import cv2

    device: int | str = int(source) if source.lstrip("-").isdigit() else source
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise SystemExit(f"verge vision watch: could not open video source {source!r}")
    return cap


def _frame_to_jpeg(frame) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("frame encode failed")
    return bytes(buf)


def _report(camera_id: str, body: dict) -> None:
    if body.get("degraded"):
        print(f"[{camera_id}] degraded: {body.get('reason')}")
        return
    detections = body.get("detections") or []
    if not detections:
        print(f"[{camera_id}] no detections")
        return
    for d in detections:
        inferred = f" inferredBy={d['inferredBy']}" if d.get("inferredBy") else ""
        print(
            f"[{camera_id}] {d['label']} conf={d['confidence']:.2f} "
            f"zone={d['zoneId'] or '-'}{inferred}"
        )


def watch(
    *,
    source: str,
    camera_id: str,
    post: str,
    interval_s: float = 2.0,
    max_frames: int | None = None,
) -> WatchResult:
    import httpx

    cap = _open_source(source)
    sent, failed = 0, 0
    url = f"{post.rstrip('/')}/api/vision/detect-frame"
    try:
        with httpx.Client(timeout=30.0) as client:
            while max_frames is None or sent + failed < max_frames:
                ok, frame = cap.read()
                if not ok:
                    print(f"[{camera_id}] source exhausted", file=sys.stderr)
                    break
                try:
                    jpeg = _frame_to_jpeg(frame)
                    resp = client.post(
                        url,
                        data={"cameraId": camera_id},
                        files={"file": ("frame.jpg", jpeg, "image/jpeg")},
                    )
                    resp.raise_for_status()
                    _report(camera_id, resp.json())
                    sent += 1
                except Exception as exc:  # noqa: BLE001 - keep watching, never crash the tour
                    print(f"[{camera_id}] detect-frame failed: {exc}", file=sys.stderr)
                    failed += 1
                if max_frames is None or sent + failed < max_frames:
                    time.sleep(interval_s)
    finally:
        cap.release()
    return WatchResult(frames_sent=sent, frames_failed=failed)
