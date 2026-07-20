"""Live camera registry + snapshot / MJPEG for the console Live Ops wall."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from .. import camera_stream

router = APIRouter(tags=["cameras"])


@router.get("/cameras")
def cameras_list() -> dict:
    cams = camera_stream.list_cameras()
    return {"cameras": cams, "count": len(cams)}


@router.get("/cameras/{camera_id}/snapshot")
def camera_snapshot(camera_id: str) -> Response:
    snap = camera_stream.grab_snapshot(camera_id)
    if not snap.ok or not snap.jpeg:
        raise HTTPException(
            404 if snap.reason == "unknown-camera" else 503,
            detail=snap.reason or "snapshot-unavailable",
        )
    headers = {
        "Cache-Control": "no-store",
        "X-Verge-Camera": snap.camera_id,
        "X-Verge-Zone": snap.zone_id or "",
        "X-Verge-Demo": "1" if snap.demo else "0",
    }
    return Response(content=snap.jpeg, media_type="image/jpeg", headers=headers)


@router.get("/cameras/{camera_id}/mjpeg")
def camera_mjpeg(camera_id: str, request: Request) -> StreamingResponse:
    cz = camera_stream.get_camera(camera_id)
    if cz is None:
        raise HTTPException(404, "unknown-camera")
    if not cz.source:
        raise HTTPException(503, "no-source-configured")

    boundary = b"frame"

    def gen():
        for jpeg in camera_stream.mjpeg_frames(camera_id):
            if getattr(request, "is_disconnected", None):
                # Best-effort; Starlette StreamingResponse cancels on client close.
                pass
            yield (
                b"--" + boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                + jpeg + b"\r\n"
            )

    return StreamingResponse(
        gen(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary.decode()}",
        headers={"Cache-Control": "no-store", "X-Verge-Camera": camera_id},
    )
