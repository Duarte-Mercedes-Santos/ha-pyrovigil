"""Tests for Pyrovigil sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.pyrovigil.const import MAX_FIRES_IN_ATTRIBUTES
from custom_components.pyrovigil.models import (
    AnepcData,
    FireIncident,
    FireRiskData,
    FireRiskEntry,
    WeatherWarning,
    WeatherWarningData,
)
from custom_components.pyrovigil.sensor import (
    ActiveFiresSensor,
    FireRiskSensor,
    FireRiskTomorrowSensor,
    NearestFireSensor,
    TotalAircraftSensor,
    TotalGroundVehiclesSensor,
    TotalPersonnelSensor,
    WeatherWarningsSensor,
)


def _make_fire(
    fire_id: str,
    distance: float,
    personnel: int = 10,
    vehicles: int = 3,
    aircraft: int = 0,
) -> FireIncident:
    return FireIncident(
        fire_id=fire_id,
        nature_code=3101,
        nature="3101 - Povoamento Florestal",
        status_code=5,
        status="Em Curso",
        status_group="Em Curso",
        latitude=38.75,
        longitude=-9.10,
        distance_km=distance,
        concelho="Lisboa",
        freguesia="Benfica",
        locality="BENFICA",
        personnel=personnel,
        ground_personnel=personnel,
        aerial_personnel=0,
        ground_vehicles=vehicles,
        aircraft=aircraft,
        entities_count=1,
        started="17/06/2026 14:30",
        duration="0/02:15",
        duration_minutes=135,
    )


def _make_anepc_data(
    fires: list | None = None,
    personnel: int = 0,
    vehicles: int = 0,
    aircraft: int = 0,
) -> AnepcData:
    if fires is None:
        fires = []
    return AnepcData(
        fires=fires,
        nearest_fire=fires[0] if fires else None,
        total_personnel=personnel,
        total_ground_vehicles=vehicles,
        total_aircraft=aircraft,
    )


def _make_coordinator(data):
    """Create a mock coordinator with the given data."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    return coordinator


def _make_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    return entry


class TestActiveFiresSensor:
    """Tests for the active fires count sensor."""

    def test_state_is_fire_count(self) -> None:
        fires = [_make_fire("1", 5.0), _make_fire("2", 10.0)]
        data = _make_anepc_data(fires, personnel=20, vehicles=6)
        coordinator = _make_coordinator(data)

        sensor = ActiveFiresSensor(coordinator, _make_entry(), 25)
        assert sensor.native_value == 2

    def test_state_zero_when_no_fires(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)

        sensor = ActiveFiresSensor(coordinator, _make_entry(), 25)
        assert sensor.native_value == 0

    def test_attributes_contain_fire_list(self) -> None:
        fires = [_make_fire("1", 5.0), _make_fire("2", 10.0)]
        data = _make_anepc_data(fires, personnel=20, vehicles=6)
        coordinator = _make_coordinator(data)

        sensor = ActiveFiresSensor(coordinator, _make_entry(), 25)
        attrs = sensor.extra_state_attributes
        assert len(attrs["fires"]) == 2
        assert attrs["radius_km"] == 25

    def test_attributes_capped_at_max(self) -> None:
        fires = [_make_fire(str(i), float(i)) for i in range(30)]
        data = _make_anepc_data(fires, personnel=300, vehicles=90)
        coordinator = _make_coordinator(data)

        sensor = ActiveFiresSensor(coordinator, _make_entry(), 25)
        attrs = sensor.extra_state_attributes
        assert len(attrs["fires"]) == MAX_FIRES_IN_ATTRIBUTES

    def test_unique_id(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)
        entry = _make_entry()

        sensor = ActiveFiresSensor(coordinator, entry, 25)
        assert sensor.unique_id == f"{entry.entry_id}_active_fires"


class TestNearestFireSensor:
    """Tests for the nearest fire distance sensor."""

    def test_state_is_distance(self) -> None:
        fire = _make_fire("1", 5.234)
        data = _make_anepc_data([fire], personnel=10, vehicles=3)
        coordinator = _make_coordinator(data)

        sensor = NearestFireSensor(coordinator, _make_entry())
        assert sensor.native_value == 5.2  # rounded to 1 decimal

    def test_state_none_when_no_fires(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)

        sensor = NearestFireSensor(coordinator, _make_entry())
        assert sensor.native_value is None

    def test_attributes_contain_fire_details(self) -> None:
        fire = _make_fire("1", 5.0, personnel=48, vehicles=12, aircraft=2)
        data = _make_anepc_data([fire], personnel=48, vehicles=12, aircraft=2)
        coordinator = _make_coordinator(data)

        sensor = NearestFireSensor(coordinator, _make_entry())
        attrs = sensor.extra_state_attributes
        assert attrs["fire_id"] == "1"
        assert attrs["personnel"] == 48
        assert attrs["ground_vehicles"] == 12
        assert attrs["aircraft"] == 2
        assert attrs["concelho"] == "Lisboa"


