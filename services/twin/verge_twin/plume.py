"""Gaussian plume exclusion zones (spec §5 Pillar 2/3).

Lightweight ALOHA-style downwind footprint for operator map overlays.
Full CFD is out of scope; this module is deterministic and GIS-ready.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class PlumeInput:
    source_x: float
    source_y: float
    release_rate_kg_s: float = 0.5
    wind_speed_m_s: float = 3.0
    wind_dir_deg: float = 270.0  # FROM direction (met convention)
    stability: str = "D"


def _sigma_y(x: float, stability: str) -> float:
    # Briggs rural parameters (simplified).
    coeffs = {
        "A": (0.22, 0.0001),
        "B": (0.16, 0.0001),
        "C": (0.11, 0.0001),
        "D": (0.08, 0.0001),
        "E": (0.06, 0.0001),
        "F": (0.04, 0.0001),
    }
    a, b = coeffs.get(stability, coeffs["D"])
    return a * x * (1 + b * x) ** 0.5


def _sigma_z(x: float, stability: str) -> float:
    coeffs = {
        "D": (0.06, 0.0015),
        "E": (0.03, 0.0003),
    }
    a, b = coeffs.get(stability, coeffs["D"])
    return a * x * (1 + b * x) ** 0.5


def exclusion_polygon(
    inp: PlumeInput,
    *,
    max_downwind_m: float = 400.0,
    step_m: float = 40.0,
    threshold_kg_m3: float = 1e-4,
) -> dict:
    """Return GeoJSON polygon approximating the ground-level exclusion cone."""
    # Wind blows TO direction (opposite of FROM).
    to_rad = math.radians((inp.wind_dir_deg + 180) % 360)
    cos_w, sin_w = math.cos(to_rad), math.sin(to_rad)

    ring: list[list[float]] = [[inp.source_x, inp.source_y]]
    x = step_m
    while x <= max_downwind_m:
        sig_y = max(_sigma_y(x, inp.stability), 1.0)
        sig_z = max(_sigma_z(x, inp.stability), 0.5)
        # Ground-level concentration ~ Q / (pi * u * sig_y * sig_z)
        u = max(inp.wind_speed_m_s, 0.5)
        conc = inp.release_rate_kg_s / (math.pi * u * sig_y * sig_z)
        half_width = sig_y if conc >= threshold_kg_m3 else 0.0
        cx = inp.source_x + x * cos_w
        cy = inp.source_y + x * sin_w
        px = cx + half_width * (-sin_w)
        py = cy + half_width * cos_w
        ring.append([px, py])
        x += step_m

    # Return path on the other side of centerline.
    x = max_downwind_m
    while x >= 0:
        sig_y = max(_sigma_y(x, inp.stability), 1.0)
        sig_z = max(_sigma_z(x, inp.stability), 0.5)
        u = max(inp.wind_speed_m_s, 0.5)
        conc = inp.release_rate_kg_s / (math.pi * u * sig_y * sig_z)
        half_width = sig_y if conc >= threshold_kg_m3 else 0.0
        cx = inp.source_x + x * cos_w
        cy = inp.source_y + x * sin_w
        px = cx - half_width * (-sin_w)
        py = cy - half_width * cos_w
        ring.append([px, py])
        x -= step_m

    ring.append([inp.source_x, inp.source_y])
    return {
        "type": "Feature",
        "properties": {
            "kind": "exclusion-plume",
            "windDirDeg": inp.wind_dir_deg,
            "windSpeedMs": inp.wind_speed_m_s,
            "releaseRateKgS": inp.release_rate_kg_s,
            "stability": inp.stability,
        },
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
