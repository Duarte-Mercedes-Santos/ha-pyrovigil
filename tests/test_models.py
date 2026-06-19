"""Tests for Pyrovigil data models."""

from custom_components.pyrovigil.models import (
    AnepcData,
    FireIncident,
    FireRiskData,
    FireRiskEntry,
    FirmsData,
    FirmsHotspot,
    WeatherWarning,
    WeatherWarningData,
)


class TestFireIncident:
    """Tests for FireIncident dataclass."""

    def test_from_api_response(self, anepc_response_data: dict) -> None:
        attrs = anepc_response_data["features"][0]["attributes"]
        fire = FireIncident.from_api_response(attrs, distance_km=5.2)

        assert fire.fire_id == "20260001234"
        assert fire.nature_code == 3101
        assert fire.nature == "3101 - Povoamento Florestal"
        assert fire.status == "Em Curso"
        assert fire.latitude == 38.75
        assert fire.longitude == -9.10
        assert fire.distance_km == 5.2
        assert fire.concelho == "Lisboa"
        assert fire.freguesia == "Benfica"
        assert fire.personnel == 48
        assert fire.ground_personnel == 45
        assert fire.aerial_personnel == 3
        assert fire.ground_vehicles == 12
        assert fire.aircraft == 2
        assert fire.entities_count == 4
        assert fire.started == "17/06/2026 14:30"
        assert fire.duration_minutes == 135

    def test_from_api_response_missing_fields(self) -> None:
        fire = FireIncident.from_api_response({}, distance_km=0.0)

        assert fire.fire_id == ""
        assert fire.nature_code == 0
        assert fire.personnel == 0
        assert fire.ground_vehicles == 0
        assert fire.aircraft == 0
        assert fire.distance_km == 0.0

    def test_from_api_response_null_resource_values(self) -> None:
        attrs = {
            "Numero": "123",
            "Operacionais": None,
            "MeiosTerrestres": None,
            "MeiosAereos": None,
        }
        fire = FireIncident.from_api_response(attrs, distance_km=1.0)

        assert fire.personnel == 0
        assert fire.ground_vehicles == 0
        assert fire.aircraft == 0

    def test_to_dict(self, anepc_response_data: dict) -> None:
        attrs = anepc_response_data["features"][0]["attributes"]
        fire = FireIncident.from_api_response(attrs, distance_km=5.23456)
        result = fire.to_dict()

        assert result["fire_id"] == "20260001234"
        assert result["distance_km"] == 5.2  # rounded to 1 decimal
        assert result["personnel"] == 48
        assert result["ground_vehicles"] == 12
        assert result["aircraft"] == 2
        assert result["latitude"] == 38.75
        assert result["longitude"] == -9.10
        assert "nature_code" not in result  # internal field, not exposed

    def test_frozen(self, anepc_response_data: dict) -> None:
        attrs = anepc_response_data["features"][0]["attributes"]
        fire = FireIncident.from_api_response(attrs, distance_km=1.0)

        try:
            fire.personnel = 999  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestFireRiskEntry:
    """Tests for FireRiskEntry dataclass."""

    def test_creation(self) -> None:
        entry = FireRiskEntry(dico_code="1106", rcm=3, latitude=38.72, longitude=-9.14)

        assert entry.dico_code == "1106"
        assert entry.rcm == 3
        assert entry.latitude == 38.72
        assert entry.longitude == -9.14


class TestWeatherWarning:
    """Tests for WeatherWarning dataclass."""

    def test_from_api_response(self, warnings_data: list[dict]) -> None:
        warning = WeatherWarning.from_api_response(warnings_data[0])

        assert warning.awareness_type == "Trovoada"
        assert warning.awareness_level == "orange"
        assert warning.area_code == "LSB"
        assert "trovoada" in warning.text.lower()
        assert warning.start_time == "2026-06-17T14:00:00"
        assert warning.end_time == "2026-06-17T21:00:00"

    def test_from_api_response_missing_fields(self) -> None:
        warning = WeatherWarning.from_api_response({})

        assert warning.awareness_type == ""
        assert warning.awareness_level == ""
        assert warning.area_code == ""

    def test_to_dict(self, warnings_data: list[dict]) -> None:
        warning = WeatherWarning.from_api_response(warnings_data[0])
        result = warning.to_dict()

        assert result["type"] == "Trovoada"
        assert result["level"] == "orange"
        assert "start" in result
        assert "end" in result
        assert "area_code" not in result  # internal field


