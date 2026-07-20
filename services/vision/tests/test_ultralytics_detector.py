"""Real CV backend: person detection, zone-intrusion, VLM-inferred PPE (spec §5).

Model/LLM calls are mocked so CI stays fast and offline; the real pipeline
(ultralytics CPU inference + a real photo with people) was manually verified
during development — see docs/progress.md.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image
from verge_llm import Completion
from verge_vision.cameras import CameraZone, load_camera_registry
from verge_vision.detect import (
    PERSON,
    PPE_MISSING,
    ZONE_INTRUSION,
    UltralyticsDetector,
)
from verge_vision.detect import (
    provider_from_env as detect_provider_from_env,
)


def _jpeg_bytes(size=(64, 64), color=(120, 120, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG")
    return buf.getvalue()


class _FakeBox:
    def __init__(self, cls_id: int, conf: float, xyxy: list[float]) -> None:
        self.cls = [cls_id]
        self.conf = [conf]
        self.xyxy = [_FakeTensor(xyxy)]


class _FakeTensor:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


class _FakeResult:
    def __init__(self, boxes: list[_FakeBox]) -> None:
        self.boxes = boxes


class _FakeModel:
    """Stands in for ``ultralytics.YOLO`` — same attribute shape, no torch."""

    names = {0: "person", 1: "bicycle"}

    def __init__(self, boxes: list[_FakeBox]) -> None:
        self._boxes = boxes
        self.predict_calls = 0

    def predict(self, image, verbose=False):
        self.predict_calls += 1
        return [_FakeResult(self._boxes)]


class _RaisingModel:
    def predict(self, image, verbose=False):
        raise RuntimeError("model exploded")


class _FakeLLM:
    def __init__(self, answer: str = "missing", degraded: bool = False) -> None:
        self.name = "fake"
        self.answer = answer
        self.degraded = degraded
        self.calls: list = []

    def complete(self, messages, *, model=None, max_tokens=512, temperature=0.2):
        self.calls.append((messages, model))
        return Completion(text=self.answer, model=model or "fake", degraded=self.degraded)

    def healthy(self) -> bool:
        return True


PERSON_BOX = _FakeBox(cls_id=0, conf=0.9, xyxy=[10.0, 10.0, 30.0, 50.0])
LOW_CONF_PERSON_BOX = _FakeBox(cls_id=0, conf=0.1, xyxy=[10.0, 10.0, 30.0, 50.0])
NON_PERSON_BOX = _FakeBox(cls_id=1, conf=0.9, xyxy=[0.0, 0.0, 5.0, 5.0])


def test_no_image_degrades_with_clear_reason():
    det = UltralyticsDetector(model=_FakeModel([]))
    result = det.detect("CAM-B04")
    assert result.degraded is True
    assert "image frame" in result.reason


def test_corrupt_image_degrades_not_raises():
    det = UltralyticsDetector(model=_FakeModel([]))
    result = det.detect("CAM-B04", image=b"not a jpeg")
    assert result.degraded is True
    assert "invalid image frame" in result.reason


def test_model_failure_degrades_not_raises():
    det = UltralyticsDetector(model=_RaisingModel())
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert result.degraded is True
    assert "ultralytics unavailable" in result.reason


def test_real_person_detection_with_zone_from_camera_registry():
    det = UltralyticsDetector(
        model=_FakeModel([PERSON_BOX]),
        cameras={"CAM-B04": CameraZone(zone_id="B-04", restricted=False)},
    )
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert not result.degraded
    assert [d.label for d in result.detections] == [PERSON]
    person = result.detections[0]
    assert person.zone_id == "B-04"
    assert person.confidence == pytest.approx(0.9)
    assert person.bbox is not None
    assert person.inferred_by is None  # deterministic, not VLM-inferred


def test_restricted_zone_camera_adds_zone_intrusion():
    det = UltralyticsDetector(
        model=_FakeModel([PERSON_BOX]),
        cameras={"CAM-B05": CameraZone(zone_id="B-05", restricted=True)},
    )
    result = det.detect("CAM-B05", image=_jpeg_bytes())
    labels = [d.label for d in result.detections]
    assert labels == [PERSON, ZONE_INTRUSION]
    assert result.detections[1].zone_id == "B-05"


def test_unrestricted_camera_never_emits_zone_intrusion():
    det = UltralyticsDetector(
        model=_FakeModel([PERSON_BOX]),
        cameras={"CAM-B04": CameraZone(zone_id="B-04", restricted=False)},
    )
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert ZONE_INTRUSION not in [d.label for d in result.detections]


def test_low_confidence_and_non_person_boxes_are_filtered():
    det = UltralyticsDetector(model=_FakeModel([LOW_CONF_PERSON_BOX, NON_PERSON_BOX]))
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert result.detections == []


def test_unknown_camera_has_no_zone_but_still_detects():
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]))
    result = det.detect("CAM-UNREGISTERED", image=_jpeg_bytes())
    assert result.detections[0].zone_id == ""


# -- PPE via VLM: real signal on a clear "missing", never a fabricated guess --


def test_ppe_missing_emitted_on_clear_vlm_answer():
    llm = _FakeLLM(answer="missing")
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]), llm=llm, vision_model="vlm-x")
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    ppe = [d for d in result.detections if d.label == PPE_MISSING]
    assert len(ppe) == 1
    assert ppe[0].inferred_by == "vlm"
    assert "verify before acting" in ppe[0].detail
    assert len(llm.calls) == 1
    # The VLM sees text + a base64 image part, never raw safety-critical logic.
    user_message = llm.calls[0][0][1]
    assert [p["type"] for p in user_message.content] == ["text", "image_url"]
    assert llm.calls[0][1] == "vlm-x"


@pytest.mark.parametrize("answer", ["compliant", "uncertain", "I'm not sure honestly"])
def test_ppe_missing_never_emitted_on_anything_but_a_clear_answer(answer):
    llm = _FakeLLM(answer=answer)
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]), llm=llm)
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert PPE_MISSING not in [d.label for d in result.detections]


def test_ppe_missing_never_emitted_when_llm_degraded():
    llm = _FakeLLM(answer="missing", degraded=True)
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]), llm=llm)
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert PPE_MISSING not in [d.label for d in result.detections]


def test_no_llm_configured_means_no_ppe_signal_and_no_call_attempted():
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]), llm=None)
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    assert PPE_MISSING not in [d.label for d in result.detections]


def test_detection_to_dict_carries_inferred_by():
    llm = _FakeLLM(answer="missing")
    det = UltralyticsDetector(model=_FakeModel([PERSON_BOX]), llm=llm)
    result = det.detect("CAM-B04", image=_jpeg_bytes())
    ppe_dict = next(d.to_dict() for d in result.detections if d.label == PPE_MISSING)
    assert ppe_dict["inferredBy"] == "vlm"
    person_dict = next(d.to_dict() for d in result.detections if d.label == PERSON)
    assert person_dict["inferredBy"] is None


# -- provider_from_env wiring --


def test_provider_from_env_builds_real_detector_when_enabled():
    det = detect_provider_from_env({
        "VERGE_VISION_ENABLED": "true",
        "VERGE_VISION_BACKEND": "ultralytics",
    })
    assert isinstance(det, UltralyticsDetector)
    # Falls back to the bundled demo camera registry.
    assert det._cameras.get("CAM-B05") == CameraZone(
        zone_id="B-05", restricted=True, source="demo"
    )


def test_provider_from_env_ultralytics_disabled_by_default():
    det = detect_provider_from_env({"VERGE_VISION_BACKEND": "ultralytics"})
    assert det.backend == "stub"


# -- camera registry --


def test_load_camera_registry_bundled_demo():
    from verge_vision.cameras import DEMO_CAMERAS

    reg = load_camera_registry(DEMO_CAMERAS)
    assert reg["CAM-B04"] == CameraZone(zone_id="B-04", restricted=False, source="demo")
    assert reg["CAM-B05"] == CameraZone(zone_id="B-05", restricted=True, source="demo")


def test_load_camera_registry_drops_malformed_entries_not_raises():
    import json

    from verge_vision.cameras import load_camera_registry as load

    def _write(tmp_path, data):
        p = tmp_path / "cams.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def check(tmp_path):
        path = _write(tmp_path, {
            "CAM-OK": {"zoneId": "Z-1", "restricted": True},
            "CAM-BAD": {"restricted": True},  # missing zoneId -- dropped
            "CAM-WRONG-SHAPE": "not-a-dict",  # dropped
        })
        reg = load(path)
        assert set(reg) == {"CAM-OK"}

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        check(Path(d))


def test_camera_registry_from_env_falls_back_to_demo_on_bad_path():
    from verge_vision.cameras import camera_registry_from_env

    reg = camera_registry_from_env({"VERGE_VISION_CAMERAS": "/no/such/file.json"})
    assert "CAM-B04" in reg  # bundled demo, not an empty/raised result
