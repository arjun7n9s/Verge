"""Best-effort post-ingest hooks for documents (Cognee + Neo4j). Never raise."""

from __future__ import annotations

import os

from verge_docintel.pipeline import DocIntelStore
from verge_memory import ingest_document
from verge_memory.client import CogneeClient
from verge_memory.datasets import dataset_name
from verge_schema.documents import DocumentAsset, DocumentStatus, EntityKind

_TRUE = {"1", "true", "yes", "on"}


def maybe_cognify_document(store: DocIntelStore, asset: DocumentAsset) -> dict:
    """Push ready document text into Cognee when configured."""
    if asset.status != DocumentStatus.READY:
        return {"degraded": True, "reason": "not-ready"}
    if os.environ.get("VERGE_COGNEE_ENABLED", "").lower() not in _TRUE:
        return {"degraded": True, "reason": "cognee-disabled"}
    text = store.texts.get(asset.document_id, "")
    if not text.strip():
        return {"degraded": True, "reason": "empty-text"}
    try:
        env = dict(os.environ)
        client = CogneeClient.from_env(env)
        result = ingest_document(client, dataset_name(env), asset.title, text)
        return {
            "degraded": bool(getattr(result, "degraded", False)),
            "reason": getattr(result, "reason", "") or "",
        }
    except Exception as exc:
        return {"degraded": True, "reason": f"cognee:{type(exc).__name__}"}


def maybe_sync_entities_neo4j(store: DocIntelStore, asset: DocumentAsset) -> dict:
    """Upsert Document + EntityMention nodes into Neo4j when configured."""
    if asset.status != DocumentStatus.READY:
        return {"degraded": True, "reason": "not-ready"}
    uri = os.environ.get("NEO4J_URI")
    password = os.environ.get("NEO4J_PASSWORD")
    user = os.environ.get("NEO4J_USER", "neo4j")
    if not uri or not password:
        return {"degraded": True, "reason": "neo4j-unconfigured"}
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"degraded": True, "reason": "neo4j-driver-missing"}

    entities = store.entities.get(asset.document_id, [])
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run(
                "MERGE (d:Document {id: $id}) "
                "SET d.title = $title, d.kind = $kind",
                id=asset.document_id,
                title=asset.title,
                kind=str(asset.kind.value if hasattr(asset.kind, "value") else asset.kind),
            )
            for ent in entities:
                label = {
                    EntityKind.EQUIPMENT: "EquipmentTag",
                    EntityKind.ZONE: "ZoneMention",
                    EntityKind.PERMIT: "PermitMention",
                    EntityKind.CLAUSE: "ClauseMention",
                }.get(ent.kind, "Entity")
                session.run(
                    f"MERGE (e:{label} {{id: $id}}) "
                    "SET e.raw = $raw, e.normalized = $norm "
                    "WITH e MATCH (d:Document {id: $doc}) "
                    "MERGE (d)-[:MENTIONS]->(e)",
                    id=ent.entity_id,
                    raw=ent.raw,
                    norm=ent.normalized or ent.raw,
                    doc=asset.document_id,
                )
        driver.close()
        return {"degraded": False, "entities": len(entities)}
    except Exception as exc:
        return {"degraded": True, "reason": f"neo4j:{type(exc).__name__}"}
