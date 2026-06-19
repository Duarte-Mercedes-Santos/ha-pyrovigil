"""Geographic mapping utilities for Pyrovigil."""

from __future__ import annotations

import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the distance in km between two points on Earth using the Haversine formula."""
    r = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_dico(lat: float, lon: float, rcm_data: dict) -> str | None:
    """Find the nearest DICO municipality code from RCM data.

    Args:
        lat: User's latitude.
        lon: User's longitude.
        rcm_data: Parsed RCM JSON with "local" key containing DICO entries.

    Returns:
        The DICO code of the nearest municipality, or None if no data.
    """
    local = rcm_data.get("local", {})
    if not local:
        return None

    best_dico = None
    best_dist = float("inf")

    for dico_code, entry in local.items():
        entry_lat = entry.get("latitude")
        entry_lon = entry.get("longitude")
        if entry_lat is None or entry_lon is None:
            continue
        dist = haversine(lat, lon, float(entry_lat), float(entry_lon))
        if dist < best_dist:
            best_dist = dist
            best_dico = dico_code

    return best_dico


def find_nearest_area_aviso(lat: float, lon: float) -> str | None:
    """Find the nearest IPMA warning area code for the given coordinates.

    Returns:
        The area code string (e.g. "LSB"), or None if mapping is empty.
    """
    if not AREA_AVISO_COORDS:
        return None

    best_code = None
    best_dist = float("inf")

    for code, (_, area_lat, area_lon) in AREA_AVISO_COORDS.items():
        dist = haversine(lat, lon, area_lat, area_lon)
        if dist < best_dist:
            best_dist = dist
            best_code = code

    return best_code


# IPMA warning area codes mapped to (district_name, latitude, longitude).
# These are approximate district center coordinates.
AREA_AVISO_COORDS: dict[str, tuple[str, float, float]] = {
    "AVR": ("Aveiro", 40.64, -8.65),
    "BJA": ("Beja", 38.01, -7.86),
    "BRG": ("Braga", 41.55, -8.43),
    "BGC": ("Bragança", 41.81, -6.76),
    "CTB": ("Castelo Branco", 39.82, -7.49),
    "CBR": ("Coimbra", 40.21, -8.43),
    "EVR": ("Évora", 38.57, -7.91),
    "FAR": ("Faro", 37.02, -7.93),
    "GRD": ("Guarda", 40.54, -7.27),
    "LRA": ("Leiria", 39.74, -8.81),
    "LSB": ("Lisboa", 38.72, -9.14),
    "PTL": ("Portalegre", 39.30, -7.43),
    "PRT": ("Porto", 41.15, -8.61),
    "STM": ("Santarém", 39.24, -8.69),
    "STB": ("Setúbal", 38.52, -8.90),
    "VCT": ("Viana do Castelo", 41.69, -8.83),
    "VRL": ("Vila Real", 41.30, -7.74),
    "VSE": ("Viseu", 40.66, -7.91),
    "MCN": ("Madeira - Costa Norte", 32.75, -16.96),
    "MCS": ("Madeira - Costa Sul", 32.65, -16.92),
    "MRM": ("Madeira - Regiões Montanhosas", 32.72, -16.95),
    "MPS": ("Madeira - Porto Santo", 33.06, -16.34),
    "AOR": ("Açores - Grupo Oriental", 37.74, -25.67),
    "ACE": ("Açores - Grupo Central", 38.53, -28.53),
    "AOC": ("Açores - Grupo Ocidental", 39.52, -31.12),
}
