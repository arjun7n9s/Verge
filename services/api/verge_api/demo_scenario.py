"""Load named scenario packs for the compound multi-source demo drill."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCENARIOS = _REPO_ROOT / "scenarios"


@dataclass
class RadioCue:
    at: float
    file: str
    lang: str
    zone_id: str
    text: str
    path: Path | None = None
    played: bool = False


@dataclass
class WorkerCue:
    at: float
    worker_id: str
    zone_id: str
    name: str | None
    role: str | None
    played: bool = False


@dataclass
class VisionCue:
    """Optional occupancy inject when live detect is empty (CI / degraded)."""

    at: float
    camera_id: str
    zone_id: str
    label: str
    confidence: float
    played: bool = False


@dataclass
class ScenarioPack:
    id: str
    name: str
    label: str
    coach: str
    duration_s: float
    interval_s: float
    zone_primary: str
    zone_secondary: str
    permit: dict[str, Any]
    sensor_curve: list[tuple[float, float]]
    radio: list[RadioCue] = field(default_factory=list)
    workers: list[WorkerCue] = field(default_factory=list)
    vision: list[VisionCue] = field(default_factory=list)
    root: Path = field(default_factory=Path)

    def sensor_factor(self, elapsed_s: float) -> float:
        curve = self.sensor_curve
        if not curve:
            return 0.15
        if elapsed_s <= curve[0][0]:
            return curve[0][1]
        if elapsed_s >= curve[-1][0]:
            return curve[-1][1]
        for i in range(1, len(curve)):
            t1, f1 = curve[i - 1]
            t2, f2 = curve[i]
            if elapsed_s <= t2:
                if t2 <= t1:
                    return f2
                u = (elapsed_s - t1) / (t2 - t1)
                return f1 + u * (f2 - f1)
        return curve[-1][1]

    def reset_cues(self) -> None:
        for c in self.radio:
            c.played = False
        for c in self.workers:
            c.played = False
        for c in self.vision:
            c.played = False


def load_scenario(scenario_id: str = "compound-drill") -> ScenarioPack:
    root = _SCENARIOS / scenario_id
    path = root / "scenario.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"scenario pack not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    radio_dir = root / "radio"
    radio: list[RadioCue] = []
    for item in raw.get("radio") or []:
        fname = str(item.get("file") or "")
        wav = radio_dir / fname if fname else None
        radio.append(
            RadioCue(
                at=float(item.get("at", 0)),
                file=fname,
                lang=str(item.get("lang") or "en"),
                zone_id=str(item.get("zoneId") or raw.get("zone_primary") or "B-04"),
                text=str(item.get("text") or "").strip(),
                path=wav if wav is not None and wav.is_file() else None,
            )
        )
    workers: list[WorkerCue] = []
    for item in raw.get("workers") or []:
        workers.append(
            WorkerCue(
                at=float(item.get("at", 0)),
                worker_id=str(item.get("workerId") or ""),
                zone_id=str(item.get("zoneId") or ""),
                name=item.get("name"),
                role=item.get("role"),
            )
        )
    vision: list[VisionCue] = []
    for item in raw.get("vision") or []:
        vision.append(
            VisionCue(
                at=float(item.get("at", 0)),
                camera_id=str(item.get("cameraId") or "demo"),
                zone_id=str(item.get("zoneId") or raw.get("zone_primary") or "B-04"),
                label=str(item.get("label") or "person"),
                confidence=float(item.get("confidence") or 0.75),
            )
        )
    curve_raw = ((raw.get("sensors") or {}).get("curve")) or []
    curve = [(float(p["at"]), float(p["factor"])) for p in curve_raw]
    return ScenarioPack(
        id=str(raw.get("id") or scenario_id),
        name=str(raw.get("name") or scenario_id),
        label=str(raw.get("label") or "DEMO DRILL"),
        coach=str(raw.get("coach") or ""),
        duration_s=float(raw.get("duration_s") or 210),
        interval_s=float(raw.get("interval_s") or 3.0),
        zone_primary=str(raw.get("zone_primary") or "B-04"),
        zone_secondary=str(raw.get("zone_secondary") or "B-05"),
        permit=dict(raw.get("permit") or {}),
        sensor_curve=curve,
        radio=radio,
        workers=workers,
        vision=vision,
        root=root,
    )
