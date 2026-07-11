"""Real incident replay data for the console's Replay view (spec §10).

Serves the same replay fixtures the eval harness scores against — no
hardcoded frontend scenarios, no re-derived numbers. Each incident's events
are mapped into the console's timeline shape, plus Verge's own computed
alert (timestamp/band/lead) so the operator sees exactly what the eval
harness proves: an alert well before the real breach, while the baselines
stayed silent (see ``eval/out/report.md``).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["replays"])

try:
    from eval.runtime import REPLAYS, load_replay, run_verge_stream
except ImportError:  # pragma: no cover - defensive; see _fallback_load_replay
    REPLAYS = None
    load_replay = None
    run_verge_stream = None

_REPO_ROOT = Path(__file__).resolve().parents[4]
_REPLAYS_DIR = _REPO_ROOT / "eval" / "replays"


def _replay_ids() -> list[str]:
    base = REPLAYS if REPLAYS is not None else _REPLAYS_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "ground-truth.json").exists())


def _fallback_load_replay(incident: str) -> tuple[dict, list[dict]]:
    """Minimal reader used only if ``eval`` isn't importable at runtime.

    Mirrors ``eval.runtime.load_replay`` exactly (ground-truth + sorted
    events) but carries none of the scoring logic — if this path is taken,
    ``vergeAlertTs``/``band``/``leadMin`` are omitted rather than
    approximated.
    """
    import json

    d = _REPLAYS_DIR / incident
    gt = json.loads((d / "ground-truth.json").read_text(encoding="utf-8"))
    events: list[dict] = []
    for line in (d / "events.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    events.sort(key=lambda e: e["ts"])
    return gt, events


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


_EVENT_TITLES = {
    "reading": lambda e: f"{e['kind']} reading",
    "permit": lambda e: f"{e['kind']} permit opened",
    "shift": lambda e: e.get("event", "shift event"),
}


def _event_sensor(e: dict) -> str:
    return e.get("sensorId") or e.get("permitId") or e.get("zoneId", "")


def _event_value(e: dict) -> str:
    if e["type"] == "reading":
        return f"{e['value']} {e.get('unit', '')}".strip()
    if e["type"] == "permit":
        return e.get("zoneId", "")
    return ""


def _band_value(band) -> str | None:
    """Normalize a LeadTimeBand — enum instance or already-coerced str — to str."""
    if band is None:
        return None
    return band.value if hasattr(band, "value") else str(band)


def _to_timeline(gt: dict, events: list[dict], *, verge_ts, band, lead_min) -> dict:
    band_value = _band_value(band)
    breach = _dt(gt["breachTs"])
    ts_list = [_dt(e["ts"]) for e in events] + [breach]
    start = min(ts_list)
    end = max(ts_list)
    duration = max((end - start).total_seconds(), 1.0)

    mapped = [
        {
            "time": round((_dt(e["ts"]) - start).total_seconds(), 1),
            "type": e["type"],
            "title": _EVENT_TITLES[e["type"]](e),
            "sensor": _event_sensor(e),
            "value": _event_value(e),
        }
        for e in events
    ]
    mapped.append(
        {
            "time": round((breach - start).total_seconds(), 1),
            "type": "breach",
            "title": "Threshold breach",
            "sensor": gt.get("zoneId", ""),
            "value": gt.get("thresholdSensor", ""),
        }
    )
    if verge_ts is not None:
        mapped.append(
            {
                "time": round((verge_ts - start).total_seconds(), 1),
                "type": "verge-alert",
                "title": f"Verge alert ({band_value or 'UNKNOWN'})",
                "sensor": gt.get("zoneId", ""),
                "value": f"{lead_min} min before breach" if lead_min is not None else "",
            }
        )
    mapped.sort(key=lambda m: m["time"])

    return {
        "id": gt["incidentId"],
        "name": gt.get("title", gt["incidentId"]),
        "description": gt.get("source", ""),
        "zoneId": gt.get("zoneId", ""),
        "duration": round(duration, 1),
        "breachTs": gt["breachTs"],
        "vergeAlertTs": verge_ts.isoformat() if verge_ts else None,
        "band": band_value,
        "leadMin": lead_min,
        "events": mapped,
    }


@router.get("/replays")
def list_replays() -> list[dict]:
    """Summary of every real incident available to replay."""
    out = []
    for incident in _replay_ids():
        gt, _ = (load_replay or _fallback_load_replay)(incident)
        out.append(
            {
                "incidentId": gt["incidentId"],
                "title": gt.get("title", incident),
                "zoneId": gt.get("zoneId", ""),
                "breachTs": gt["breachTs"],
            }
        )
    return out


@router.get("/replays/{incident_id}")
def get_replay(incident_id: str) -> dict:
    """One incident's full timeline, plus Verge's real computed alert."""
    if incident_id not in _replay_ids():
        raise HTTPException(404, "replay not found")
    loader = load_replay or _fallback_load_replay
    gt, events = loader(incident_id)

    verge_ts, band, lead_min = None, None, None
    if run_verge_stream is not None:
        verge_ts, band = run_verge_stream(gt, events)
        if verge_ts is not None:
            breach = _dt(gt["breachTs"])
            lead_min = round((breach - verge_ts).total_seconds() / 60.0, 1)

    return _to_timeline(gt, events, verge_ts=verge_ts, band=band, lead_min=lead_min)
