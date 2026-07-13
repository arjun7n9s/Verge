"""The simulator must emit a coherent, ingestible stream with the injected gap."""

from verge_sims import vizag_like


def test_emits_permit_shift_and_readings() -> None:
    events = list(vizag_like().events())
    kinds = {e["type"] for e in events}
    assert {"permit", "shift", "reading"} <= kinds
    assert sum(1 for e in events if e["type"] == "shift") == 2  # start + end


def test_lel_rises_and_eventually_high() -> None:
    lel = [e["value"] for e in vizag_like().events()
           if e["type"] == "reading" and e["sensorId"] == "LEL-04"]
    assert lel[0] < lel[-1]
    assert lel[-1] >= 95.0  # approaching the 100 %LEL alarm


def test_injected_stale_gap_present() -> None:
    # LEL-04 emits nothing during the 06:38-06:42 stale window (minutes 8-12)
    lel_count = sum(1 for e in vizag_like().events()
                    if e["type"] == "reading" and e["sensorId"] == "LEL-04")
    co_count = sum(1 for e in vizag_like().events()
                   if e["type"] == "reading" and e["sensorId"] == "CO-04")
    assert lel_count < co_count  # the gap means fewer LEL readings than CO


def test_worker_fixes_emitted_and_deterministic() -> None:
    events = list(vizag_like().events())
    fixes = [e for e in events if e["type"] == "worker-location"]
    assert fixes, "vizag-like must emit worker-location fixes"
    # Deterministic: two runs produce identical streams (replayable, P5).
    assert fixes == [e for e in vizag_like().events() if e["type"] == "worker-location"]
    # The welder converges on B-04 (the hot-work zone) by minute 10.
    w101 = [e for e in fixes if e["workerId"] == "W-101"]
    assert w101[0]["zoneId"] == "B-02"
    assert w101[-1]["zoneId"] == "B-04"
    # Every fix passes the worker-location contract.
    from verge_contracts import ContractRegistry

    reg = ContractRegistry()
    assert all(reg.validate_event(e).valid for e in fixes)
