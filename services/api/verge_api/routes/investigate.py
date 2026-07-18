"""Finding investigation — advisory orchestrator route (Phase 2.5).

Binds read-only tools over live app state, runs specialists → merge → validate.
Advisory only (P8). Every response carries specialist digests, tool evidence,
and a deterministic validation report. Audit-chained.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from verge_agents import Tool, ToolRegistry, TwinCatalog, investigate
from verge_compliance.clauses import load_clauses

router = APIRouter(tags=["investigate"])

_STR = {"type": "string"}


def _build_tools(app, finding) -> ToolRegistry:
    store = app.state.store
    plant = app.state.plant
    readings = app.state.readings
    occupancy = app.state.occupancy
    permits = app.state.permits
    thresholds = getattr(app.state, "sensor_thresholds", {})
    docintel = getattr(app.state, "docintel", None)

    def get_finding(finding_id: str = "") -> dict:
        f = store.get_finding(finding_id or finding.finding_id)
        if f is None:
            return {"error": "finding not found"}
        return f.model_dump(by_alias=True, mode="json")

    def get_zone_context(zone_id: str = "") -> dict:
        zid = zone_id or finding.zone_id
        zone = plant.zones.get(zid)
        return {
            "zoneId": zid,
            "name": zone.name if zone else "(unknown zone)",
            "adjacentZones": sorted(plant.adjacency().get(zid, set())),
            "sensors": [
                {"sensorId": s.sensor_id, "kind": s.kind, "unit": s.unit,
                 "threshold": s.threshold}
                for s in plant.sensors_in_zone(zid)
            ],
            "equipment": [
                {"equipmentId": e.equipment_id, "name": e.name, "kind": e.kind}
                for e in plant.equipment.values() if e.zone_id == zid
            ],
            "workersPresent": len(occupancy.zone_roster().get(zid, [])),
        }

    def get_recent_telemetry(finding_id: str = "") -> dict:
        f = store.get_finding(finding_id or finding.finding_id) or finding
        data = readings.series_for_finding(f, thresholds=thresholds)
        for series in data.get("series", []):
            pts = series.get("points", [])
            if len(pts) > 24:
                series["points"] = pts[-24:]
                series["trimmedTo"] = 24
        return data

    def get_active_permits(zone_id: str = "") -> list[dict]:
        zid = zone_id or finding.zone_id
        nearby = {zid} | set(plant.adjacency().get(zid, set()))
        return [
            {
                "permitId": p.permit_id, "kind": p.kind, "zoneId": p.zone_id,
                "equipmentId": p.equipment_id,
                "validTo": p.valid_to.isoformat(),
                "inFindingZone": p.zone_id == zid,
            }
            for p in permits.list_active()
            if p.zone_id in nearby
        ]

    def get_equipment_graph(zone_id: str = "") -> dict:
        zid = zone_id or finding.zone_id
        nearby = {zid} | set(plant.adjacency().get(zid, set()))
        active = [p for p in permits.list_active() if p.zone_id in nearby]
        nodes = []
        for e in plant.equipment.values():
            if e.zone_id not in nearby:
                continue
            touching = [p.permit_id for p in active if p.equipment_id == e.equipment_id]
            nodes.append({
                "equipmentId": e.equipment_id, "name": e.name, "kind": e.kind,
                "zoneId": e.zone_id, "activePermits": touching,
                "riskNote": "permit-covered work on this equipment" if touching else None,
            })
        return {"zoneId": zid, "nearbyZones": sorted(nearby), "equipment": nodes}

    def search_incident_memory(query: str = "") -> dict:
        try:
            from verge_memory import query_memory
            return query_memory(
                query or f"incidents similar to: {finding.title}",
                finding=finding,
                provider=app.state.llm,
                env=dict(os.environ),
            )
        except Exception as exc:
            return {"answer": "", "citations": [], "degraded": True,
                    "reason": f"memory unavailable: {type(exc).__name__}"}

    def get_compliance_clauses(zone_id: str = "") -> list[dict]:
        title = finding.title.lower()
        lineage = " ".join(finding.lineage).lower()
        haystack = f"{title} {lineage}"
        scored = []
        for c in load_clauses():
            words = [w for w in c.capability.replace("-", " ").split() if len(w) > 3]
            if any(w in haystack for w in words):
                scored.append({"clauseId": c.id, "standard": c.standard,
                               "title": c.title, "requirement": c.requirement})
        return scored[:8]

    def search_plant_docs(query: str = "") -> dict:
        """Local DocIntel chunk retrieval for the Knowledge Specialist."""
        if docintel is None:
            return {"citations": [], "degraded": True, "reason": "docintel-unavailable"}
        q = (query or finding.title).lower().split()
        scored: list[tuple[int, dict]] = []
        for doc_id, chunks in getattr(docintel, "chunks", {}).items():
            doc = getattr(docintel, "documents", {}).get(doc_id)
            for ch in chunks:
                text = ch.text.lower()
                score = sum(1 for tok in q if tok in text)
                if score:
                    scored.append((
                        score,
                        {
                            "documentId": doc_id,
                            "title": doc.title if doc else doc_id,
                            "chunkId": ch.chunk_id,
                            "page": ch.page,
                            "excerpt": ch.text[:400],
                            "score": score,
                        },
                    ))
        scored.sort(key=lambda x: x[0], reverse=True)
        citations = [row for _, row in scored[:6]]
        return {
            "citations": citations,
            "degraded": len(citations) == 0,
            "reason": "" if citations else "no-matching-chunks",
        }

    def query_zone_graph(zone_id: str = "") -> dict:
        """GraphRAG: local twin + Neo4j coverage + doc/equipment multi-hops."""
        zid = zone_id or finding.zone_id
        local = get_equipment_graph(zid)
        local_hops = [
            {"from": zid, "rel": "ADJACENT", "to": z}
            for z in local.get("nearbyZones", []) if z != zid
        ]
        neo: dict = {"degraded": True, "reason": "skipped"}
        doc_hops: dict = {"degraded": True, "hops": [], "reason": "skipped"}
        equip_hops: dict = {"degraded": True, "hops": [], "reason": "skipped"}
        try:
            from verge_twin.neo4j_query import (
                zone_document_hops,
                zone_equipment_document_hops,
                zone_graph_coverage,
            )
            neo = zone_graph_coverage(zid, env=dict(os.environ))
            doc_hops = zone_document_hops(zid, env=dict(os.environ))
            equip_hops = zone_equipment_document_hops(zid, env=dict(os.environ))
        except Exception as exc:
            neo = {"degraded": True, "reason": type(exc).__name__}
            doc_hops = {"degraded": True, "hops": [], "reason": type(exc).__name__}
            equip_hops = {"degraded": True, "hops": [], "reason": type(exc).__name__}
        merged = local_hops + list(doc_hops.get("hops") or []) + list(
            equip_hops.get("hops") or []
        )
        return {
            "zoneId": zid,
            "localTwin": local,
            "neo4j": neo,
            "documentHops": doc_hops,
            "equipmentDocumentHops": equip_hops,
            "hops": merged,
        }

    def get_recent_voice_events(zone_id: str = "") -> dict:
        zid = zone_id or finding.zone_id
        try:
            from ..voice_events import list_voice_events
            events = list_voice_events(app.state, limit=20)
        except Exception as exc:
            return {"events": [], "degraded": True, "reason": type(exc).__name__}
        rows = []
        for e in events:
            dump = e.model_dump(by_alias=True, mode="json") if hasattr(e, "model_dump") else dict(e)
            ez = dump.get("zoneId") or dump.get("zone_id")
            if ez and ez != zid and ez not in plant.adjacency().get(zid, set()):
                continue
            rows.append({
                "eventId": dump.get("eventId") or dump.get("event_id"),
                "transcript": (dump.get("transcript") or dump.get("englishTranscript") or "")[:300],
                "transcriptOriginal": (dump.get("transcriptOriginal") or "")[:200] or None,
                "languagesDetected": dump.get("languagesDetected") or [],
                "zoneId": ez,
                "source": dump.get("source"),
                "hazards": dump.get("hazards") or [],
            })
        return {"zoneId": zid, "events": rows[:8], "count": len(rows)}

    def get_recent_vision_events(zone_id: str = "") -> dict:
        zid = zone_id or finding.zone_id
        try:
            from ..vision_events import list_vision_detections
            dets = list_vision_detections(app.state, limit=20)
        except Exception as exc:
            return {"detections": [], "degraded": True, "reason": type(exc).__name__}
        rows = []
        for d in dets:
            dump = d.model_dump(by_alias=True, mode="json") if hasattr(d, "model_dump") else dict(d)
            ez = dump.get("zoneId") or dump.get("zone_id")
            if ez and ez != zid:
                continue
            rows.append({
                "label": dump.get("label") or dump.get("className"),
                "zoneId": ez,
                "cameraId": dump.get("cameraId"),
                "confidence": dump.get("confidence"),
            })
        return {"zoneId": zid, "detections": rows[:8], "count": len(rows)}

    return ToolRegistry([
        Tool("get_finding", "Full details of a risk finding by id.",
             get_finding, {"type": "object", "properties": {"finding_id": _STR}}),
        Tool("get_zone_context",
             "Zone name, adjacency, sensors, equipment, and worker presence.",
             get_zone_context, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("get_recent_telemetry",
             "Recent time-series for the sensors behind a finding, with thresholds.",
             get_recent_telemetry, {"type": "object", "properties": {"finding_id": _STR}}),
        Tool("get_active_permits",
             "Active work permits in a zone and its adjacent zones.",
             get_active_permits, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("get_equipment_graph",
             "Equipment-permit-risk relationships around a zone (local twin graph).",
             get_equipment_graph, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("search_incident_memory",
             "Search organizational memory: similar incidents, near-misses, OISD guidance.",
             search_incident_memory,
             {"type": "object", "properties": {"query": _STR}}),
        Tool("search_plant_docs",
             "Search ingested plant SOPs/manuals (DocIntel chunks) with citations.",
             search_plant_docs, {"type": "object", "properties": {"query": _STR}}),
        Tool("query_zone_graph",
             "Multi-hop zone graph: local twin adjacency/equipment + Neo4j coverage.",
             query_zone_graph, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("get_compliance_clauses",
             "Regulatory clauses (OISD/Factory Act) relevant to this finding.",
             get_compliance_clauses, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("get_recent_voice_events",
             "Recent radio/voice events (English ops text) near the finding zone.",
             get_recent_voice_events, {"type": "object", "properties": {"zone_id": _STR}}),
        Tool("get_recent_vision_events",
             "Recent vision detections near the finding zone.",
             get_recent_vision_events, {"type": "object", "properties": {"zone_id": _STR}}),
    ])


@router.post("/findings/{finding_id}/investigate")
def investigate_finding(finding_id: str, request: Request) -> dict:
    app = request.app
    store = app.state.store
    finding = store.get_finding(finding_id)
    if finding is None:
        raise HTTPException(404, "finding not found")

    tools = _build_tools(app, finding)
    catalog = TwinCatalog.from_plant(app.state.plant)
    model = os.environ.get("VERGE_LLM_AGENT_MODEL") or None
    result = investigate(
        app.state.llm,
        finding_id=finding.finding_id,
        zone_id=finding.zone_id,
        title=finding.title,
        tools=tools,
        model=model,
        catalog=catalog,
    )
    store.audit_append(
        actor="advisory-orchestrator",
        kind="investigation-run",
        payload={
            "findingId": finding_id,
            "degraded": result["degraded"],
            "toolCalls": [s["tool"] for s in result["evidence"]],
            "specialists": [s["name"] for s in result.get("specialists") or []],
            "validationOk": (result.get("validation") or {}).get("ok"),
            "inventedTags": (result.get("validation") or {}).get("inventedTags") or [],
            "model": result["model"],
            "orchestrator": result.get("orchestrator"),
        },
        timestamp=datetime.now(UTC),
    )
    return result
