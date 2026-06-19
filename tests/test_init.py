"""Tests for Pyrovigil integration setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pyrovigil.const import CONF_RADIUS, DOMAIN

MOCK_CONFIG = {
    CONF_LATITUDE: 38.72,
    CONF_LONGITUDE: -9.14,
    CONF_RADIUS: 25,
    CONF_SCAN_INTERVAL: 5,
}


@pytest.fixture
def mock_api():
    """Mock the API client and aiohttp session."""
    with (
        patch("custom_components.pyrovigil.PyrovigilApiClient") as mock_cls,
        patch(
            "custom_components.pyrovigil.async_get_clientsession",
            return_value=AsyncMock(),
        ),
    ):
        client = AsyncMock()
        client.async_get_nearby_fires.return_value = []
        client.async_get_fire_risk.return_value = {
            "dataPrev": "2026-06-17",
            "local": {
                "1106": {
                    "data": {"rcm": 3},
                    "dico": "1106",
                    "latitude": 38.72,
                    "longitude": -9.14,
                }
            },
        }
        client.async_get_weather_warnings.return_value = []
        client.async_get_fogos_active.return_value = []
        client.async_get_weather_stations.return_value = [
            {
                "properties": {"idEstacao": "1200535", "localEstacao": "Lisboa/Gago Coutinho"},
                "latitude": 38.77,
                "longitude": -9.13,
            }
        ]
        client.async_get_weather_observations.return_value = {
            "2026-06-17T15:00": {
                "1200535": {
                    "intensidadeVentoKM": 12.0,
                    "idDireccVento": 3,
                }
            }
        }
        mock_cls.return_value = client
        yield client


class TestSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_setup_entry(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test_1")
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED
        assert DOMAIN in hass.data
        assert "test_1" in hass.data[DOMAIN]
        assert "anepc" in hass.data[DOMAIN]["test_1"]
        assert "fire_risk" in hass.data[DOMAIN]["test_1"]
        assert "warnings" in hass.data[DOMAIN]["test_1"]

    @pytest.mark.asyncio
    async def test_unload_entry(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test_2")
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.NOT_LOADED
        assert "test_2" not in hass.data.get(DOMAIN, {})

    @pytest.mark.asyncio
    async def test_setup_creates_sensors(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test_3")
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check that key entities were registered
        entity_ids = [state.entity_id for state in hass.states.async_all()]
        # At minimum, active_fires and fire_nearby should exist
        # (sensors with entity_registry_enabled_default=False may not appear as states)
        assert any("active_fires" in eid for eid in entity_ids)

    @pytest.mark.asyncio
    async def test_api_failure_on_setup(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        """If the API fails on first refresh, the entry should fail to load."""
        mock_api.async_get_nearby_fires.side_effect = Exception("API down")

        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG, entry_id="test_4")
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.SETUP_RETRY
