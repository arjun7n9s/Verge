"""Long-running RTSP / file / webcam sampler → detect-frame API (Phase 2B).

Uses OpenCV ``VideoCapture`` (RTSP URL, file path, or camera index). Posts
JPEG snapshots to the Verge API so fusion gets lineage-backed detections.
Degrades honestly when OpenCV or the API is unavailable — never fabricates.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any


def _encode_jpeg(frame: Any) -> bytes | None:
    try:
        import cv2
    except ImportError:
        return None
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None
    return bytes(buf)


def sample_once(
    source: str | int,
    *,
    api_base: str,
    camera_id: str,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Grab one frame from ``source`` and POST to ``/api/vision/detect-frame``."""
    try:
        import cv2
    except ImportError:
        return {"ok": False, "reason": "opencv not installed"}

    import httpx

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        return {"ok": False, "reason": f"cannot open source {source!r}"}
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            return {"ok": False, "reason": "frame read failed"}
        jpeg = _encode_jpeg(frame)
        if not jpeg:
            return {"ok": False, "reason": "jpeg encode failed"}
    finally:
        cap.release()

    url = api_base.rstrip("/") + "/api/vision/detect-frame"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.post(
                url,
                data={"cameraId": camera_id},
                files={"file": ("frame.jpg", jpeg, "image/jpeg")},
            )
            resp.raise_for_status()
            body = resp.json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"api post failed: {type(exc).__name__}"}
    return {
        "ok": True,
        "cameraId": camera_id,
        "degraded": bool(body.get("degraded")),
        "detections": len(body.get("detections") or []),
        "fusionCount": body.get("fusionCount", 0),
        "frameUri": body.get("frameUri"),
    }


def run_loop(
    source: str | int,
    *,
    api_base: str,
    camera_id: str,
    interval_s: float = 2.0,
    max_frames: int | None = None,
) -> int:
    """Poll ``source`` until interrupted. Returns number of successful posts."""
    posted = 0
    n = 0
    while max_frames is None or n < max_frames:
        n += 1
        result = sample_once(source, api_base=api_base, camera_id=camera_id)
        if result.get("ok"):
            posted += 1
            print(
                f"[rtsp_worker] ok camera={camera_id} "
                f"detections={result.get('detections')} "
                f"frameUri={result.get('frameUri') or '-'}",
                flush=True,
            )
        else:
            print(f"[rtsp_worker] degrade: {result.get('reason')}", flush=True)
        time.sleep(max(0.2, interval_s))
    return posted


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Verge RTSP/file vision worker")
    p.add_argument(
        "--source",
        default=os.environ.get("VERGE_VISION_RTSP_URL", "0"),
        help="RTSP URL, file path, or webcam index (default 0)",
    )
    p.add_argument(
        "--camera-id",
        default=os.environ.get("VERGE_VISION_CAMERA_ID", "cam-rtsp-1"),
    )
    p.add_argument(
        "--api",
        default=os.environ.get("VERGE_API_BASE", "http://127.0.0.1:8000"),
    )
    p.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("VERGE_VISION_INTERVAL_S", "2")),
    )
    p.add_argument("--max-frames", type=int, default=None)
    args = p.parse_args(argv)
    source: str | int = args.source
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    try:
        run_loop(
            source,
            api_base=args.api,
            camera_id=args.camera_id,
            interval_s=args.interval,
            max_frames=args.max_frames,
        )
    except KeyboardInterrupt:
        print("[rtsp_worker] stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
