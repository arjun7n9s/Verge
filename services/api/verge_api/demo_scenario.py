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
class DemoPhase:
    id: str
    label: str
    hint: str
    at: float


# Default Meridian drill phases (elapsed seconds). Pack YAML may override via `phases:`.
_DEFAULT_PHASES: list[DemoPhase] = [
    DemoPhase(
        id="baseline",
        label="Baseline",
        hint="Quiet feeds — LEL normal, radio silent, cameras idle.",
        at=0,
    ),
    DemoPhase(
        id="hot-work",
        label="Hot work",
        hint="Permit chatter — routine work; single streams still look benign.",
        at=40,
    ),
    DemoPhase(
        id="weak-smell",
        label="Weak smell",
        hint="Radio smell report; LEL creeping but still under classic alarm.",
        at=80,
    ),
    DemoPhase(
        id="people-still",
        label="People still there",
        hint="Camera shows people in bay — occupancy risk with rising gas.",
        at=110,
    ),
    DemoPhase(
        id="converge",
        label="Converge",
        hint="Voice + LEL + vision together — early compound finding.",
        at=140,
    ),
    DemoPhase(
        id="advise",
        label="Advise",
        hint="Open the finding — hold work / clear bay (advisory).",
        at=170,
    ),
]


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
    phases: list[DemoPhase] = field(default_factory=list)
    root: Path = field(default_factory=Path)

    def phase_at(self, elapsed_s: float) -> dict[str, Any]:
        """Current narrative phase for the Live Ops coach strip."""
        phases = self.phases or list(_DEFAULT_PHASES)
        current = phases[0]
        for p in phases:
            if elapsed_s >= p.at:
                current = p
            else:
                break
        return {
            "phaseId": current.id,
            "phaseLabel": current.label,
            "phaseHint": current.hint,
            "phases": [
                {"id": p.id, "label": p.label, "at": p.at, "active": p.id == current.id}
                for p in phases
            ],
            "elapsedS": round(elapsed_s, 1),
        }

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
    phases: list[DemoPhase] = []
    for item in raw.get("phases") or []:
        phases.append(
            DemoPhase(
                id=str(item.get("id") or "phase"),
                label=str(item.get("label") or item.get("id") or "Phase"),
                hint=str(item.get("hint") or "").strip(),
                at=float(item.get("at", 0)),
            )
        )
    if not phases:
        # Scale default Meridian phases when pack duration differs (e.g. CI).
        duration = float(raw.get("duration_s") or 210)
        scale = duration / 210.0 if duration > 0 else 1.0
        if abs(scale - 1.0) > 0.05:
            phases = [
                DemoPhase(
                    id=p.id,
                    label=p.label,
                    hint=p.hint,
                    at=round(p.at * scale, 1),
                )
                for p in _DEFAULT_PHASES
            ]
        else:
            phases = list(_DEFAULT_PHASES)
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
        phases=phases,
        root=root,
    )
