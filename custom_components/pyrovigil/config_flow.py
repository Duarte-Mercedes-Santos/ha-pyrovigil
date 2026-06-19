"""Config flow for the Pyrovigil integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PyrovigilApiClient
from .const import (
    CONF_ADAPTIVE_POLLING,
    CONF_ALERT_SCAN_INTERVAL,
    CONF_AQICN_TOKEN,
    CONF_HIGH_RISK_THRESHOLD,
    CONF_NASA_FIRMS_KEY,
    CONF_RADIUS,
    CONF_SAFETY_MARGIN,
    DEFAULT_ADAPTIVE_POLLING,
    DEFAULT_ALERT_SCAN_INTERVAL_MINUTES,
    DEFAULT_HIGH_RISK_THRESHOLD,
    DEFAULT_RADIUS_KM,
    DEFAULT_SAFETY_MARGIN_KM,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_RADIUS_KM,
    MAX_SAFETY_MARGIN_KM,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_ALERT_SCAN_INTERVAL_MINUTES,
    MIN_RADIUS_KM,
    MIN_SAFETY_MARGIN_KM,
    MIN_SCAN_INTERVAL_MINUTES,
    PORTUGAL_LAT_MAX,
    PORTUGAL_LAT_MIN,
    PORTUGAL_LON_MAX,
    PORTUGAL_LON_MIN,
)

CONF_ZONE_NAME = "zone_name"

_LOGGER = logging.getLogger(__name__)


class PyrovigilConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pyrovigil."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            lat = user_input[CONF_LATITUDE]
            lon = user_input[CONF_LONGITUDE]

            if not (
                PORTUGAL_LAT_MIN <= lat <= PORTUGAL_LAT_MAX
                and PORTUGAL_LON_MIN <= lon <= PORTUGAL_LON_MAX
            ):
                errors["base"] = "invalid_coordinates"
            else:
                # Check for duplicate entry
                unique_id = f"{round(lat, 2)}_{round(lon, 2)}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Test API connectivity
                try:
                    session = async_get_clientsession(self.hass)
                    client = PyrovigilApiClient(session)
                    await client.async_get_nearby_fires(lat, lon, 10)
                except Exception:
                    errors["base"] = "cannot_connect"

            if not errors:
                zone_name = user_input.get(CONF_ZONE_NAME, "Home")
                return self.async_create_entry(
                    title=f"Pyrovigil — {zone_name}",
                    data=user_input,
                )

        default_lat = self.hass.config.latitude or 38.72
        default_lon = self.hass.config.longitude or -9.14

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ZONE_NAME, default="Home"): str,
                    vol.Required(CONF_LATITUDE, default=default_lat): vol.Coerce(float),
                    vol.Required(CONF_LONGITUDE, default=default_lon): vol.Coerce(float),
                    vol.Required(CONF_RADIUS, default=DEFAULT_RADIUS_KM): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_RADIUS_KM, max=MAX_RADIUS_KM)
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_MINUTES
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL_MINUTES, max=MAX_SCAN_INTERVAL_MINUTES),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle YAML import."""
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PyrovigilOptionsFlow:
        """Get the options flow."""
        return PyrovigilOptionsFlow(config_entry)


class PyrovigilOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Pyrovigil."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_RADIUS,
                        default=self._config_entry.options.get(
                            CONF_RADIUS,
                            self._config_entry.data.get(CONF_RADIUS, DEFAULT_RADIUS_KM),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_RADIUS_KM, max=MAX_RADIUS_KM)),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self._config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL_MINUTES, max=MAX_SCAN_INTERVAL_MINUTES),
                    ),
                    vol.Required(
                        CONF_HIGH_RISK_THRESHOLD,
                        default=self._config_entry.options.get(
                            CONF_HIGH_RISK_THRESHOLD, DEFAULT_HIGH_RISK_THRESHOLD
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=5)),
                    vol.Required(
                        CONF_SAFETY_MARGIN,
                        default=self._config_entry.options.get(
                            CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN_KM
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SAFETY_MARGIN_KM, max=MAX_SAFETY_MARGIN_KM),
                    ),
                    vol.Required(
                        CONF_ADAPTIVE_POLLING,
                        default=self._config_entry.options.get(
                            CONF_ADAPTIVE_POLLING, DEFAULT_ADAPTIVE_POLLING
                        ),
                    ): bool,
                    vol.Required(
                        CONF_ALERT_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_ALERT_SCAN_INTERVAL, DEFAULT_ALERT_SCAN_INTERVAL_MINUTES
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_ALERT_SCAN_INTERVAL_MINUTES,
                            max=MAX_SCAN_INTERVAL_MINUTES,
                        ),
                    ),
                    vol.Optional(
                        CONF_NASA_FIRMS_KEY,
                        default=self._config_entry.options.get(CONF_NASA_FIRMS_KEY, ""),
                    ): str,
                    vol.Optional(
                        CONF_AQICN_TOKEN,
                        default=self._config_entry.options.get(CONF_AQICN_TOKEN, ""),
                    ): str,
                }
            ),
        )
