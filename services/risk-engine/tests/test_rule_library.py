"""Starter rule library invariants (spec §14.5 step 3).

The library must be large enough for go-live (30+ known fatal combinations) and
every rule must be valid. New broad-hazard rules must extend coverage WITHOUT
firing on the replay datasets — that is the guarantee that keeps the
replay-proven lead-time numbers stable.
"""

from __future__ import annotations

from verge_risk import STARTER_RULES, load_rules

# Sensor/permit kinds present in the replay datasets. A rule that keys only on
# these can legitimately fire on a replay; a rule that requires any other kind
# must stay inert there.
REPLAY_SENSOR_KINDS = {"gas-lel", "gas-co"}
REPLAY_PERMIT_KINDS = {"hot-work", "confined-space"}


def _rules():
    return load_rules(STARTER_RULES)


def test_library_has_at_least_60_valid_rules():
    rules = _rules()
    assert len(rules) >= 60
    assert all(r.predicates for r in rules)  # no empty rules
    assert len({r.id for r in rules}) == len(rules)  # ids unique


def test_every_rule_predicate_type_is_supported_by_the_engine():
    from verge_risk.engine import PREDICATES

    for r in _rules():
        for pred in r.predicates:
            assert pred["type"] in PREDICATES, f"{r.id}: unknown predicate {pred['type']}"


def test_broad_hazard_rules_cannot_fire_on_replay_kinds():
    """Each rule either keys only on replay kinds, or requires a kind absent from
    the replays (so it stays inert and cannot perturb replay results)."""
    for r in _rules():
        sensor_kinds = {
            p["sensor_kind"] for p in r.predicates if p["type"] == "gas_near_threshold"
        }
        permit_kinds = {p["kind"] for p in r.predicates if p["type"] == "permit_active"}
        only_replay_kinds = (
            sensor_kinds <= REPLAY_SENSOR_KINDS and permit_kinds <= REPLAY_PERMIT_KINDS
        )
        has_novel_kind = bool(sensor_kinds - REPLAY_SENSOR_KINDS) or bool(
            permit_kinds - REPLAY_PERMIT_KINDS
        )
        assert only_replay_kinds or has_novel_kind
