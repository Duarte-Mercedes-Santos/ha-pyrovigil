"""The Pyrovigil integration — Portuguese wildfire monitoring."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.components.persistent_notification import (
    async_create as pn_create,
)
from homeassistant.components.persistent_notification import (
    async_dismiss as pn_dismiss,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PyrovigilApiClient
from .const import (
    AQICN_UPDATE_INTERVAL,
    CONF_ADAPTIVE_POLLING,
    CONF_ALERT_SCAN_INTERVAL,
    CONF_AQICN_TOKEN,
    CONF_NASA_FIRMS_KEY,
    CONF_RADIUS,
    CONF_SAFETY_MARGIN,
    DEFAULT_ADAPTIVE_POLLING,
    DEFAULT_ALERT_SCAN_INTERVAL_MINUTES,
    DEFAULT_RADIUS_KM,
    DEFAULT_SAFETY_MARGIN_KM,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    FIRE_RISK_UPDATE_INTERVAL,
    FIRMS_UPDATE_INTERVAL,
    WEATHER_WARNING_UPDATE_INTERVAL,
)
from .coordinator import (
    AirQualityCoordinator,
    AnepcCoordinator,
    FireRiskCoordinator,
    FirmsCoordinator,
    WeatherWarningCoordinator,
    WindCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.GEO_LOCATION]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_LATITUDE): cv.latitude,
                vol.Required(CONF_LONGITUDE): cv.longitude,
                vol.Optional(CONF_RADIUS, default=DEFAULT_RADIUS_KM): cv.positive_int,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_MINUTES
                ): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Pyrovigil from YAML configuration."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=config[DOMAIN],
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pyrovigil from a config entry."""
    lat = entry.data[CONF_LATITUDE]
    lon = entry.data[CONF_LONGITUDE]
    radius = entry.options.get(CONF_RADIUS, entry.data.get(CONF_RADIUS, DEFAULT_RADIUS_KM))
    scan_minutes = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES),
    )
    safety_margin = entry.options.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN_KM)
    firms_key = entry.options.get(CONF_NASA_FIRMS_KEY, "")
    aqicn_token = entry.options.get(CONF_AQICN_TOKEN, "")
    adaptive = entry.options.get(CONF_ADAPTIVE_POLLING, DEFAULT_ADAPTIVE_POLLING)
    alert_minutes = entry.options.get(CONF_ALERT_SCAN_INTERVAL, DEFAULT_ALERT_SCAN_INTERVAL_MINUTES)

    session = async_get_clientsession(hass)
    client = PyrovigilApiClient(session)

    alert_interval = timedelta(minutes=alert_minutes) if adaptive else None
    anepc = AnepcCoordinator(
        hass,
        client,
        lat,
        lon,
        radius,
        timedelta(minutes=scan_minutes),
        safety_margin,
        alert_interval=alert_interval,
    )
    fire_risk = FireRiskCoordinator(hass, client, lat, lon, FIRE_RISK_UPDATE_INTERVAL)
    warnings = WeatherWarningCoordinator(hass, client, lat, lon, WEATHER_WARNING_UPDATE_INTERVAL)
    wind = WindCoordinator(hass, client, lat, lon, WEATHER_WARNING_UPDATE_INTERVAL)

    coordinators_to_refresh = [
        anepc.async_config_entry_first_refresh(),
        fire_risk.async_config_entry_first_refresh(),
        warnings.async_config_entry_first_refresh(),
        wind.async_config_entry_first_refresh(),
    ]

    firms = None
    if firms_key:
        firms = FirmsCoordinator(hass, client, lat, lon, firms_key, FIRMS_UPDATE_INTERVAL)
        coordinators_to_refresh.append(firms.async_config_entry_first_refresh())

    air_quality = None
    if aqicn_token:
        air_quality = AirQualityCoordinator(
            hass, client, lat, lon, aqicn_token, AQICN_UPDATE_INTERVAL
        )
        coordinators_to_refresh.append(air_quality.async_config_entry_first_refresh())

    await asyncio.gather(*coordinators_to_refresh)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "anepc": anepc,
        "fire_risk": fire_risk,
        "warnings": warnings,
        "wind": wind,
        "firms": firms,
        "air_quality": air_quality,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Persistent notification: show/dismiss based on fire_nearby state
    _setup_persistent_notification(hass, anepc, entry.entry_id)

    return True


@callback
def _setup_persistent_notification(
    hass: HomeAssistant, anepc: AnepcCoordinator, entry_id: str
) -> None:
    """Register a listener that creates/dismisses persistent notifications."""
    notification_id = f"pyrovigil_fire_{entry_id}"

    @callback
    def _on_update() -> None:
        data = anepc.data
        if data is None:
            return
        if data.fires:
            nearest = data.nearest_fire
            pn_create(
                hass,
                (
                    f"**{len(data.fires)} fire(s) detected nearby.**\n"
                    f"Nearest: {nearest.nature} in {nearest.concelho}, "
                    f"{round(nearest.effective_distance_km, 1)} km away. "
                    f"Severity: {nearest.severity}. "
                    f"Personnel: {data.total_personnel}."
                ),
                title="Pyrovigil — Fire Alert",
                notification_id=notification_id,
            )
        else:
            pn_dismiss(hass, notification_id)

    anepc.async_add_listener(_on_update)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        pn_dismiss(hass, f"pyrovigil_fire_{entry.entry_id}")
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
