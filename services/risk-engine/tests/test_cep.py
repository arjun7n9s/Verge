"""CEP sliding-window pattern tests."""

from __future__ import annotations

from verge_risk.cep import CepState, evaluate_cep


def test_cep_multi_gas_rising():
    state = CepState(window_min=10.0)
    base = "2025-01-01T06:40:00+00:00"
    events = [
        {"type": "reading", "ts": base, "zoneId": "B-04", "sensorId": "LEL-04",
         "kind": "gas-lel", "value": 40.0},
        {"type": "reading", "ts": "2025-01-01T06:41:00+00:00", "zoneId": "B-04",
         "sensorId": "LEL-04", "kind": "gas-lel", "value": 55.0},
        {"type": "reading", "ts": "2025-01-01T06:42:00+00:00", "zoneId": "B-04",
         "sensorId": "LEL-05", "kind": "gas-lel", "value": 30.0},
        {"type": "reading", "ts": "2025-01-01T06:43:00+00:00", "zoneId": "B-04",
         "sensorId": "LEL-05", "kind": "gas-lel", "value": 48.0},
    ]
    findings = []
    for e in events:
        findings.extend(evaluate_cep(state, e))
    assert findings
    assert "CEP" in findings[-1].title


def test_cep_drops_late_events_beyond_max_lateness():
    state = CepState(window_min=10.0, max_lateness_min=1.0)
    on_time = {"type": "reading", "ts": "2025-01-01T06:40:00+00:00", "zoneId": "B-04",
               "sensorId": "LEL-04", "kind": "gas-lel", "value": 40.0}
    late = {"type": "reading", "ts": "2025-01-01T06:37:00+00:00", "zoneId": "B-04",
            "sensorId": "LEL-04", "kind": "gas-lel", "value": 40.0}
    evaluate_cep(state, on_time)
    findings = evaluate_cep(state, late)
    assert findings == []
    assert state.late_dropped == 1
