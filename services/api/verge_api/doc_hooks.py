"""Best-effort post-ingest hooks for documents (Cognee + Neo4j). Never raise."""

from __future__ import annotations

import os

from verge_docintel.pipeline import DocIntelStore
from verge_memory.client import CogneeClient
from verge_memory.datasets import dataset_name
from verge_memory.ingest import ingest_and_cognify
from verge_schema.documents import DocumentAsset, DocumentStatus, EntityKind


def maybe_cognify_document(store: DocIntelStore, asset: DocumentAsset) -> dict:
    """Push ready document text into Cognee when configured.

    Enabled when ``VERGE_COGNEE_ENABLED=true`` **or** when API key + base URL
    are present (auto). Explicit ``false`` always disables.
    """
    if asset.status != DocumentStatus.READY:
        return {"degraded": True, "reason": "not-ready"}
    text = store.texts.get(asset.document_id, "")
    if not text.strip():
        return {"degraded": True, "reason": "empty-text"}
    try:
        from verge_memory.client import cognee_enabled_from_env

        env = dict(os.environ)
        if not cognee_enabled_from_env(env):
            return {"degraded": True, "reason": "cognee-disabled"}
        client = CogneeClient.from_env(env)
        if not client.settings.ready:
            return {
                "degraded": True,
                "reason": client.settings.missing_reason() or "cognee-not-ready",
            }
        # Docs: add alone is not searchable — cognify builds the graph.
        result = ingest_and_cognify(
            client, dataset_name(env), asset.title, text, ensure_dataset=True
        )
        return {
            "degraded": bool(getattr(result, "degraded", False)),
            "reason": getattr(result, "reason", "") or "",
            "statusCode": getattr(result, "status_code", None),
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
