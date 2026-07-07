"""OPC-UA runner tests — degradation without asyncua."""

from __future__ import annotations

from verge_edge.opcua_runner import main


def test_opcua_degrades_without_endpoint(capsys) -> None:
    rc = main(["--map", "{}", "--endpoint", ""])
    assert rc == 0
    assert "degraded" in capsys.readouterr().err.lower()


def test_opcua_degrades_without_node_map(capsys) -> None:
    rc = main(["--endpoint", "opc.tcp://localhost:4840", "--map", "{}"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "empty node map" in err.lower() or "degraded" in err.lower()