class TestTotalPersonnelSensor:
    """Tests for the total personnel aggregate sensor."""

    def test_state(self) -> None:
        data = AnepcData(total_personnel=72)
        coordinator = _make_coordinator(data)

        sensor = TotalPersonnelSensor(coordinator, _make_entry())
        assert sensor.native_value == 72

    def test_default_disabled(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)

        sensor = TotalPersonnelSensor(coordinator, _make_entry())
        assert sensor.entity_registry_enabled_default is False


class TestTotalGroundVehiclesSensor:
    """Tests for the total ground vehicles aggregate sensor."""

    def test_state(self) -> None:
        data = AnepcData(total_ground_vehicles=20)
        coordinator = _make_coordinator(data)

        sensor = TotalGroundVehiclesSensor(coordinator, _make_entry())
        assert sensor.native_value == 20


class TestTotalAircraftSensor:
    """Tests for the total aircraft aggregate sensor."""

    def test_state(self) -> None:
        data = AnepcData(total_aircraft=3)
        coordinator = _make_coordinator(data)

        sensor = TotalAircraftSensor(coordinator, _make_entry())
        assert sensor.native_value == 3


class TestFireRiskSensor:
    """Tests for the fire risk sensor."""

    def test_state_is_rcm_value(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=3, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106", forecast_date="2026-06-17")
        coordinator = _make_coordinator(data)

        sensor = FireRiskSensor(coordinator, _make_entry())
        assert sensor.native_value == 3

    def test_state_none_when_no_data(self) -> None:
        data = FireRiskData()
        coordinator = _make_coordinator(data)

        sensor = FireRiskSensor(coordinator, _make_entry())
        assert sensor.native_value is None

    def test_attributes_contain_risk_label(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=4, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106", forecast_date="2026-06-17")
        coordinator = _make_coordinator(data)

        sensor = FireRiskSensor(coordinator, _make_entry())
        attrs = sensor.extra_state_attributes
        assert attrs["risk_label"] == "Muito Elevado"
        assert attrs["dico_code"] == "1106"
        assert attrs["forecast_date"] == "2026-06-17"


class TestFireRiskTomorrowSensor:
    """Tests for the tomorrow fire risk sensor."""

    def test_state_from_tomorrow_data(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=5, latitude=38.72, longitude=-9.14)
        data = FireRiskData(tomorrow=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = FireRiskTomorrowSensor(coordinator, _make_entry())
        assert sensor.native_value == 5

    def test_default_disabled(self) -> None:
        data = FireRiskData()
        coordinator = _make_coordinator(data)

        sensor = FireRiskTomorrowSensor(coordinator, _make_entry())
        assert sensor.entity_registry_enabled_default is False


class TestWeatherWarningsSensor:
    """Tests for the weather warnings sensor."""

    def test_state_is_warning_count(self) -> None:
        w = WeatherWarning(
            awareness_type="Trovoada",
            awareness_level="orange",
            area_code="LSB",
            text="Trovoada.",
            start_time="",
            end_time="",
        )
        data = WeatherWarningData(warnings=[w], highest_level="orange")
        coordinator = _make_coordinator(data)

        sensor = WeatherWarningsSensor(coordinator, _make_entry())
        assert sensor.native_value == 1

    def test_attributes_contain_warnings(self) -> None:
        w = WeatherWarning(
            awareness_type="Trovoada",
            awareness_level="orange",
            area_code="LSB",
            text="Trovoada.",
            start_time="",
            end_time="",
        )
        data = WeatherWarningData(warnings=[w], highest_level="orange")
        coordinator = _make_coordinator(data)

        sensor = WeatherWarningsSensor(coordinator, _make_entry())
        attrs = sensor.extra_state_attributes
        assert attrs["highest_level"] == "orange"
        assert len(attrs["warnings"]) == 1

    def test_default_disabled(self) -> None:
        data = WeatherWarningData()
        coordinator = _make_coordinator(data)

        sensor = WeatherWarningsSensor(coordinator, _make_entry())
        assert sensor.entity_registry_enabled_default is False