class TestAnepcData:
    """Tests for AnepcData aggregate dataclass."""

    def test_defaults(self) -> None:
        data = AnepcData()

        assert data.fires == []
        assert data.nearest_fire is None
        assert data.total_personnel == 0
        assert data.total_ground_vehicles == 0
        assert data.total_aircraft == 0
        assert data.last_updated is None


class TestFireRiskData:
    """Tests for FireRiskData aggregate dataclass."""

    def test_defaults(self) -> None:
        data = FireRiskData()

        assert data.today is None
        assert data.tomorrow is None
        assert data.dico_code == ""
        assert data.forecast_date == ""


class TestWeatherWarningData:
    """Tests for WeatherWarningData aggregate dataclass."""

    def test_defaults(self) -> None:
        data = WeatherWarningData()

        assert data.warnings == []
        assert data.highest_level == "green"


class TestFireIncidentSeverity:
    """Tests for severity computation."""

    def test_low_severity(self) -> None:
        assert FireIncident.compute_severity(10, 0) == "low"

    def test_moderate_severity(self) -> None:
        assert FireIncident.compute_severity(50, 0) == "moderate"

    def test_high_severity_by_personnel(self) -> None:
        assert FireIncident.compute_severity(150, 0) == "high"

    def test_high_severity_by_aircraft(self) -> None:
        assert FireIncident.compute_severity(10, 2) == "high"

    def test_extreme_severity_by_personnel(self) -> None:
        assert FireIncident.compute_severity(300, 0) == "extreme"

    def test_extreme_severity_by_aircraft(self) -> None:
        assert FireIncident.compute_severity(10, 4) == "extreme"


class TestFireRadiusFromArea:
    """Tests for burn area to fire radius conversion."""

    def test_zero_area(self) -> None:
        assert FireIncident.fire_radius_from_area(0) == 0.0

    def test_negative_area(self) -> None:
        assert FireIncident.fire_radius_from_area(-10) == 0.0

    def test_100ha(self) -> None:
        # 100 ha = 1 km2, radius = sqrt(1/pi) ≈ 0.564 km
        radius = FireIncident.fire_radius_from_area(100)
        assert 0.55 < radius < 0.58

    def test_1000ha(self) -> None:
        # 1000 ha = 10 km2, radius = sqrt(10/pi) ≈ 1.78 km
        radius = FireIncident.fire_radius_from_area(1000)
        assert 1.7 < radius < 1.9


class TestEffectiveDistance:
    """Tests for effective_distance_km property."""

    def test_uses_adjusted_when_available(self) -> None:
        fire = FireIncident.from_api_response(
            {"Numero": "1"}, distance_km=10.0, adjusted_distance_km=7.5
        )
        assert fire.effective_distance_km == 7.5

    def test_falls_back_to_origin_distance(self) -> None:
        fire = FireIncident.from_api_response({"Numero": "1"}, distance_km=10.0)
        assert fire.effective_distance_km == 10.0


class TestToDictWithBurnArea:
    """Tests for to_dict with burn area fields."""

    def test_includes_severity(self) -> None:
        fire = FireIncident.from_api_response({"Numero": "1"}, distance_km=5.0, severity="high")
        assert fire.to_dict()["severity"] == "high"

    def test_includes_burn_area_when_nonzero(self) -> None:
        fire = FireIncident.from_api_response(
            {"Numero": "1"},
            distance_km=10.0,
            burn_area_ha=500.0,
            adjusted_distance_km=8.5,
        )
        result = fire.to_dict()
        assert result["burn_area_ha"] == 500.0
        assert result["adjusted_distance_km"] == 8.5

    def test_omits_burn_area_when_zero(self) -> None:
        fire = FireIncident.from_api_response({"Numero": "1"}, distance_km=5.0)
        result = fire.to_dict()
        assert "burn_area_ha" not in result


class TestFirmsData:
    """Tests for FIRMS data models."""

    def test_defaults(self) -> None:
        data = FirmsData()
        assert data.hotspots == []
        assert data.nearest_hotspot_km is None
        assert data.count == 0

    def test_hotspot_creation(self) -> None:
        h = FirmsHotspot(
            latitude=38.75,
            longitude=-9.10,
            brightness=350.0,
            confidence="nominal",
            frp=25.5,
            distance_km=3.2,
        )
        assert h.latitude == 38.75
        assert h.distance_km == 3.2
