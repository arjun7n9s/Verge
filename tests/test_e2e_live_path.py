"""End-to-end live path, in-process: sims -> risk-engine runner -> API ingest.

Exercises the same flow as the deployed pipeline (sims -> Redpanda ->
risk-engine -> api -> console) without needing a broker, so CI proves the
components actually compose, not just that each unit passes in isolation.
"""

from fastapi.testclient import TestClient
from verge_api.main import app
from verge_risk import STARTER_RULES, load_rules, run_stream
from verge_sims import vizag_like

RULES = load_rules(STARTER_RULES)


def test_sims_stream_produces_convergence_finding() -> None:
    findings = []
    emitted = run_stream(vizag_like().events(), RULES, findings.append)
    assert emitted == len(findings) >= 1

    conv = [f for f in findings if f.zone_id == "B-04" and "changeover" in f.title.lower()]
    assert conv, "the Vizag-style convergence must surface from the live sims stream"
    f = conv[0]
    assert f.confidence >= 0.8
    assert f.lead_time_band in {"NEAR", "IMMINENT"}
    assert f.lineage  # source lineage carried through (P3)


def test_dedup_emits_each_convergence_once() -> None:
    seen_titles = []
    run_stream(vizag_like().events(), RULES, lambda f: seen_titles.append((f.zone_id, f.title)))
    # no (zone, title) emitted twice across the whole stream
    assert len(seen_titles) == len(set(seen_titles))


def test_runner_findings_ingest_into_api_and_show_on_console() -> None:
    client = TestClient(app)
    before = len(client.get("/api/findings").json())

    def post(f):
        r = client.post("/api/findings", content=f.model_dump_json(by_alias=True),
                        headers={"Content-Type": "application/json"})
        assert r.status_code == 200

    run_stream(vizag_like().events(), RULES, post)

    after = client.get("/api/findings").json()
    assert len(after) > before
    # the ingested finding is now visible to the console feed
    assert any("changeover" in f["title"].lower() for f in after)
    # audit chain still verifies after ingestion (P6)
    assert client.get("/health").json()["audit"]["verified"] is True
