"""`verge vision watch` — frame sampler/forwarder (spec §5).

Real cv2/httpx calls are mocked here for a fast, offline test; the actual
pipeline (real video -> real HTTP -> real ultralytics inference) was
manually verified end-to-end during development against a live API — see
docs/progress.md.
"""

from __future__ import annotations

from verge_cli.cli import main
from verge_cli.vision_watch import WatchResult, watch


class _FakeCap:
    def __init__(self, frames: int) -> None:
        self._remaining = frames
        self.released = False

    def isOpened(self) -> bool:  # noqa: N802 - matches cv2's API
        return True

    def read(self):
        if self._remaining <= 0:
            return False, None
        self._remaining -= 1
        return True, object()

    def release(self) -> None:
        self.released = True


class _FakeResponse:
    def __init__(self, body: dict) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._body


class _FailingResponse:
    def raise_for_status(self) -> None:
        raise RuntimeError("boom")


class _FakeClient:
    posts: list[tuple] = []
    response_body: dict = {"degraded": False, "detections": []}
    fail_after: int | None = None

    def __init__(self, timeout: float = 30.0) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        pass

    def post(self, url, *, data, files):
        _FakeClient.posts.append((url, data, files))
        if _FakeClient.fail_after is not None and len(_FakeClient.posts) > _FakeClient.fail_after:
            return _FailingResponse()
        return _FakeResponse(_FakeClient.response_body)


def _patch_cv_and_http(monkeypatch, *, frames: int, response_body=None, fail_after=None):
    import cv2
    import httpx

    _FakeClient.posts = []
    _FakeClient.response_body = response_body or {"degraded": False, "detections": []}
    _FakeClient.fail_after = fail_after

    monkeypatch.setattr(cv2, "VideoCapture", lambda source: _FakeCap(frames))
    monkeypatch.setattr(cv2, "imencode", lambda ext, frame: (True, b"fake-jpeg"))
    monkeypatch.setattr(httpx, "Client", _FakeClient)


def test_watch_samples_every_frame_until_source_exhausted(monkeypatch):
    _patch_cv_and_http(monkeypatch, frames=3)
    result = watch(source="clip.mp4", camera_id="CAM-B04", post="http://localhost:8000",
                    interval_s=0)
    assert result == WatchResult(frames_sent=3, frames_failed=0)
    assert len(_FakeClient.posts) == 3
    url, data, files = _FakeClient.posts[0]
    assert url == "http://localhost:8000/api/vision/detect-frame"
    assert data == {"cameraId": "CAM-B04"}
    assert files["file"][2] == "image/jpeg"


def test_watch_respects_max_frames(monkeypatch):
    _patch_cv_and_http(monkeypatch, frames=10)
    result = watch(source="clip.mp4", camera_id="CAM-B04", post="http://localhost:8000",
                    interval_s=0, max_frames=2)
    assert result == WatchResult(frames_sent=2, frames_failed=0)


def test_watch_counts_failures_without_stopping(monkeypatch):
    _patch_cv_and_http(monkeypatch, frames=3, fail_after=1)
    result = watch(source="clip.mp4", camera_id="CAM-B04", post="http://localhost:8000",
                    interval_s=0)
    assert result == WatchResult(frames_sent=1, frames_failed=2)


def test_watch_prints_real_detections(monkeypatch, capsys):
    body = {"degraded": False, "detections": [
        {"label": "person", "confidence": 0.84, "zoneId": "B-05", "inferredBy": None},
        {"label": "ppe-missing", "confidence": 0.84, "zoneId": "B-05", "inferredBy": "vlm"},
    ]}
    _patch_cv_and_http(monkeypatch, frames=1, response_body=body)
    watch(source="clip.mp4", camera_id="CAM-B05", post="http://localhost:8000", interval_s=0)
    out = capsys.readouterr().out
    assert "person conf=0.84 zone=B-05" in out
    assert "ppe-missing conf=0.84 zone=B-05 inferredBy=vlm" in out


def test_watch_reports_degraded_backend(monkeypatch, capsys):
    _patch_cv_and_http(monkeypatch, frames=1, response_body={
        "degraded": True, "reason": "vision disabled", "detections": [],
    })
    watch(source="clip.mp4", camera_id="CAM-B04", post="http://localhost:8000", interval_s=0)
    assert "degraded: vision disabled" in capsys.readouterr().out


def test_cli_vision_watch_dispatches_with_parsed_args(monkeypatch):
    captured = {}

    def fake_watch(**kwargs):
        captured.update(kwargs)
        return WatchResult(frames_sent=1, frames_failed=0)

    import verge_cli.vision_watch as vw
    monkeypatch.setattr(vw, "watch", fake_watch)

    code = main([
        "vision", "watch",
        "--source", "0",
        "--camera", "CAM-B04",
        "--post", "http://localhost:8000",
        "--interval-s", "1.5",
        "--max-frames", "5",
    ])
    assert code == 0
    assert captured == {
        "source": "0",
        "camera_id": "CAM-B04",
        "post": "http://localhost:8000",
        "interval_s": 1.5,
        "max_frames": 5,
    }
