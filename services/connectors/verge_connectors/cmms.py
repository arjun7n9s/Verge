"""CMMS + VMS connectors (spec §14 Phase 4, §15 Q2/Q3).

The CMMS (SAP PM, Maximo, or paper) is the source of permit-to-work and
maintenance context; a paper-based plant needs the CSV path as its *first*
integration (spec §15 Q2). The VMS (Milestone, Genetec) supplies camera streams
the vision plane consumes.

The CSV CMMS connector is real and emits canonical ``permit`` events. The
proprietary CMMS/VMS connectors default to degraded on a host with no live
system, honestly reporting the integration point rather than faking permits.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from .base import Connector, ConnectorResult, degraded
from .historian import SAMPLES_DIR, _parse_ts


def _iso_utc(raw: str | None) -> str | None:
    """Coerce a permit timestamp to tz-aware UTC ISO (edge-plane convention).

    Real CMMS exports are often naive local ISO; downstream events must be
    tz-aware so the stream runner can order permits against readings.
    """
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


class CsvCmmsConnector:
    """Read permit rows from a CMMS export into canonical ``permit`` events.

    CSV columns: ``permitId,kind,zoneId,equipmentId,validFrom,validTo``.
    """

    name = "csv-cmms"

    def __init__(self, csv_path: str | Path) -> None:
        self._csv = Path(csv_path)

    def pull(self, since: str | None = None) -> ConnectorResult:
        if not self._csv.exists():
            return degraded(self.name, f"CMMS export not found: {self._csv}")
        since_dt = _parse_ts(since)
        events: list[dict] = []
        skipped = 0
        rows = csv.DictReader(self._csv.read_text(encoding="utf-8-sig").splitlines())
        for row in rows:
            permit_id = (row.get("permitId") or "").strip()
            kind = (row.get("kind") or "").strip()
            zone = (row.get("zoneId") or "").strip()
            if not (permit_id and kind and zone):
                skipped += 1
                continue
            valid_from = _iso_utc((row.get("validFrom") or "").strip())
            valid_to = _iso_utc((row.get("validTo") or "").strip())
            # Canonical events carry a top-level tz-aware `ts`; a permit's event
            # time is when it becomes active. No validity window == malformed.
            ts = valid_from or valid_to
            if ts is None:
                skipped += 1
                continue
            # Window on the permit's end (compare instants, not ISO strings). An
            # open-ended permit (no validTo) is never filtered out — a still-open
            # permit is always in-window regardless of `since`.
            if since_dt is not None and valid_to is not None:
                vt = _parse_ts(valid_to)
                if vt is not None and vt < since_dt:
                    continue
            event = {
                "type": "permit",
                "ts": ts,
                "permitId": permit_id,
                "kind": kind,
                "zoneId": zone,
                "validFrom": valid_from,
                "validTo": valid_to,
            }
            equipment = (row.get("equipmentId") or "").strip()
            if equipment:
                event["equipmentId"] = equipment
            events.append(event)
        return ConnectorResult(source=self.name, events=events, skipped=skipped)


class _NetworkSystem:
    """Shared degraded behaviour for network-backed CMMS/VMS systems."""

    name = "system"
    _url_env = ""
    _label = "system"

    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env

    def pull(self, since: str | None = None) -> ConnectorResult:
        if not self._env.get(self._url_env):
            return degraded(self.name, f"{self._label} not configured ({self._url_env} unset)")
        return degraded(self.name, f"{self._label} configured but unreachable from this host")


class MaximoConnector(_NetworkSystem):
    name = "maximo"
    _url_env = "VERGE_MAXIMO_URL"
    _label = "IBM Maximo CMMS"


class SapPmConnector(_NetworkSystem):
    name = "sap-pm"
    _url_env = "VERGE_SAP_PM_URL"
    _label = "SAP PM CMMS"


class MilestoneVmsConnector(_NetworkSystem):
    """Milestone VMS — supplies camera streams to the vision plane (§15 Q3)."""

    name = "milestone"
    _url_env = "VERGE_MILESTONE_URL"
    _label = "Milestone VMS"


def demo_cmms() -> Connector:
    return CsvCmmsConnector(SAMPLES_DIR / "cmms-permits.csv")
