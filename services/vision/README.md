# verge-vision

PPE / person / zone-intrusion **CV detector plane** (spec §5 Pillar — vision).

Vision is a *detector*, not a narrator. It emits classic-CV detections that
become one leg — a `ContributingSignal(kind="frame")` — of a compound finding.
It is deterministic ML (Ultralytics / RT-DETR on the plant GPU box in
production), **not** an LLM, so it is allowed in the safety plane (P1). The
narrative layer never enters here.

## Degraded by default (P4)

The production backend needs a GPU + model, which the dev/CI/hackathon box does
not have. So the plane is **degraded-by-default and honest about it**: with no
model configured, `detect()` returns `degraded=True` and an empty detection
list. It never fabricates a detection.

## Backends

| Backend | When | Behaviour |
|---------|------|-----------|
| `stub` (default) | no model | `degraded=True`, no detections |
| `annotations` | dev / CI / demo | deterministic replay of pre-labeled frames — real detections, no GPU |
| `ultralytics` | plant GPU box | lazily imported; degrades to stub if the stack/GPU is absent |

## Env

```bash
VERGE_VISION_ENABLED=true
VERGE_VISION_BACKEND=annotations                # stub | annotations | ultralytics
VERGE_VISION_ANNOTATIONS=/path/to/frames.json   # for the annotations backend
VERGE_VISION_MODEL=/models/ppe.pt               # for the ultralytics backend
```

## Use

```python
from verge_vision import provider_from_env, to_contributing_signals

detector = provider_from_env()          # env-driven; degraded stub by default
result = detector.detect("CAM-B04")     # VisionResult(detections=[...], degraded=...)
signals = to_contributing_signals(result)   # -> [ContributingSignal(kind="frame"), ...]
```

## API

```bash
curl -X POST http://localhost:8000/api/vision/detect \
  -H 'content-type: application/json' \
  -d '{"cameraId": "CAM-B04"}'
# -> { "detections": [...], "degraded": false, "contributingSignals": [...] }
```

## Annotation format

`{ camera_id: [ { frameId, label, zoneId, confidence, ts, detail, bbox } ] }`
where `label ∈ {person, ppe-missing, zone-intrusion}`. See
[`verge_vision/samples/vizag-ppe.json`](verge_vision/samples/vizag-ppe.json).
