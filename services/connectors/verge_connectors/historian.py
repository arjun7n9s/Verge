"""Historian connectors — process data sources (spec §14 Phase 4).

A historian speaks *tags* (e.g. ``FIC-101.PV``); Verge speaks *sensors*. The tag
map — a commissioning artifact — bridges the two. Because a historian tag is
exactly an OPC-UA node in this respect, the CSV historian reuses the edge
plane's :func:`verge_edge.normalize_opcua` to turn each row into a canonical
reading, so there is one normalization path, not two.

The two proprietary connectors (OSIsoft PI Web API, Honeywell PHD) are the real
integration points; they need a live network + credentials and therefore default
to **degraded** on the dev/air-gapped box rather than pretending to connect.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from verge_edge import NormalizationError, normalize_opcua

from .base import Connector, ConnectorResult, degraded

SAMPLES_DIR = Path(__file__).parent / "samples"


def load_tag_map(path: str | Path) -> dict[str, dict]:
    """Load a historian tag -> {sensorId, kind, unit, zoneId} mapping (JSON)."""
    # utf-8-sig tolerates a BOM (common in Windows/Excel exports).
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _parse_ts(ts: str | None) -> datetime | None:
    """Parse an ISO timestamp to an aware datetime (naive => UTC); None if unparseable."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


class CsvHistorianConnector:
    """Read ``tag,ts,value`` rows from a historian CSV export into readings.

    Rows whose tag is not in the tag map are skipped and counted — never mapped
    to a guessed sensor (P3).
    """

    name = "csv-historian"

    def __init__(self, csv_path: str | Path, tag_map: Mapping[str, dict]) -> None:
        self._csv = Path(csv_path)
        self._map = dict(tag_map)

    def pull(self, since: str | None = None) -> ConnectorResult:
        if not self._csv.exists():
            return degraded(self.name, f"historian export not found: {self._csv}")
        since_dt = _parse_ts(since)
        events: list[dict] = []
        skipped = 0
        rows = csv.DictReader(self._csv.read_text(encoding="utf-8-sig").splitlines())
        for row in rows:
            tag = (row.get("tag") or "").strip()
            ts = (row.get("ts") or "").strip() or None
            raw_value = row.get("value")
            if not tag or raw_value in (None, ""):
                skipped += 1
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                skipped += 1
                continue
            # Reject non-finite readings — NaN/inf silently defeat threshold rules
            # on a safety product; drop and count, never emit poison data (P4).
            if not math.isfinite(value):
                skipped += 1
                continue
            try:
                event = normalize_opcua(tag, value, ts=ts, mapping=self._map)
            except NormalizationError:
                skipped += 1
                continue
            # Compare instants, not strings: ISO offsets make lexical order wrong.
            if since_dt is not None:
                ev_dt = _parse_ts(event["ts"])
                if ev_dt is not None and ev_dt < since_dt:
                    continue
            events.append(event)
        return ConnectorResult(source=self.name, events=events, skipped=skipped)


class _NetworkHistorian:
    """Shared degraded behaviour for network-backed historians (no live host here)."""

    name = "historian"
    _url_env = ""
    _label = "historian"

    def __init__(self, env: Mapping[str, str]) -> None:
        self._env = env

    def pull(self, since: str | None = None) -> ConnectorResult:
        url = self._env.get(self._url_env)
        if not url:
            return degraded(self.name, f"{self._label} not configured ({self._url_env} unset)")
        # A live install wires the vendor SDK/HTTP here. On the dev/air-gapped box
        # there is no host to reach, so we degrade rather than fabricate readings.
        return degraded(self.name, f"{self._label} configured but unreachable from this host")


class PiWebApiConnector(_NetworkHistorian):
    """OSIsoft PI Web API historian (spec §15 Q1)."""

    name = "pi"
    _url_env = "VERGE_PI_WEB_API_URL"
    _label = "OSIsoft PI Web API"


class HoneywellPhdConnector(_NetworkHistorian):
    """Honeywell PHD historian (spec §15 Q1)."""

    name = "phd"
    _url_env = "VERGE_PHD_URL"
    _label = "Honeywell PHD"


def demo_historian() -> Connector:
    return CsvHistorianConnector(
        SAMPLES_DIR / "historian-readings.csv",
        load_tag_map(SAMPLES_DIR / "historian-tagmap.json"),
    )
