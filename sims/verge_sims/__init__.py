"""SCADA/MQTT plant simulators (spec §12 — replaces VesperGrid's Gazebo theater)."""

from .scenario import SCENARIOS, Scenario, SensorSpec, vizag_like

__all__ = ["SCENARIOS", "Scenario", "SensorSpec", "vizag_like"]
__version__ = "0.3.0"
