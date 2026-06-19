"""Diagnostics support for Pyrovigil."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    anepc_data = data["anepc"].data
    fire_risk_data = data["fire_risk"].data
    warnings_data = data["warnings"].data

    # Round coordinates for privacy
    config = dict(entry.data)
    if "latitude" in config:
        config["latitude"] = round(config["latitude"], 1)
    if "longitude" in config:
        config["longitude"] = round(config["longitude"], 1)

    return {
        "config": config,
        "options": dict(entry.options),
        "anepc": {
            "fire_count": len(anepc_data.fires),
            "total_personnel": anepc_data.total_personnel,
            "total_ground_vehicles": anepc_data.total_ground_vehicles,
            "total_aircraft": anepc_data.total_aircraft,
            "coordinator_last_update_success": data["anepc"].last_update_success,
        },
        "fire_risk": {
            "dico_code": fire_risk_data.dico_code,
            "today_rcm": fire_risk_data.today.rcm if fire_risk_data.today else None,
            "tomorrow_rcm": fire_risk_data.tomorrow.rcm if fire_risk_data.tomorrow else None,
            "forecast_date": fire_risk_data.forecast_date,
            "coordinator_last_update_success": data["fire_risk"].last_update_success,
        },
        "warnings": {
            "warning_count": len(warnings_data.warnings),
            "highest_level": warnings_data.highest_level,
            "coordinator_last_update_success": data["warnings"].last_update_success,
        },
    }
