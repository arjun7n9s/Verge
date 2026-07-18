"""Neo4j GraphRAG helpers degrade without a live database."""

from __future__ import annotations

from verge_twin.neo4j_query import (
    zone_document_hops,
    zone_equipment_document_hops,
    zone_graph_coverage,
)


def test_zone_graph_coverage_degrades_unconfigured():
    out = zone_graph_coverage("B-04", env={})
    assert out["degraded"] is True
    assert out["reason"] == "neo4j not configured"


def test_zone_document_hops_degrades_unconfigured():
    out = zone_document_hops("B-04", env={})
    assert out["degraded"] is True
    assert out["hops"] == []
    assert out["reason"] == "neo4j not configured"


def test_zone_document_hops_returns_paths_when_driver_mocked(monkeypatch):
    class FakeResult:
        def __iter__(self):
            yield {
                "documentId": "DOC-1",
                "title": "Hot Work SOP",
                "mentionLabels": ["ZoneMention"],
                "mentionId": "zm-b04",
                "mentionNorm": "B-04",
                "mentionRaw": "B-04",
            }

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def run(self, cypher, **params):
            assert params["zone"] == "B-04"
            return FakeResult()

    class FakeDriver:
        def session(self):
            return FakeSession()

        def close(self):
            return None

    class FakeGraphDatabase:
        @staticmethod
        def driver(uri, auth=None):
            assert uri.startswith("bolt://")
            return FakeDriver()

    import sys
    import types

    fake_neo4j = types.ModuleType("neo4j")
    fake_neo4j.GraphDatabase = FakeGraphDatabase
    monkeypatch.setitem(sys.modules, "neo4j", fake_neo4j)

    out = zone_document_hops(
        "B-04",
        env={"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "x"},
    )
    assert out["degraded"] is False
    assert out["count"] == 1
    assert out["hops"][0]["from"] == "DOC-1"
    assert out["hops"][0]["path"][-1]["id"] == "B-04"


def test_zone_equipment_document_hops_degrades_unconfigured():
    out = zone_equipment_document_hops("B-04", env={})
    assert out["degraded"] is True
    assert out["hops"] == []
    assert out["reason"] == "neo4j not configured"


def test_zone_equipment_document_hops_mocked(monkeypatch):
    class FakeResult:
        def __iter__(self):
            yield {
                "zoneId": "B-04",
                "equipmentId": "EQ-OVEN-1",
                "documentId": "DOC-1",
                "title": "Hot Work SOP",
                "mentionId": "ent-oven",
                "mentionNorm": "EQ-OVEN-1",
                "mentionLabels": ["EquipmentTag"],
            }

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def run(self, cypher, **params):
            assert "HAS_SENSOR" in cypher
            assert params["zone"] == "B-04"
            return FakeResult()

    class FakeDriver:
        def session(self):
            return FakeSession()

        def close(self):
            return None

    class FakeGraphDatabase:
        @staticmethod
        def driver(uri, auth=None):
            return FakeDriver()

    import sys
    import types

    fake_neo4j = types.ModuleType("neo4j")
    fake_neo4j.GraphDatabase = FakeGraphDatabase
    monkeypatch.setitem(sys.modules, "neo4j", fake_neo4j)

    out = zone_equipment_document_hops(
        "B-04",
        env={"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "x"},
    )
    assert out["degraded"] is False
    assert out["count"] == 1
    assert out["hops"][0]["to"] == "EQ-OVEN-1"
    assert out["hops"][0]["path"][-1]["id"] == "B-04"
