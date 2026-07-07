"""The 6-step commissioning workflow orchestration (spec §14.5)."""

from __future__ import annotations

import json

from verge_cli.cli import main
from verge_cli.commission import (
    DEMO_LAYOUT,
    DEMO_SENSORS,
    render_markdown,
    run_commission,
)


def test_demo_plant_commissions_ready():
    report = run_commission("vizag-coke-oven", DEMO_LAYOUT, DEMO_SENSORS)
    assert report.ready
    statuses = {c.step.split(" ")[0]: c.status for c in report.checks}
    assert statuses["1"] == "pass"  # layout clean
    assert statuses["2"] == "pass"  # all sensors mapped
    # Dry-run must catch the plant's own incident with a calibrated band.
    vizag = next(d for d in report.dry_run if d["incident"] == "vizag-2025-01")
    assert vizag["verge"]["alertTs"] is not None
    assert vizag["verge"]["bandCalibrated"] is True


def test_verge_beats_baselines_on_dry_run():
    report = run_commission("vizag-coke-oven", DEMO_LAYOUT, DEMO_SENSORS,
                            replays=["vizag-2025-01"])
    d = report.dry_run[0]
    # Verge alerts with real lead time; the fixed-threshold baseline does not.
    assert d["verge"]["leadMin"] > 10
    assert (d["b0"]["leadMin"] or 0) < d["verge"]["leadMin"]


def test_overlapping_layout_is_not_ready(tmp_path):
    doc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"zoneId": "Z1"},
             "geometry": {"type": "Polygon",
                          "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}},
            {"type": "Feature", "properties": {"zoneId": "Z2"},
             "geometry": {"type": "Polygon",
                          "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]]}},
        ],
    }
    p = tmp_path / "bad.geojson"
    p.write_text(json.dumps(doc), encoding="utf-8")
    report = run_commission("bad", p, None, replays=["vizag-2025-01"])
    assert not report.ready
    layout_check = next(c for c in report.checks if c.step.startswith("1"))
    assert layout_check.status == "fail"


def test_markdown_report_renders_all_steps():
    report = run_commission("vizag-coke-oven", DEMO_LAYOUT, DEMO_SENSORS,
                            replays=["vizag-2025-01"])
    md = render_markdown(report)
    assert "Commissioning report" in md
    assert "READY for 30-day shadow mode" in md
    for step in ("1 · layout", "2 · sensors", "3 · rules",
                 "4 · thresholds", "5 · dry-run", "6 · shadow"):
        assert step in md


def test_cli_commission_json_smoke(capsys):
    rc = main(["commission", "--replay", "vizag-2025-01", "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["plant"] == "vizag-coke-oven"
    assert payload["ready"] is True
    assert rc == 0


def test_cli_plant_import_smoke(capsys):
    rc = main(["plant", "import", "--file", str(DEMO_LAYOUT), "--name", "vizag-coke-oven"])
    out = capsys.readouterr().out
    assert "clean" in out
    assert rc == 0
