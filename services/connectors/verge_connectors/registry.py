"""Connector registry + env selection for the integration hub."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from .base import Connector, ConnectorResult, degraded
from .cmms import (
    CsvCmmsConnector,
    MaximoConnector,
    MilestoneVmsConnector,
    SapPmConnector,
)
from .historian import (
    CsvHistorianConnector,
    HoneywellPhdConnector,
    PiWebApiConnector,
    load_tag_map,
)

# Names a plant can select via VERGE_CONNECTOR (or the CLI --connector flag).
CONNECTOR_NAMES = (
    "csv-historian",
    "csv-cmms",
    "pi",
    "phd",
    "maximo",
    "sap-pm",
    "milestone",
)


class NullConnector:
    """Placeholder when nothing is configured — always degraded (P4)."""

    name = "none"

    def pull(self, since: str | None = None) -> ConnectorResult:
        return degraded(self.name, "no connector configured (set VERGE_CONNECTOR)")


def _csv_historian(env: Mapping[str, str]) -> Connector:
    csv_path = env.get("VERGE_HISTORIAN_CSV")
    tagmap_path = env.get("VERGE_HISTORIAN_TAGMAP")
    if not csv_path or not tagmap_path or not Path(tagmap_path).exists():
        return NullConnector()
    return CsvHistorianConnector(csv_path, load_tag_map(tagmap_path))


def get_connector(name: str, env: Mapping[str, str] | None = None) -> Connector:
    """Build a connector by name, wiring it from the environment."""
    env = env if env is not None else os.environ
    if name == "csv-historian":
        return _csv_historian(env)
    if name == "csv-cmms":
        path = env.get("VERGE_CMMS_CSV")
        return CsvCmmsConnector(path) if path else NullConnector()
    if name == "pi":
        return PiWebApiConnector(env)
    if name == "phd":
        return HoneywellPhdConnector(env)
    if name == "maximo":
        return MaximoConnector(env)
    if name == "sap-pm":
        return SapPmConnector(env)
    if name == "milestone":
        return MilestoneVmsConnector(env)
    return NullConnector()


def connector_from_env(env: Mapping[str, str] | None = None) -> Connector:
    """Select the connector named by ``VERGE_CONNECTOR`` (degraded null if unset)."""
    env = env if env is not None else os.environ
    return get_connector(env.get("VERGE_CONNECTOR", ""), env)
