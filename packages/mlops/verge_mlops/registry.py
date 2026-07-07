"""Model registry with a shadow → canary → production lifecycle (spec §14 Phase 4).

Verge's safety path is rules + classic ML; the ML layer (IsolationForest today,
CV models on the plant GPU box) needs the same discipline as the finding
lifecycle: nothing goes to production without passing through **shadow** (runs
silently alongside) and **canary** (limited live) first, and every promotion is
an explicit, recorded transition. This mirrors §14.5 shadow-mode commissioning,
one layer down.

The registry is file-backed JSON — no database, no service — so it version-
controls and ships inside an air-gapped bundle (P2). Exactly one model per name
can be in ``production`` at a time; promoting a replacement retires the incumbent.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "samples"
DEMO_REGISTRY = SAMPLES_DIR / "demo-registry.json"

# Lifecycle stages and their legal transitions (a small state machine, like the
# finding lifecycle). A model may be retired from any stage.
REGISTERED = "registered"
SHADOW = "shadow"
CANARY = "canary"
PRODUCTION = "production"
RETIRED = "retired"

_LEGAL: dict[str, set[str]] = {
    REGISTERED: {SHADOW, RETIRED},
    SHADOW: {CANARY, RETIRED},
    CANARY: {PRODUCTION, SHADOW, RETIRED},
    PRODUCTION: {RETIRED},
    RETIRED: set(),
}


class IllegalPromotion(ValueError):
    """Raised on a stage transition the lifecycle does not allow."""


@dataclass
class ModelCard:
    model_id: str
    name: str
    version: str
    kind: str  # isolation-forest | rt-detr | ...
    stage: str = REGISTERED
    metrics: dict = field(default_factory=dict)
    artifact_ref: str | None = None
    notes: str = ""
    created_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_raw(raw: dict) -> ModelCard:
        """Build from a stored dict, ignoring unknown keys (forward-compatible:
        a registry written by a newer version still loads)."""
        known = {f.name for f in fields(ModelCard)}
        return ModelCard(**{k: v for k, v in raw.items() if k in known})


class ModelRegistry:
    """In-memory registry with optional JSON persistence."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else None
        self._models: dict[str, ModelCard] = {}
        if self._path and self._path.exists():
            self._load()

    # ── persistence ───────────────────────────────────────────────────────
    def _load(self) -> None:
        doc = json.loads(self._path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
        for raw in doc.get("models", []):
            card = ModelCard.from_raw(raw)
            self._models[card.model_id] = card

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"models": [c.to_dict() for c in self._models.values()]}
        text = json.dumps(payload, indent=2, sort_keys=True)
        # Atomic write: never leave a half-written registry if the process dies
        # mid-save (the registry is a version-controlled bundle artifact).
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self._path)

    # ── registry ops ──────────────────────────────────────────────────────
    def register(self, card: ModelCard) -> ModelCard:
        card.stage = card.stage or REGISTERED
        self._models[card.model_id] = card
        self._save()
        return card

    def get(self, model_id: str) -> ModelCard | None:
        return self._models.get(model_id)

    def list(self, *, name: str | None = None, stage: str | None = None) -> list[ModelCard]:
        cards = list(self._models.values())
        if name is not None:
            cards = [c for c in cards if c.name == name]
        if stage is not None:
            cards = [c for c in cards if c.stage == stage]
        return sorted(cards, key=lambda c: (c.name, c.version))

    def production(self, name: str) -> ModelCard | None:
        """The current production model for a name (at most one)."""
        return next((c for c in self._models.values()
                     if c.name == name and c.stage == PRODUCTION), None)

    def promote(self, model_id: str, to_stage: str) -> ModelCard:
        card = self._models.get(model_id)
        if card is None:
            raise KeyError(model_id)
        if to_stage not in _LEGAL.get(card.stage, set()):
            raise IllegalPromotion(f"{card.stage} → {to_stage} is not allowed")
        # One production model per name: retire the incumbent on promotion.
        if to_stage == PRODUCTION:
            incumbent = self.production(card.name)
            if incumbent is not None and incumbent.model_id != model_id:
                incumbent.stage = RETIRED
        card.stage = to_stage
        self._save()
        return card

    @classmethod
    def read_only(cls, path: str | Path) -> ModelRegistry:
        """Load a registry into memory without binding it to disk (no writes).

        Used for the bundled demo and for serving a read-only view of a registry
        that lives inside a signed bundle."""
        reg = cls(path=None)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        for raw in doc.get("models", []):
            card = ModelCard.from_raw(raw)
            reg._models[card.model_id] = card
        return reg

    def summary(self) -> dict:
        by_stage: dict[str, int] = {}
        for c in self._models.values():
            by_stage[c.stage] = by_stage.get(c.stage, 0) + 1
        production = {c.name: c.version for c in self._models.values() if c.stage == PRODUCTION}
        return {"total": len(self._models), "byStage": by_stage, "production": production}
