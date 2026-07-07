"""Vision detector plane: degradation posture + annotation replay (spec §5)."""

from __future__ import annotations

from verge_vision import (
    PPE_MISSING,
    SAMPLE_ANNOTATIONS,
    AnnotationDetector,
    StubDetector,
    load_annotations,
    provider_from_env,
    to_contributing_signals,
)


def test_stub_is_degraded_and_never_fabricates():
    result = StubDetector().detect("CAM-B04")
    assert result.degraded is True
    assert result.detections == []
    assert result.reason


def test_env_defaults_to_degraded_stub():
    det = provider_from_env({})
    assert isinstance(det, StubDetector)
    assert det.detect("CAM-B04").degraded is True


def test_enabled_but_missing_annotations_degrades_not_raises():
    det = provider_from_env({
        "VERGE_VISION_ENABLED": "true",
        "VERGE_VISION_BACKEND": "annotations",
        "VERGE_VISION_ANNOTATIONS": "/no/such/file.json",
    })
    assert det.detect("CAM-B04").degraded is True


def test_unknown_backend_degrades():
    det = provider_from_env({"VERGE_VISION_ENABLED": "1", "VERGE_VISION_BACKEND": "acme"})
    assert det.detect("CAM-B04").degraded is True


def test_annotation_replay_returns_real_detections():
    det = AnnotationDetector(load_annotations(SAMPLE_ANNOTATIONS))
    result = det.detect("CAM-B04")
    assert not result.degraded
    labels = {d.label for d in result.detections}
    assert PPE_MISSING in labels
    ppe = next(d for d in result.detections if d.label == PPE_MISSING)
    assert ppe.zone_id == "B-04"
    assert "hard-hat" in ppe.summary()


def test_frame_filter_scopes_detections():
    det = AnnotationDetector(load_annotations(SAMPLE_ANNOTATIONS))
    only = det.detect("CAM-B04", frame_id="f-0001")
    assert all(d.camera_id == "CAM-B04" for d in only.detections)
    none = det.detect("CAM-B04", frame_id="f-9999")
    assert none.detections == []


def test_detections_become_frame_contributing_signals():
    det = AnnotationDetector(load_annotations(SAMPLE_ANNOTATIONS))
    signals = to_contributing_signals(det.detect("CAM-B04"))
    assert signals
    assert all(s.kind == "frame" for s in signals)
    assert any("B-04" in s.summary for s in signals)


def test_malformed_annotations_are_skipped_not_raised():
    ann = {"CAM-X": [
        {"label": "ppe-missing", "zoneId": "B-04", "confidence": "high"},  # bad confidence -> skip
        {"label": "person", "zoneId": "B-04", "confidence": 0.9, "ts": "nope"},  # bad ts -> skip
        {"label": "person", "zoneId": "B-04", "confidence": 0.8, "bbox": [1, 2, 3]},  # repaired
        {"label": "person", "zoneId": "B-04", "confidence": 0.95},  # valid
    ]}
    result = AnnotationDetector(ann).detect("CAM-X")
    assert not result.degraded
    # Unrepairable rows (bad confidence, bad ts) are skipped; the wrong-length
    # bbox is repaired to None and its detection kept.
    assert len(result.detections) == 2
    assert "2 malformed" in result.reason


def test_corrupt_annotation_file_degrades_to_stub(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    det = provider_from_env({
        "VERGE_VISION_ENABLED": "true",
        "VERGE_VISION_BACKEND": "annotations",
        "VERGE_VISION_ANNOTATIONS": str(bad),
    })
    assert det.detect("CAM-X").degraded is True  # did not crash wiring


def test_bad_bbox_dropped_but_detection_kept_when_repairable():
    ann = {"CAM-Y": [{"label": "person", "zoneId": "B-04", "confidence": 0.9,
                      "bbox": [0.1, 0.2, 0.3]}]}  # wrong length -> bbox None, det kept
    result = AnnotationDetector(ann).detect("CAM-Y")
    assert len(result.detections) == 1
    assert result.detections[0].bbox is None


def test_provider_from_env_annotation_backend_end_to_end():
    det = provider_from_env({
        "VERGE_VISION_ENABLED": "true",
        "VERGE_VISION_BACKEND": "annotations",
        "VERGE_VISION_ANNOTATIONS": str(SAMPLE_ANNOTATIONS),
    })
    result = det.detect("CAM-B05")
    assert result.backend == "annotations"
    assert any(d.label == "zone-intrusion" for d in result.detections)
