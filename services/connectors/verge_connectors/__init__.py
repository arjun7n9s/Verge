"""Integration hub — connectors that emit canonical Verge events (spec §14 Phase 4).

Historians (OSIsoft PI, Honeywell PHD), CMMS (SAP PM, Maximo), and VMS
(Milestone). Real CSV adapters for historian + CMMS; proprietary connectors
degrade cleanly when no live system is reachable (P4).
"""

from .base import Connector, ConnectorResult, degraded
from .cmms import (
    CsvCmmsConnector,
    MaximoConnector,
    MilestoneVmsConnector,
    SapPmConnector,
    demo_cmms,
)
from .historian import (
    CsvHistorianConnector,
    HoneywellPhdConnector,
    PiWebApiConnector,
    demo_historian,
    load_tag_map,
)
from .registry import (
    CONNECTOR_NAMES,
    NullConnector,
    connector_from_env,
    get_connector,
)

__all__ = [
    "CONNECTOR_NAMES",
    "Connector",
    "ConnectorResult",
    "CsvCmmsConnector",
    "CsvHistorianConnector",
    "HoneywellPhdConnector",
    "MaximoConnector",
    "MilestoneVmsConnector",
    "NullConnector",
    "PiWebApiConnector",
    "SapPmConnector",
    "connector_from_env",
    "degraded",
    "demo_cmms",
    "demo_historian",
    "get_connector",
    "load_tag_map",
]
__version__ = "0.3.0"
