"""Continuous multi-source WatchLoop — the product heartbeat.

When running, each tick samples cameras → detect, optional radio chunks →
transcribe, optional sensor schedule → readings, then live fusion → findings,
and Cognee memory for new evidence. No frontend fiction: the console only
renders APIs/SSE like a real shift.

Runs on a dedicated thread so ticks continue outside request handlers.
"""

from __future__ import annotations

import glob
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from verge_schema.core import Permit
from verge_schema.findings import RiskFinding

from . import camera_stream
from .audio_clip_cache import store_clip
from .demo_scenario import ScenarioPack, load_scenario
from .hooks import (
    maybe_ingest_open_finding,
    maybe_ingest_vision_watch,
    maybe_ingest_voice_ops,
)
from .routes.fusion import run_live_fusion
from .routes.vision import run_detect
from .voice_events import record_voice_event

log = logging.getLogger("verge.watch")

_TRUE = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass
class WatchStatus:
    running: bool = False
    mode: str = "watch"  # watch | demo
    scenario_id: str | None = None
    scenario_label: str | None = None
    coach: str | None = None
    started_at: str | None = None
    interval_s: float = 3.0
    ticks: int = 0
    last_tick_at: str | None = None
    last_error: str | None = None
    legs: dict[str, bool] = field(
        default_factory=lambda: {
            "vision": True,
            "voice": True,
            "sensors": True,
            "fuse": True,
            "cognee": True,
            "workers": True,
        }
    )
    counts: dict[str, int] = field(
        default_factory=lambda: {
            "visionFrames": 0,
            "visionDetections": 0,
            "voiceEvents": 0,
            "sensorReads": 0,
            "workerFixes": 0,
            "findingsPersisted": 0,
            "cogneeIngests": 0,
        }
    )
    last: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "scenarioId": self.scenario_id,
            "scenarioLabel": self.scenario_label,
            "coach": self.coach,
            "startedAt": self.started_at,
            "intervalS": self.interval_s,
            "ticks": self.ticks,
            "lastTickAt": self.last_tick_at,
            "lastError": self.last_error,
            "legs": dict(self.legs),
            "counts": dict(self.counts),
            "last": dict(self.last),
        }


