"""Neo4j read helpers for compound-risk scoring (spec §4.1 / §5)."""

from __future__ import annotations

import os
from typing import Any


def zone_graph_coverage(
    zone_id: str,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return adjacency coverage for a zone; degrades when Neo4j is unset."""
    env = env or dict(os.environ)
    uri = env.get("NEO4J_URI")
    password = env.get("NEO4J_PASSWORD")
    user = env.get("NEO4J_USER", "neo4j")
    if not uri or not password:
        return {"degraded": True, "coveragePct": 0.0, "reason": "neo4j not configured"}

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
