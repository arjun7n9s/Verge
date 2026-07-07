"""Plant graph sync — Neo4j equipment-permit-zone relationships (spec §5)."""

from __future__ import annotations

from fastapi import APIRouter
from verge_risk import STARTER_RULES, load_rules
from verge_twin import load_plant
from verge_twin.neo4j_sync import sync_plant
from verge_twin.plant import DEMO_PLANT

router = APIRouter(tags=["plant"])


@router.post("/plant/graph-sync")
def plant_graph_sync() -> dict:
    """Push the commissioned demo plant into Neo4j when configured."""
    plant = load_plant(DEMO_PLANT)
    _ = load_rules(STARTER_RULES)  # ensures rules library is loadable
    return sync_plant(plant)
