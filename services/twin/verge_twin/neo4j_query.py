"""Neo4j read helpers for compound-risk scoring and GraphRAG (Phase 2.5)."""

from __future__ import annotations

import os
from typing import Any


def _auth(env: dict[str, str]) -> tuple[str, str, str] | None:
    uri = env.get("NEO4J_URI")
    password = env.get("NEO4J_PASSWORD")
    user = env.get("NEO4J_USER", "neo4j")
    if not uri or not password:
        return None
    return uri, user, password


def zone_graph_coverage(
    zone_id: str,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return adjacency coverage for a zone; degrades when Neo4j is unset."""
    env = dict(os.environ) if env is None else env
    creds = _auth(env)
    if creds is None:
        return {"degraded": True, "coveragePct": 0.0, "reason": "neo4j not configured"}
    uri, user, password = creds

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"degraded": True, "coveragePct": 0.0, "reason": "neo4j driver missing"}

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            total = session.run(
                "MATCH (z:Zone {id: $id})-[:HAS_SENSOR]->() RETURN count(*) AS n",
                id=zone_id,
            ).single()["n"]
            linked = session.run(
                "MATCH (z:Zone {id: $id})-[:HAS_SENSOR]->(e:Equipment) "
                "WHERE EXISTS { MATCH (e)-[:ADJACENT_TO|NEAR*1..2]-(:Equipment) } "
                "RETURN count(DISTINCT e) AS n",
                id=zone_id,
            ).single()["n"]
        driver.close()
        pct = round(100.0 * linked / total, 1) if total else 0.0
        return {"degraded": False, "coveragePct": pct, "sensors": int(total)}
    except Exception as exc:
        return {"degraded": True, "coveragePct": 0.0, "reason": type(exc).__name__}


def zone_document_hops(
    zone_id: str,
    *,
    env: dict[str, str] | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """GraphRAG template: Document -[:MENTIONS]-> entity near a zone id.

    Returns multi-hop citation rows (doc → mention → zone token). Degrades
    cleanly when Neo4j is unset or empty — callers still have the local twin.
    """
    env = dict(os.environ) if env is None else env
    creds = _auth(env)
    if creds is None:
        return {"degraded": True, "hops": [], "reason": "neo4j not configured"}
    uri, user, password = creds

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"degraded": True, "hops": [], "reason": "neo4j driver missing"}

    # Match docs that mention the zone id (as ZoneMention or in normalized text)
    # or equipment tags whose normalized/raw contains the zone token.
    cypher = """
    MATCH (d:Document)-[:MENTIONS]->(e)
    WHERE e.normalized CONTAINS $zone
       OR e.raw CONTAINS $zone
       OR e.id CONTAINS $zone
       OR (e:ZoneMention AND (e.id = $zone OR e.normalized = $zone))
    RETURN d.id AS documentId,
           d.title AS title,
           labels(e) AS mentionLabels,
           e.id AS mentionId,
           e.normalized AS mentionNorm,
           e.raw AS mentionRaw
    LIMIT $limit
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        hops: list[dict[str, Any]] = []
        with driver.session() as session:
            rows = session.run(cypher, zone=zone_id, limit=int(limit))
            for row in rows:
                hops.append({
                    "from": row["documentId"],
                    "rel": "MENTIONS",
                    "to": row["mentionId"],
                    "title": row["title"],
                    "mentionLabels": list(row["mentionLabels"] or []),
                    "mentionNorm": row["mentionNorm"],
                    "path": [
                        {"kind": "Document", "id": row["documentId"]},
                        {"kind": "MENTIONS", "id": None},
                        {
                            "kind": (row["mentionLabels"] or ["Entity"])[0],
                            "id": row["mentionId"],
                        },
                        {"kind": "Zone", "id": zone_id},
                    ],
                })
        driver.close()
        return {
            "degraded": False,
            "zoneId": zone_id,
            "hops": hops,
            "count": len(hops),
            "reason": "" if hops else "no-document-mentions",
        }
    except Exception as exc:
        return {"degraded": True, "hops": [], "reason": type(exc).__name__}


def zone_equipment_document_hops(
    zone_id: str,
    *,
    env: dict[str, str] | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """GraphRAG multi-hop: Zone → Equipment → Document MENTIONS.

    Path shape: ``(Zone)-[:HAS_SENSOR]->(Equipment)`` joined to
    ``(Document)-[:MENTIONS]->(mention)`` when the mention matches the
    equipment id / normalized tag. Degrades cleanly when Neo4j is unset.
    """
    env = dict(os.environ) if env is None else env
    creds = _auth(env)
    if creds is None:
        return {"degraded": True, "hops": [], "reason": "neo4j not configured"}
    uri, user, password = creds

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"degraded": True, "hops": [], "reason": "neo4j driver missing"}

    cypher = """
    MATCH (z:Zone {id: $zone})-[:HAS_SENSOR]->(eq:Equipment)
    MATCH (d:Document)-[:MENTIONS]->(m)
    WHERE m.id = eq.id
       OR m.normalized = eq.id
       OR m.raw = eq.id
       OR (m.normalized IS NOT NULL AND toLower(m.normalized) CONTAINS toLower(eq.id))
       OR (m.raw IS NOT NULL AND toLower(m.raw) CONTAINS toLower(eq.id))
    RETURN z.id AS zoneId,
           eq.id AS equipmentId,
           d.id AS documentId,
           d.title AS title,
           m.id AS mentionId,
           m.normalized AS mentionNorm,
           labels(m) AS mentionLabels
    LIMIT $limit
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        hops: list[dict[str, Any]] = []
        with driver.session() as session:
            rows = session.run(cypher, zone=zone_id, limit=int(limit))
            for row in rows:
                hops.append({
                    "from": row["documentId"],
                    "rel": "MENTIONS_EQUIPMENT_IN_ZONE",
                    "to": row["equipmentId"],
                    "title": row["title"],
                    "mentionId": row["mentionId"],
                    "mentionNorm": row["mentionNorm"],
                    "mentionLabels": list(row["mentionLabels"] or []),
                    "path": [
                        {"kind": "Document", "id": row["documentId"]},
                        {"kind": "MENTIONS", "id": None},
                        {
                            "kind": (row["mentionLabels"] or ["Entity"])[0],
                            "id": row["mentionId"],
                        },
                        {"kind": "Equipment", "id": row["equipmentId"]},
                        {"kind": "Zone", "id": zone_id},
                    ],
                })
        driver.close()
        return {
            "degraded": False,
            "zoneId": zone_id,
            "hops": hops,
            "count": len(hops),
            "reason": "" if hops else "no-equipment-document-hops",
        }
    except Exception as exc:
        return {"degraded": True, "hops": [], "reason": type(exc).__name__}
