"""Lifecycle: legal paths flow, illegal ones raise, reasons are enforced."""

from datetime import datetime, timezone

import pytest

from verge_schema.enums import FindingState as S
from verge_schema.lifecycle import IllegalTransition, can_transition, is_terminal, transition

TS = datetime(2025, 1, 13, 6, 44, tzinfo=timezone.utc)


def test_happy_path_new_to_closed() -> None:
    path = [S.NEW, S.ACKNOWLEDGED, S.IN_PROGRESS, S.RESOLVED, S.CLOSED]
    for frm, to in zip(path, path[1:]):
        assert can_transition(frm, to)
        ev = transition("F-1", frm, to, actor="maya", timestamp=TS)
        assert ev.to_state == to


def test_illegal_transition_raises() -> None:
    with pytest.raises(IllegalTransition):
        transition("F-1", S.NEW, S.CLOSED, actor="maya", timestamp=TS)


def test_snooze_requires_reason() -> None:
    with pytest.raises(IllegalTransition):
        transition("F-1", S.ACKNOWLEDGED, S.SNOOZED, actor="maya", timestamp=TS)
    ev = transition("F-1", S.ACKNOWLEDGED, S.SNOOZED, actor="maya", timestamp=TS,
                    reason_code="awaiting-shift-engineer-review")
    assert ev.reason_code == "awaiting-shift-engineer-review"


def test_suppress_requires_reason_and_is_reversible() -> None:
    with pytest.raises(IllegalTransition):
        transition("F-1", S.IN_PROGRESS, S.SUPPRESSED_AS_DUPLICATE, actor="maya", timestamp=TS)
    assert can_transition(S.SUPPRESSED_AS_DUPLICATE, S.REOPENED)


def test_closed_can_reopen() -> None:
    assert can_transition(S.CLOSED, S.REOPENED)
    assert is_terminal(S.CLOSED) is True
    assert is_terminal(S.RESOLVED) is False