class WatchController:
    """Process-wide continuous watch; start/stop from API or lifespan env."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.status = WatchStatus()
        self._radio_paths: list[Path] = []
        self._radio_idx = 0
        self._seen_finding_keys: set[str] = set()
        self._app: Any = None
        self._voice_auto_fuse_prev: str | None = None
        self._pack: ScenarioPack | None = None

    def bind_app(self, app) -> None:
        self._app = app

    def configure_from_env(self) -> None:
        self.status.interval_s = max(1.0, _env_float("VERGE_WATCH_INTERVAL_S", 3.0))
        self.status.legs = {
            "vision": _env_bool("VERGE_WATCH_VISION", True),
            "voice": _env_bool("VERGE_WATCH_VOICE", True),
            "sensors": _env_bool("VERGE_WATCH_SENSORS", True),
            "fuse": _env_bool("VERGE_WATCH_FUSE", True),
            "cognee": _env_bool("VERGE_WATCH_COGNEE", True),
            "workers": True,
        }

    def _load_radio_paths(self) -> list[Path]:
        single = (os.environ.get("VERGE_WATCH_RADIO_PATH") or "").strip()
        pattern = (os.environ.get("VERGE_WATCH_RADIO_GLOB") or "").strip()
        directory = (os.environ.get("VERGE_WATCH_RADIO_DIR") or "").strip()
        paths: list[Path] = []
        if single:
            p = Path(single)
            if p.is_file():
                paths.append(p)
        if pattern:
            paths.extend(Path(p) for p in sorted(glob.glob(pattern)) if Path(p).is_file())
        if directory:
            root = Path(directory)
            if root.is_dir():
                for ext in ("*.wav", "*.mp3", "*.ogg", "*.webm", "*.m4a"):
                    paths.extend(sorted(root.glob(ext)))
        seen: set[str] = set()
        out: list[Path] = []
        for p in paths:
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                out.append(p)
        return out

    def start(
        self,
        *,
        interval_s: float | None = None,
        legs: dict[str, bool] | None = None,
        scenario_id: str | None = None,
    ) -> dict:
        with self._lock:
            if self.status.running and self._thread and self._thread.is_alive():
                return self.status.to_dict()
            self.configure_from_env()
            pack: ScenarioPack | None = None
            if scenario_id:
                pack = load_scenario(scenario_id)
                pack.reset_cues()
                self._pack = pack
                self.status.mode = "demo"
                self.status.scenario_id = pack.id
                self.status.scenario_label = pack.label
                self.status.coach = pack.coach or None
                self.status.interval_s = max(1.0, pack.interval_s)
            else:
                self._pack = None
                self.status.mode = "watch"
                self.status.scenario_id = None
                self.status.scenario_label = None
                self.status.coach = None
            if interval_s is not None:
                self.status.interval_s = max(1.0, float(interval_s))
            if legs:
                for k, v in legs.items():
                    if k in self.status.legs:
                        self.status.legs[k] = bool(v)
            if pack:
                # Prefer pack radio timeline; env glob is watch-only fallback.
                self._radio_paths = []
            else:
                self._radio_paths = self._load_radio_paths()
            self._radio_idx = 0
            self._seen_finding_keys = self._existing_finding_keys()
            self._stop.clear()
            self.status.running = True
            self.status.started_at = datetime.now(UTC).isoformat()
            self.status.last_error = None
            self.status.ticks = 0
            for k in self.status.counts:
                self.status.counts[k] = 0
            self._voice_auto_fuse_prev = os.environ.get("VERGE_VOICE_AUTO_FUSE")
            os.environ["VERGE_VOICE_AUTO_FUSE"] = "false"
            if pack:
                self._seed_demo_permit(pack)
            self._thread = threading.Thread(
                target=self._run,
                name="verge-watch-loop",
                daemon=True,
            )
            self._thread.start()
            return self.status.to_dict()

    def start_demo(
        self,
        *,
        scenario_id: str = "compound-drill",
        interval_s: float | None = None,
        legs: dict[str, bool] | None = None,
    ) -> dict:
        return self.start(
            interval_s=interval_s, legs=legs, scenario_id=scenario_id
        )

    def stop(self) -> dict:
        with self._lock:
            self._stop.set()
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=self.status.interval_s + 5.0)
        with self._lock:
            self.status.running = False
            self._thread = None
            self._pack = None
            self.status.mode = "watch"
            self.status.scenario_id = None
            self.status.scenario_label = None
            self.status.coach = None
            if self._voice_auto_fuse_prev is None:
                os.environ.pop("VERGE_VOICE_AUTO_FUSE", None)
            else:
                os.environ["VERGE_VOICE_AUTO_FUSE"] = self._voice_auto_fuse_prev
            self._voice_auto_fuse_prev = None
            return self.status.to_dict()

    def _seed_demo_permit(self, pack: ScenarioPack) -> None:
        app = self._app
        if app is None:
            return
        registry = getattr(app.state, "permits", None)
        if registry is None:
            return
        meta = pack.permit or {}
        zone = str(meta.get("zoneId") or pack.zone_primary)
        hours = float(meta.get("validHours") or 4)
        now = datetime.now(UTC)
        permit = Permit(
            permit_id=str(meta.get("permitId") or f"PW-DEMO-{pack.id}"),
            kind=str(meta.get("kind") or "hot-work"),
            zone_id=zone,
            valid_from=now - timedelta(minutes=5),
            valid_to=now + timedelta(hours=hours),
        )
        try:
            registry.upsert(permit)
        except Exception:  # noqa: BLE001
            log.exception("demo permit seed failed")

    def _existing_finding_keys(self) -> set[str]:
        app = self._app
        if app is None:
            return set()
        store = getattr(app.state, "store", None)
        if store is None:
            return set()
        keys: set[str] = set()
        for f in store.list_findings():
            keys.add(self._finding_key(f))
        return keys

    @staticmethod
    def _finding_key(f: RiskFinding | dict) -> str:
        if isinstance(f, RiskFinding):
            zone = f.zone_id or ""
            title = f.title or ""
            lineage = "|".join(f.lineage or [])
        else:
            zone = str(f.get("zoneId") or "")
            title = str(f.get("title") or "")
            lineage = "|".join(f.get("lineage") or [])
        return f"{zone}::{title}::{lineage}"

    def _run(self) -> None:
        assert self._app is not None
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                self._tick_sync()
            except Exception as exc:  # noqa: BLE001
                self.status.last_error = f"{type(exc).__name__}: {exc}"
                log.exception("watch tick failed")
            self.status.ticks += 1
            self.status.last_tick_at = datetime.now(UTC).isoformat()
            elapsed = time.monotonic() - t0
            wait = max(0.2, self.status.interval_s - elapsed)
            if self._stop.wait(timeout=wait):
                break
        self.status.running = False

    def _elapsed_s(self) -> float:
        started = self.status.started_at
        if not started:
            return 0.0
        try:
            t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        return max(0.0, (datetime.now(UTC) - t0).total_seconds())

    def _tick_sync(self) -> None:
        app = self._app
        state = app.state
        tick: dict[str, Any] = {}
        elapsed = self._elapsed_s()
        pack = self._pack

        if pack and pack.duration_s > 0 and elapsed > pack.duration_s + 30:
            # Soft end: keep running but stop advancing scripted cues.
            tick["scenario"] = {"elapsedS": round(elapsed, 1), "complete": True}

        if self.status.legs.get("workers") and pack:
            tick["workers"] = self._tick_workers(state, pack, elapsed)
        if self.status.legs.get("vision"):
            tick["vision"] = self._tick_vision(state)
            if pack:
                inj = self._tick_vision_inject(state, pack, elapsed, tick["vision"])
                if inj.get("injected"):
                    tick["visionInject"] = inj
        if self.status.legs.get("voice"):
            if pack:
                tick["voice"] = self._tick_voice_scenario(state, pack, elapsed)
            else:
                tick["voice"] = self._tick_voice(state)
        if self.status.legs.get("sensors"):
            tick["sensors"] = self._tick_sensors(state, pack, elapsed)
        if self.status.legs.get("fuse"):
            tick["fuse"] = self._tick_fuse(app)
        self.status.last = tick

    def _camera_ids(self) -> list[str]:
        raw = (os.environ.get("VERGE_WATCH_CAMERA_IDS") or "").strip()
        cams = camera_stream.list_cameras()
        if raw:
            want = {c.strip() for c in raw.split(",") if c.strip()}
            return [
                c["cameraId"]
                for c in cams
                if c["cameraId"] in want and c.get("hasSource")
            ]
        return [c["cameraId"] for c in cams if c.get("hasSource")]

    def _tick_vision(self, state) -> dict[str, Any]:
        detector = getattr(state, "vision", None)
        if detector is None:
            return {"ok": False, "reason": "no-vision-provider"}
        results = []
        for cam_id in self._camera_ids():
            snap = camera_stream.grab_snapshot(cam_id)
            if not snap.ok or not snap.jpeg:
                results.append({"cameraId": cam_id, "ok": False, "reason": snap.reason})
                continue
            body = run_detect(
                state,
                detector,
                cam_id,
                None,
                snap.jpeg,
                zone_id=snap.zone_id or None,
            )
            dets = body.get("detections") or []
            n = len(dets)
            self.status.counts["visionFrames"] += 1
            self.status.counts["visionDetections"] += n
            labels = [
                str(d.get("label") if isinstance(d, dict) else getattr(d, "label", ""))
                for d in dets
            ]
            cognee = None
            if (
                self.status.legs.get("cognee")
                and n > 0
                and not body.get("degraded")
                and self.status.ticks % 3 == 0
            ):
                cognee = maybe_ingest_vision_watch(
                    camera_id=cam_id,
                    zone_id=snap.zone_id or "",
                    labels=[x for x in labels if x],
                    detection_count=n,
                )
                if cognee and not cognee.get("degraded"):
                    self.status.counts["cogneeIngests"] += 1
            results.append(
                {
                    "cameraId": cam_id,
                    "ok": True,
                    "degraded": bool(body.get("degraded")),
                    "detections": n,
                    "labels": labels[:8],
                    "cognee": cognee,
                }
            )
        return {"cameras": results, "count": len(results)}

    def _tick_voice(self, state) -> dict[str, Any]:
        if not self._radio_paths:
            return {
                "ok": False,
                "reason": "no-radio-sources",
                "hint": "Set VERGE_WATCH_RADIO_DIR or VERGE_WATCH_RADIO_GLOB",
            }
        path = self._radio_paths[self._radio_idx % len(self._radio_paths)]
        self._radio_idx += 1
        audio = path.read_bytes()
        if not audio:
            return {"ok": False, "reason": "empty-audio", "path": str(path)}
        from verge_voice import transcribe_audio

        llm = getattr(state, "llm", None)
        result = transcribe_audio(
            audio,
            filename=path.name,
            content_type="audio/wav",
            provider=llm,
        )
        english = (
            getattr(result, "transcript_en", None)
            or getattr(result, "transcript", "")
            or ""
        )
        if result.degraded or not str(english).strip():
            return {
                "ok": False,
                "degraded": True,
                "reason": getattr(result, "reason", None) or "transcribe-degraded",
                "path": str(path),
            }
        structured = getattr(result, "structured", None) or {}
        zones = structured.get("zones") or []
        zone_id = zones[0] if zones else None
        ev = record_voice_event(
            state,
            transcript=str(english),
            structured=structured,
            zone_id=zone_id,
            source="watch-radio",
            transcript_original=getattr(result, "transcript_original", None),
            languages_detected=list(getattr(result, "languages_detected", ()) or ()),
        )
        uri = store_clip(state, ev.event_id, audio, content_type="audio/wav")
        if uri:
            ev.audio_clip_uri = uri
        self.status.counts["voiceEvents"] += 1
        cognee = None
        if self.status.legs.get("cognee"):
            cognee = maybe_ingest_voice_ops(
                str(english), structured=structured, source="watch-radio"
            )
            if cognee and not cognee.get("degraded"):
                self.status.counts["cogneeIngests"] += 1
        return {
            "ok": True,
            "path": str(path),
            "eventId": ev.event_id,
            "zoneId": ev.zone_id,
            "transcript": str(english)[:200],
            "audioClipUri": uri or None,
            "cognee": cognee,
        }

    def _tick_vision_inject(
        self,
        state,
        pack: ScenarioPack,
        elapsed: float,
        vision_tick: dict[str, Any],
    ) -> dict[str, Any]:
        """CI / degraded occupancy: inject person cue if live detect is empty."""
        from .vision_events import record_vision_detections

        live_dets = 0
        for cam in vision_tick.get("cameras") or []:
            live_dets += int(cam.get("detections") or 0)
        if live_dets > 0:
            return {"injected": False, "reason": "live-detections-present"}
        due = [
            c
            for c in pack.vision
            if not c.played and elapsed >= c.at
        ]
        if not due:
            return {"injected": False, "reason": "no-due-cues"}
        payloads = []
        for cue in due:
            cue.played = True
            payloads.append(
                {
                    "detectionId": f"VD-DEMO-{uuid.uuid4().hex[:8].upper()}",
                    "ts": datetime.now(UTC).isoformat(),
                    "cameraId": cue.camera_id,
                    "zoneId": cue.zone_id,
                    "label": cue.label,
                    "confidence": cue.confidence,
                    "source": "demo-inject",
                }
            )
        recorded = record_vision_detections(state, payloads)
        self.status.counts["visionDetections"] += len(recorded)
        return {
            "injected": True,
            "count": len(recorded),
            "labels": [c.label for c in due],
        }

    def _tick_workers(
        self, state, pack: ScenarioPack, elapsed: float
    ) -> dict[str, Any]:
        occupancy = getattr(state, "occupancy", None)
        if occupancy is None:
            return {"ok": False, "reason": "no-occupancy"}
        now = datetime.now(UTC).isoformat()
        applied = []
        for cue in pack.workers:
            if cue.played or elapsed < cue.at or not cue.worker_id:
                continue
            payload = {
                "type": "worker-location",
                "ts": now,
                "workerId": cue.worker_id,
                "zoneId": cue.zone_id,
                "name": cue.name,
                "role": cue.role,
                "source": "demo-drill",
                "eventId": f"DEMO-W-{uuid.uuid4().hex[:8].upper()}",
            }
            try:
                occupancy.ingest(payload)
                cue.played = True
                self.status.counts["workerFixes"] += 1
                applied.append(
                    {
                        "workerId": cue.worker_id,
                        "zoneId": cue.zone_id,
                        "at": cue.at,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("demo worker ingest failed: %s", exc)
        return {"ok": True, "applied": applied, "count": len(applied)}

    def _tick_voice_scenario(
        self, state, pack: ScenarioPack, elapsed: float
    ) -> dict[str, Any]:
        """Play timed radio cues once; WAV → Melia, else English text fallback."""
        due = next(
            (c for c in pack.radio if not c.played and elapsed >= c.at),
            None,
        )
        if due is None:
            return {"ok": True, "idle": True, "elapsedS": round(elapsed, 1)}

        due.played = True
        if due.path is not None and due.path.is_file():
            audio = due.path.read_bytes()
            if audio:
                from verge_voice import transcribe_audio

                llm = getattr(state, "llm", None)
                result = transcribe_audio(
                    audio,
                    filename=due.path.name,
                    content_type="audio/wav",
                    provider=llm,
                )
                english = (
                    getattr(result, "transcript_en", None)
                    or getattr(result, "transcript", "")
                    or ""
                )
                if not result.degraded and str(english).strip():
                    structured = getattr(result, "structured", None) or {}
                    zones = structured.get("zones") or []
                    zone_id = zones[0] if zones else due.zone_id
                    ev = record_voice_event(
                        state,
                        transcript=str(english),
                        structured=structured,
                        zone_id=zone_id,
                        source="demo-radio",
                        transcript_original=getattr(
                            result, "transcript_original", None
                        ),
                        languages_detected=list(
                            getattr(result, "languages_detected", ()) or ()
                        ),
                    )
                    uri = store_clip(
                        state, ev.event_id, audio, content_type="audio/wav"
                    )
                    if uri:
                        ev.audio_clip_uri = uri
                    self.status.counts["voiceEvents"] += 1
                    cognee = None
                    if self.status.legs.get("cognee"):
                        cognee = maybe_ingest_voice_ops(
                            str(english),
                            structured=structured,
                            source="demo-radio",
                        )
                        if cognee and not cognee.get("degraded"):
                            self.status.counts["cogneeIngests"] += 1
                    return {
                        "ok": True,
                        "path": str(due.path),
                        "eventId": ev.event_id,
                        "zoneId": ev.zone_id,
                        "transcript": str(english)[:200],
                        "audioClipUri": uri or None,
                        "lang": due.lang,
                        "cognee": cognee,
                    }

        # Degraded path: inject script text so fusion still has a voice leg.
        text = due.text or f"Radio cue at B-04 ({due.file})"
        hazards = []
        low = text.lower()
        for h in ("gas", "smell", "lel", "hold", "hot-work", "flammable"):
            if h.replace("-", " ") in low or h in low:
                hazards.append(h if h != "hot-work" else "hot-work")
        structured = {
            "zones": [due.zone_id],
            "hazards": hazards or ["gas", "smell"],
        }
        ev = record_voice_event(
            state,
            transcript=text,
            structured=structured,
            zone_id=due.zone_id,
            source="demo-radio-text",
            languages_detected=[due.lang],
        )
        self.status.counts["voiceEvents"] += 1
        return {
            "ok": True,
            "degraded": True,
            "reason": "no-wav-text-fallback",
            "file": due.file,
            "eventId": ev.event_id,
            "zoneId": ev.zone_id,
            "transcript": text[:200],
            "lang": due.lang,
        }

    def _tick_sensors(
        self,
        state,
        pack: ScenarioPack | None = None,
        elapsed: float | None = None,
    ) -> dict[str, Any]:
        """Advance plant sensors on a watch / scenario curve (honest drill)."""
        plant = getattr(state, "plant", None)
        buf = getattr(state, "readings", None)
        if plant is None or buf is None:
            return {"ok": False, "reason": "no-plant-or-readings"}
        sensors = getattr(plant, "sensors", None) or {}
        if not sensors:
            return {"ok": False, "reason": "no-plant-sensors"}

        if elapsed is None:
            elapsed = self._elapsed_s()
        if pack is not None:
            factor = pack.sensor_factor(elapsed)
        elif elapsed < 40:
            factor = 0.04
        elif elapsed < 100:
            # Creep under classic alarm; stay soft vs early fusion alone.
            factor = 0.04 + (elapsed - 40) / 60 * 0.10
        elif elapsed < 150:
            factor = 0.14 + (elapsed - 100) / 50 * 0.34
        else:
            factor = max(0.20, 0.48 - (elapsed - 150) / 120 * 0.25)

        now = datetime.now(UTC).isoformat()
        ingested = []
        for sid, node in list(sensors.items())[:12]:
            kind = str(getattr(node, "kind", None) or "unknown").lower()
            zone_id = str(getattr(node, "zone_id", None) or "UNKNOWN")
            unit = str(getattr(node, "unit", None) or "")
            node_thr = getattr(node, "threshold", None)
            if any(k in kind for k in ("lel", "gas", "voc", "h2s", "flammable")):
                thr = float(node_thr) if node_thr is not None else 0.0
                if thr <= 0:
                    thr = 100.0 if "lel" in kind else 50.0
                value = round(thr * factor, 4)
            else:
                base = float(node_thr) if node_thr is not None else 1.0
                value = round(base * (0.1 + factor * 0.05), 4)
            payload = {
                "type": "reading",
                "ts": now,
                "sensorId": sid,
                "kind": kind,
                "unit": unit,
                "zoneId": zone_id,
                "value": value,
                "eventId": f"WATCH-{uuid.uuid4().hex[:10].upper()}",
            }
            buf.ingest(payload)
            self.status.counts["sensorReads"] += 1
            ingested.append({"sensorId": sid, "value": value, "zoneId": zone_id})
        return {
            "ok": True,
            "elapsedS": round(elapsed, 1),
            "factor": round(factor, 3),
            "readings": ingested[:8],
        }

    def _tick_fuse(self, app) -> dict[str, Any]:
        persist = _env_bool("VERGE_WATCH_FUSE_PERSIST", True)
        out = run_live_fusion(app.state, persist=False, limit=50)
        findings = out.get("findings") or []
        persisted_ids: list[str] = []
        if persist and findings:
            store = app.state.store
            for raw in findings:
                try:
                    f = RiskFinding.model_validate(raw)
                except Exception:
                    continue
                key = self._finding_key(f)
                if key in self._seen_finding_keys:
                    continue
                store.add_finding(f)
                self._seen_finding_keys.add(key)
                persisted_ids.append(f.finding_id)
                self.status.counts["findingsPersisted"] += 1
                if self.status.legs.get("cognee"):
                    cog = maybe_ingest_open_finding(f)
                    if cog and not cog.get("degraded"):
                        self.status.counts["cogneeIngests"] += 1
            try:
                from .stream_notify import drain_outbox

                drain_outbox(app)
            except Exception:  # noqa: BLE001
                pass
        return {
            "ok": True,
            "evaluated": out.get("count", 0),
            "persisted": len(persisted_ids),
            "findingIds": persisted_ids,
            "inputs": out.get("inputs"),
        }


controller = WatchController()
