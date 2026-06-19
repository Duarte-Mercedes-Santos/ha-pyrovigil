"""Tests for Pyrovigil geographic mapping utilities."""

from custom_components.pyrovigil.mappings import (
    AREA_AVISO_COORDS,
    find_nearest_area_aviso,
    find_nearest_dico,
    haversine,
)


class TestHaversine:
    """Tests for the Haversine distance formula."""

    def test_same_point(self) -> None:
        assert haversine(38.72, -9.14, 38.72, -9.14) == 0.0

    def test_lisbon_to_porto(self) -> None:
        # Lisbon (38.72, -9.14) to Porto (41.15, -8.61) ~274 km
        dist = haversine(38.72, -9.14, 41.15, -8.61)
        assert 270 < dist < 280

    def test_lisbon_to_faro(self) -> None:
        # Lisbon (38.72, -9.14) to Faro (37.02, -7.93) ~218 km
        dist = haversine(38.72, -9.14, 37.02, -7.93)
        assert 210 < dist < 225

    def test_short_distance(self) -> None:
        # ~1km apart
        dist = haversine(38.72, -9.14, 38.729, -9.14)
        assert 0.9 < dist < 1.1

    def test_symmetry(self) -> None:
        d1 = haversine(38.72, -9.14, 41.15, -8.61)
        d2 = haversine(41.15, -8.61, 38.72, -9.14)
        assert abs(d1 - d2) < 0.001


class TestFindNearestDico:
    """Tests for DICO code lookup."""

    def test_nearest_to_lisbon(self, rcm_d0_data: dict) -> None:
        # Lisbon coords should match DICO 1106 (lat=38.72, lon=-9.14)
        dico = find_nearest_dico(38.72, -9.14, rcm_d0_data)
        assert dico == "1106"

    def test_nearest_to_aveiro(self, rcm_d0_data: dict) -> None:
        # Aveiro coords should match DICO 0101 (lat=40.58, lon=-8.44)
        dico = find_nearest_dico(40.60, -8.45, rcm_d0_data)
        assert dico == "0101"

    def test_nearest_to_faro(self, rcm_d0_data: dict) -> None:
        # Faro coords should match DICO 0801 (lat=37.02, lon=-7.93)
        dico = find_nearest_dico(37.00, -7.90, rcm_d0_data)
        assert dico == "0801"

    def test_empty_data(self) -> None:
        assert find_nearest_dico(38.72, -9.14, {}) is None

    def test_empty_local(self) -> None:
        assert find_nearest_dico(38.72, -9.14, {"local": {}}) is None

    def test_entry_missing_coords(self) -> None:
        data = {"local": {"9999": {"dico": "9999"}}}
        assert find_nearest_dico(38.72, -9.14, data) is None


class TestFindNearestAreaAviso:
    """Tests for IPMA warning area lookup."""

    def test_lisbon(self) -> None:
        code = find_nearest_area_aviso(38.72, -9.14)
        assert code == "LSB"

    def test_porto(self) -> None:
        code = find_nearest_area_aviso(41.15, -8.61)
        assert code == "PRT"

    def test_faro(self) -> None:
        code = find_nearest_area_aviso(37.02, -7.93)
        assert code == "FAR"

    def test_braga(self) -> None:
        code = find_nearest_area_aviso(41.55, -8.43)
        assert code == "BRG"

    def test_madeira(self) -> None:
        code = find_nearest_area_aviso(32.65, -16.90)
        assert code in ("MCS", "MCN", "MRM")  # Southern Madeira coast

    def test_all_area_codes_have_coords(self) -> None:
        for code, (name, lat, lon) in AREA_AVISO_COORDS.items():
            assert isinstance(code, str)
            assert len(code) == 3
            assert isinstance(name, str)
            assert isinstance(lat, float)
            assert isinstance(lon, float)
