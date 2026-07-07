"""Model router — pick which model version serves a scoring request (spec §14 P4).

A canary is only useful if traffic actually reaches it in a controlled way. The
router sends a request for a model *name* to the production version by default,
but routes to the canary for a configured set of zones — a canary rollout scoped
to, say, one battery before plant-wide promotion. If neither exists, it routes to
nothing and says so (degraded), so the caller falls back to rules rather than a
guessed model (P1: the safety path never depends on the ML layer being up).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .registry import CANARY, PRODUCTION, ModelCard, ModelRegistry


@dataclass
class RouteDecision:
    name: str
    zone: str | None
    stage: str | None  # production | canary | None
    model: ModelCard | None
    reason: str

    @property
    def routed(self) -> bool:
        return self.model is not None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "zone": self.zone,
            "stage": self.stage,
            "modelId": self.model.model_id if self.model else None,
            "version": self.model.version if self.model else None,
            "routed": self.routed,
            "reason": self.reason,
        }


class ModelRouter:
    """Routes scoring requests across production/canary using a per-name canary
    zone map: ``{model_name: {zone_id, ...}}``."""

    def __init__(
        self, registry: ModelRegistry, canary_zones: Mapping[str, set[str]] | None = None
    ) -> None:
        self._registry = registry
        self._canary_zones = {k: set(v) for k, v in (canary_zones or {}).items()}

    def set_canary_zones(self, name: str, zones: set[str]) -> None:
        self._canary_zones[name] = set(zones)

    def route(self, name: str, *, zone: str | None = None) -> RouteDecision:
        canary_zones = self._canary_zones.get(name, set())
        if zone is not None and zone in canary_zones:
            canary = self._registry.list(name=name, stage=CANARY)
            if canary:
                return RouteDecision(name, zone, CANARY, canary[0],
                                     f"canary rollout active for zone {zone}")
        production = self._registry.production(name)
        if production is not None:
            return RouteDecision(name, zone, PRODUCTION, production,
                                 "routed to production model")
        # No production model — the caller must fall back to rules (P1).
        canary = self._registry.list(name=name, stage=CANARY)
        if canary:
            return RouteDecision(name, zone, CANARY, canary[0],
                                 "no production model; canary available")
        return RouteDecision(name, zone, None, None,
                             f"no production or canary model for '{name}'")
