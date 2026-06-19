"""Tests for Pyrovigil coordinators."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.pyrovigil.api import PyrovigilApiClient
from custom_components.pyrovigil.coordinator import (
    AnepcCoordinator,
    FireRiskCoordinator,
    FirmsCoordinator,
    WeatherWarningCoordinator,
)
from custom_components.pyrovigil.models import (
    AnepcData,
    FireRiskData,
    FirmsData,
    WeatherWarningData,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict | list:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def mock_api() -> AsyncMock:
    """Create a mock API client."""
    api = AsyncMock(spec=PyrovigilApiClient)
    return api


# --- Lisbon coords for all tests ---
HOME_LAT = 38.72
HOME_LON = -9.14


class TestAnepcCoordinator:
    """Tests for the ANEPC fire incidents coordinator."""

    @pytest.mark.asyncio
    async def test_update_returns_anepc_data(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        assert coordinator.last_update_success
        data: AnepcData = coordinator.data
        assert len(data.fires) == 3
        assert data.total_personnel == 48 + 16 + 8
        assert data.total_ground_vehicles == 12 + 5 + 3
        assert data.total_aircraft == 2 + 0 + 0

    @pytest.mark.asyncio
    async def test_fires_sorted_by_distance(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        data: AnepcData = coordinator.data
        distances = [f.distance_km for f in data.fires]
        assert distances == sorted(distances)

    @pytest.mark.asyncio
    async def test_nearest_fire(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        data: AnepcData = coordinator.data
        assert data.nearest_fire is not None
        assert data.nearest_fire.distance_km == min(f.distance_km for f in data.fires)

    @pytest.mark.asyncio
    async def test_empty_fires(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_nearby_fires.return_value = []

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        data: AnepcData = coordinator.data
        assert len(data.fires) == 0
        assert data.nearest_fire is None
        assert data.total_personnel == 0
        assert data.total_ground_vehicles == 0
        assert data.total_aircraft == 0

    @pytest.mark.asyncio
    async def test_api_error_raises_update_failed(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        mock_api.async_get_nearby_fires.side_effect = Exception("connection error")

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        assert not coordinator.last_update_success

    @pytest.mark.asyncio
    async def test_new_fire_event(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        """Test that pyrovigil_fire_detected event fires for new fires."""
        events = []
        hass.bus.async_listen("pyrovigil_fire_detected", lambda e: events.append(e))

        # First update — all fires are new
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_no_duplicate_events_on_second_refresh(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        """Existing fires should not fire events again."""
        events = []
        hass.bus.async_listen("pyrovigil_fire_detected", lambda e: events.append(e))

        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        initial_count = len(events)

        # Second refresh with same data — no new events
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert len(events) == initial_count


class TestFireRiskCoordinator:
    """Tests for the IPMA fire risk coordinator."""

    @pytest.mark.asyncio
    async def test_update_returns_fire_risk_data(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        rcm_d0 = _load_fixture("rcm_d0.json")
        rcm_d1 = _load_fixture("rcm_d0.json")  # reuse fixture for d1
        mock_api.async_get_fire_risk.side_effect = [rcm_d0, rcm_d1]

        coordinator = FireRiskCoordinator(hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=60))
        await coordinator.async_refresh()

        data: FireRiskData = coordinator.data
        assert data.today is not None
        assert data.today.rcm == 3  # DICO 1106 is nearest to Lisbon
        assert data.dico_code == "1106"

    @pytest.mark.asyncio
    async def test_caches_dico_code(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        rcm = _load_fixture("rcm_d0.json")
        mock_api.async_get_fire_risk.return_value = rcm

        coordinator = FireRiskCoordinator(hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=60))
        await coordinator.async_refresh()
        first_dico = coordinator._dico_code

        # Second refresh — dico should be cached, not recomputed
        await coordinator.async_refresh()
        assert coordinator._dico_code == first_dico

    @pytest.mark.asyncio
    async def test_api_error(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_fire_risk.side_effect = Exception("timeout")

        coordinator = FireRiskCoordinator(hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=60))
        await coordinator.async_refresh()

        assert not coordinator.last_update_success


class TestWeatherWarningCoordinator:
    """Tests for the IPMA weather warning coordinator."""

    @pytest.mark.asyncio
    async def test_update_returns_warning_data(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        warnings = _load_fixture("warnings.json")
        mock_api.async_get_weather_warnings.return_value = warnings

        coordinator = WeatherWarningCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        data: WeatherWarningData = coordinator.data
        # LSB has 2 warnings in the fixture (Trovoada + Tempo Quente)
        assert len(data.warnings) >= 1

    @pytest.mark.asyncio
    async def test_filters_to_user_area(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        warnings = _load_fixture("warnings.json")
        mock_api.async_get_weather_warnings.return_value = warnings

        # Porto coords — should only see PRT warnings
        coordinator = WeatherWarningCoordinator(hass, mock_api, 41.15, -8.61, timedelta(minutes=30))
        await coordinator.async_refresh()

        data: WeatherWarningData = coordinator.data
        for w in data.warnings:
            assert w.area_code == "PRT"

    @pytest.mark.asyncio
    async def test_highest_level(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        warnings = _load_fixture("warnings.json")
        mock_api.async_get_weather_warnings.return_value = warnings

        coordinator = WeatherWarningCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        data: WeatherWarningData = coordinator.data
        # LSB has orange + yellow, highest should be orange
        assert data.highest_level == "orange"

    @pytest.mark.asyncio
    async def test_no_warnings(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_weather_warnings.return_value = []

        coordinator = WeatherWarningCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        data: WeatherWarningData = coordinator.data
        assert data.warnings == []
        assert data.highest_level == "green"

    @pytest.mark.asyncio
    async def test_api_error(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_weather_warnings.side_effect = Exception("error")

        coordinator = WeatherWarningCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        assert not coordinator.last_update_success


class TestAnepcCoordinatorSafetyBuffer:
    """Tests for safety buffer and burn area enrichment."""

    @pytest.mark.asyncio
    async def test_safety_margin_extends_query(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        mock_api.async_get_nearby_fires.return_value = []
        mock_api.async_get_fogos_active.return_value = []

        coordinator = AnepcCoordinator(
            hass,
            mock_api,
            HOME_LAT,
            HOME_LON,
            25,
            timedelta(minutes=5),
            safety_margin_km=10,
        )
        await coordinator.async_refresh()

        call_args = mock_api.async_get_nearby_fires.call_args
        assert call_args[0][2] == 35  # radius + margin

    @pytest.mark.asyncio
    async def test_severity_is_computed(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list
        mock_api.async_get_fogos_active.return_value = []

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        data: AnepcData = coordinator.data
        for fire in data.fires:
            assert fire.severity in ("low", "moderate", "high", "extreme")

    @pytest.mark.asyncio
    async def test_burn_area_adjusts_distance(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list
        mock_api.async_get_fogos_active.return_value = [
            {
                "sadoId": "20260001234",
                "id": "fogos_1",
                "icnf": {"burnArea": {"total": 500}},
            }
        ]

        coordinator = AnepcCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, 100, timedelta(minutes=5)
        )
        await coordinator.async_refresh()

        fire = next(f for f in coordinator.data.fires if f.fire_id == "20260001234")
        assert fire.burn_area_ha == 500.0
        assert fire.adjusted_distance_km is not None
        assert fire.adjusted_distance_km < fire.distance_km

    @pytest.mark.asyncio
    async def test_fogos_failure_is_graceful(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        fixture = _load_fixture("anepc_response.json")
        attrs_list = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs_list
        mock_api.async_get_fogos_active.side_effect = Exception("fogos down")

        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, timedelta(minutes=5))
        await coordinator.async_refresh()

        assert coordinator.last_update_success
        assert len(coordinator.data.fires) == 3


class TestAdaptivePolling:
    """Tests for adaptive polling rate."""

    @pytest.mark.asyncio
    async def test_switches_to_alert_interval_when_fires_appear(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        mock_api.async_get_fogos_active.return_value = []
        # Start with no fires
        mock_api.async_get_nearby_fires.return_value = []

        normal = timedelta(minutes=5)
        alert = timedelta(minutes=2)
        coordinator = AnepcCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, 25, normal, alert_interval=alert
        )
        await coordinator.async_refresh()
        assert coordinator.update_interval == normal

        # Now fires appear
        fixture = _load_fixture("anepc_response.json")
        mock_api.async_get_nearby_fires.return_value = [
            f["attributes"] for f in fixture["features"]
        ]
        await coordinator.async_refresh()
        assert coordinator.update_interval == alert

    @pytest.mark.asyncio
    async def test_restores_normal_interval_when_fires_clear(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        mock_api.async_get_fogos_active.return_value = []
        fixture = _load_fixture("anepc_response.json")

        normal = timedelta(minutes=5)
        alert = timedelta(minutes=2)
        coordinator = AnepcCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, 25, normal, alert_interval=alert
        )

        # Fires present
        mock_api.async_get_nearby_fires.return_value = [
            f["attributes"] for f in fixture["features"]
        ]
        await coordinator.async_refresh()
        assert coordinator.update_interval == alert

        # Fires clear
        mock_api.async_get_nearby_fires.return_value = []
        await coordinator.async_refresh()
        assert coordinator.update_interval == normal

    @pytest.mark.asyncio
    async def test_no_change_without_adaptive(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        """Without alert_interval, polling stays constant."""
        mock_api.async_get_fogos_active.return_value = []
        fixture = _load_fixture("anepc_response.json")

        normal = timedelta(minutes=5)
        coordinator = AnepcCoordinator(hass, mock_api, HOME_LAT, HOME_LON, 25, normal)

        mock_api.async_get_nearby_fires.return_value = [
            f["attributes"] for f in fixture["features"]
        ]
        await coordinator.async_refresh()
        assert coordinator.update_interval == normal

    @pytest.mark.asyncio
    async def test_stays_in_alert_mode_while_fires_persist(
        self, hass: HomeAssistant, mock_api: AsyncMock
    ) -> None:
        mock_api.async_get_fogos_active.return_value = []
        fixture = _load_fixture("anepc_response.json")

        normal = timedelta(minutes=5)
        alert = timedelta(minutes=2)
        coordinator = AnepcCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, 25, normal, alert_interval=alert
        )

        attrs = [f["attributes"] for f in fixture["features"]]
        mock_api.async_get_nearby_fires.return_value = attrs

        await coordinator.async_refresh()
        assert coordinator.update_interval == alert

        # Second refresh with fires still there — should stay in alert
        await coordinator.async_refresh()
        assert coordinator.update_interval == alert


class TestFirmsCoordinator:
    """Tests for the NASA FIRMS coordinator."""

    @pytest.mark.asyncio
    async def test_returns_firms_data(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_firms_hotspots.return_value = [
            {
                "latitude": "38.75",
                "longitude": "-9.10",
                "bright_ti4": "350",
                "confidence": "nominal",
                "frp": "25",
            },
            {
                "latitude": "38.80",
                "longitude": "-9.05",
                "bright_ti4": "320",
                "confidence": "low",
                "frp": "10",
            },
        ]

        coordinator = FirmsCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, "test_key", timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        data: FirmsData = coordinator.data
        assert data.count == 2
        assert data.nearest_hotspot_km is not None

    @pytest.mark.asyncio
    async def test_empty_hotspots(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_firms_hotspots.return_value = []

        coordinator = FirmsCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, "test_key", timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        data: FirmsData = coordinator.data
        assert data.count == 0
        assert data.nearest_hotspot_km is None

    @pytest.mark.asyncio
    async def test_api_error(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_firms_hotspots.side_effect = Exception("error")

        coordinator = FirmsCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, "test_key", timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        assert not coordinator.last_update_success

    @pytest.mark.asyncio
    async def test_sorted_by_distance(self, hass: HomeAssistant, mock_api: AsyncMock) -> None:
        mock_api.async_get_firms_hotspots.return_value = [
            {
                "latitude": "39.0",
                "longitude": "-9.2",
                "bright_ti4": "300",
                "confidence": "n",
                "frp": "5",
            },
            {
                "latitude": "38.73",
                "longitude": "-9.13",
                "bright_ti4": "350",
                "confidence": "h",
                "frp": "20",
            },
        ]

        coordinator = FirmsCoordinator(
            hass, mock_api, HOME_LAT, HOME_LON, "test_key", timedelta(minutes=30)
        )
        await coordinator.async_refresh()

        distances = [h.distance_km for h in coordinator.data.hotspots]
        assert distances == sorted(distances)
