"""Tests for Pyrovigil binary sensor entities."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.pyrovigil.binary_sensor import (
    FireNearbyBinarySensor,
    HighFireRiskBinarySensor,
)
from custom_components.pyrovigil.models import (
    AnepcData,
    FireIncident,
    FireRiskData,
    FireRiskEntry,
)


def _make_fire(fire_id: str, distance: float) -> FireIncident:
    return FireIncident(
        fire_id=fire_id,
        nature_code=3101,
        nature="Florestal",
        status_code=5,
        status="Em Curso",
        status_group="Em Curso",
        latitude=38.75,
        longitude=-9.10,
        distance_km=distance,
        concelho="Lisboa",
        freguesia="Benfica",
        locality="BENFICA",
        personnel=10,
        ground_personnel=10,
        aerial_personnel=0,
        ground_vehicles=3,
        aircraft=0,
        entities_count=1,
        started="",
        duration="",
        duration_minutes=0,
    )


def _make_coordinator(data):
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    return coordinator


def _make_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    return entry


class TestFireNearbyBinarySensor:
    """Tests for fire_nearby binary sensor."""

    def test_on_when_fires_exist(self) -> None:
        fire = _make_fire("1", 5.0)
        data = AnepcData(
            fires=[fire],
            nearest_fire=fire,
            total_personnel=10,
            total_ground_vehicles=3,
            total_aircraft=0,
        )
        coordinator = _make_coordinator(data)

        sensor = FireNearbyBinarySensor(coordinator, _make_entry())
        assert sensor.is_on is True

    def test_off_when_no_fires(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)

        sensor = FireNearbyBinarySensor(coordinator, _make_entry())
        assert sensor.is_on is False

    def test_attributes(self) -> None:
        fires = [_make_fire("1", 5.0), _make_fire("2", 10.0)]
        data = AnepcData(
            fires=fires,
            nearest_fire=fires[0],
            total_personnel=20,
            total_ground_vehicles=6,
            total_aircraft=0,
        )
        coordinator = _make_coordinator(data)

        sensor = FireNearbyBinarySensor(coordinator, _make_entry())
        attrs = sensor.extra_state_attributes
        assert attrs["count"] == 2
        assert attrs["nearest_distance_km"] == 5.0

    def test_attributes_no_fires(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)

        sensor = FireNearbyBinarySensor(coordinator, _make_entry())
        attrs = sensor.extra_state_attributes
        assert attrs["count"] == 0
        assert attrs["nearest_distance_km"] is None

    def test_unique_id(self) -> None:
        data = AnepcData()
        coordinator = _make_coordinator(data)
        entry = _make_entry()

        sensor = FireNearbyBinarySensor(coordinator, entry)
        assert sensor.unique_id == f"{entry.entry_id}_fire_nearby"


class TestHighFireRiskBinarySensor:
    """Tests for high_fire_risk binary sensor."""

    def test_on_when_rcm_at_threshold(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=4, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=4)
        assert sensor.is_on is True

    def test_on_when_rcm_above_threshold(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=5, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=4)
        assert sensor.is_on is True

    def test_off_when_rcm_below_threshold(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=2, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=4)
        assert sensor.is_on is False

    def test_off_when_no_data(self) -> None:
        data = FireRiskData()
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=4)
        assert sensor.is_on is False

    def test_attributes(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=4, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=4)
        attrs = sensor.extra_state_attributes
        assert attrs["risk_level"] == 4
        assert attrs["threshold"] == 4
        assert attrs["dico_code"] == "1106"

    def test_custom_threshold(self) -> None:
        risk = FireRiskEntry(dico_code="1106", rcm=3, latitude=38.72, longitude=-9.14)
        data = FireRiskData(today=risk, dico_code="1106")
        coordinator = _make_coordinator(data)

        sensor = HighFireRiskBinarySensor(coordinator, _make_entry(), threshold=3)
        assert sensor.is_on is True
