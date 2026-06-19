"""Tests for Pyrovigil config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pyrovigil.const import (
    CONF_HIGH_RISK_THRESHOLD,
    CONF_RADIUS,
    DEFAULT_RADIUS_KM,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

VALID_USER_INPUT = {
    CONF_LATITUDE: 38.72,
    CONF_LONGITUDE: -9.14,
    CONF_RADIUS: DEFAULT_RADIUS_KM,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL_MINUTES,
}


@pytest.fixture(autouse=True)
def mock_api_connectivity():
    """Mock API connectivity check."""
    with patch("custom_components.pyrovigil.config_flow.PyrovigilApiClient") as mock_cls:
        client = AsyncMock()
        client.async_get_nearby_fires.return_value = []
        mock_cls.return_value = client
        yield client


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Prevent actual setup during config flow tests."""
    with patch(
        "custom_components.pyrovigil.async_setup_entry",
        return_value=True,
        create=True,
    ):
        yield


class TestConfigFlow:
    """Tests for the user config flow."""

    @pytest.mark.asyncio
    async def test_user_form_shown(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_successful_config(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_USER_INPUT,
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Pyrovigil — Home"
        assert result["data"][CONF_LATITUDE] == 38.72
        assert result["data"][CONF_LONGITUDE] == -9.14
        assert result["data"][CONF_RADIUS] == DEFAULT_RADIUS_KM
        assert result["data"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL_MINUTES

    @pytest.mark.asyncio
    async def test_cannot_connect(
        self, hass: HomeAssistant, mock_api_connectivity: AsyncMock
    ) -> None:
        mock_api_connectivity.async_get_nearby_fires.side_effect = Exception("timeout")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_USER_INPUT,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_invalid_latitude(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                **VALID_USER_INPUT,
                CONF_LATITUDE: 50.0,  # outside Portugal
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_coordinates"

    @pytest.mark.asyncio
    async def test_invalid_longitude(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                **VALID_USER_INPUT,
                CONF_LONGITUDE: 5.0,  # outside Portugal
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_coordinates"

    @pytest.mark.asyncio
    async def test_duplicate_entry(self, hass: HomeAssistant) -> None:
        # First entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_USER_INPUT,
        )

        # Second entry with same coords — should abort
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_USER_INPUT,
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_yaml_import(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=VALID_USER_INPUT,
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_LATITUDE] == 38.72


class TestOptionsFlow:
    """Tests for the options flow."""

    @pytest.mark.asyncio
    async def test_options_flow(self, hass: HomeAssistant) -> None:
        # Create initial entry
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_USER_INPUT,
        )
        entry = result["result"]

        # Open options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_RADIUS: 50,
                CONF_SCAN_INTERVAL: 10,
                CONF_HIGH_RISK_THRESHOLD: 3,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_RADIUS] == 50
        assert entry.options[CONF_SCAN_INTERVAL] == 10
        assert entry.options[CONF_HIGH_RISK_THRESHOLD] == 3
