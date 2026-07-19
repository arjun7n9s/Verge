"""Neo4j VoiceEvent linkage — ``(:VoiceEvent)-[:ABOUT]->(:Zone|:Equipment)``.

Best-effort: missing Neo4j / driver / zone → degraded dict, never raises to
the voice ingest path.
"""

from __future__ import annotations

import os
from typing import Any

from verge_schema.events import VoiceEvent


def sync_voice_event(
    event: VoiceEvent,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Upsert a VoiceEvent node and ABOUT edges to zone / equipment."""
    env = env or dict(os.environ)
    uri = env.get("NEO4J_URI")
    if not uri:
        return {"degraded": True, "reason": "neo4j not configured"}
    user = env.get("NEO4J_USER", "neo4j")
    password = env.get("NEO4J_PASSWORD", "")
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"degraded": True, "reason": "neo4j driver not installed"}

    linked_zone = False
    linked_equipment = 0
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run(
                """
                MERGE (v:VoiceEvent {id: $id})
                SET v.ts = $ts,
                    v.transcript = $transcript,
                    v.source = $source,
                    v.hazards = $hazards
                """,
                id=event.event_id,
                ts=event.ts.isoformat(),
                transcript=(event.transcript or "")[:500],
                source=event.source or "radio",
                hazards=list(event.hazards or []),
            )
            if event.zone_id:
                session.run(
                    """
                    MERGE (z:Zone {id: $zone})
                    WITH z
                    MATCH (v:VoiceEvent {id: $id})
                    MERGE (v)-[:ABOUT]->(z)
                    """,
                    zone=event.zone_id,
                    id=event.event_id,
                )
                linked_zone = True
            for eq in event.equipment_ids or []:
                if not eq:
                    continue
                session.run(
                    """
                    MERGE (e:Equipment {id: $eq})
                    WITH e
                    MATCH (v:VoiceEvent {id: $id})
                    MERGE (v)-[:ABOUT]->(e)
                    """,
                    eq=str(eq),
                    id=event.event_id,
                )
                linked_equipment += 1
        driver.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "degraded": True,
            "reason": f"neo4j voice sync failed: {type(exc).__name__}",
        }
    return {
        "degraded": False,
        "eventId": event.event_id,
        "linkedZone": linked_zone,
        "linkedEquipment": linked_equipment,
    }


__all__ = ["sync_voice_event"]
