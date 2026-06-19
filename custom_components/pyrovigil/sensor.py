"""Sensor platform for Pyrovigil."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, MAX_FIRES_IN_ATTRIBUTES, RCM_LABELS
from .entity import PyrovigilEntity
from .models import (
    AirQualityData,
    AnepcData,
    FireRiskData,
    FirmsData,
    WeatherWarningData,
    WindData,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pyrovigil sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    anepc = data["anepc"]
    fire_risk = data["fire_risk"]
    warnings = data["warnings"]
    radius = entry.options.get("radius", entry.data.get("radius", 25))

    entities = [
        ActiveFiresSensor(anepc, entry, radius),
        NearestFireSensor(anepc, entry),
        TotalPersonnelSensor(anepc, entry),
        TotalGroundVehiclesSensor(anepc, entry),
        TotalAircraftSensor(anepc, entry),
        FireRiskSensor(fire_risk, entry),
        FireRiskTomorrowSensor(fire_risk, entry),
        WeatherWarningsSensor(warnings, entry),
    ]

    wind = data["wind"]
    entities.append(WindSensor(wind, entry))

    entities.append(FiresThisWeekSensor(anepc, entry))
    entities.append(FiresThisMonthSensor(anepc, entry))
    entities.append(ClosestFireRecordSensor(anepc, entry))

    firms = data.get("firms")
    if firms is not None:
        entities.append(FirmsHotspotsSensor(firms, entry))
        entities.append(NearestHotspotSensor(firms, entry))

    air_quality = data.get("air_quality")
    if air_quality is not None:
        entities.append(AirQualitySensor(air_quality, entry))

    async_add_entities(entities)


class ActiveFiresSensor(PyrovigilEntity, SensorEntity):
    """Number of active fires within radius."""

    _attr_icon = "mdi:fire-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = None

    def __init__(
        self, coordinator: DataUpdateCoordinator, entry: ConfigEntry, radius_km: int
    ) -> None:
        super().__init__(coordinator, entry)
        self._radius_km = radius_km
        self._attr_unique_id = f"{entry.entry_id}_active_fires"
        self._attr_name = "Active fires"

    @property
    def native_value(self) -> int:
        data: AnepcData = self.coordinator.data
        return len(data.fires)

    @property
    def extra_state_attributes(self) -> dict:
        data: AnepcData = self.coordinator.data
        return {
            "fires": [f.to_dict() for f in data.fires[:MAX_FIRES_IN_ATTRIBUTES]],
            "radius_km": self._radius_km,
        }


class NearestFireSensor(PyrovigilEntity, SensorEntity):
    """Distance to the nearest fire."""

    _attr_icon = "mdi:fire"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_nearest_fire"
        self._attr_name = "Nearest fire"

    @property
    def native_value(self) -> float | None:
        data: AnepcData = self.coordinator.data
        if data.nearest_fire is None:
            return None
        return round(data.nearest_fire.distance_km, 1)

    @property
    def extra_state_attributes(self) -> dict:
        data: AnepcData = self.coordinator.data
        if data.nearest_fire is None:
            return {}
        return data.nearest_fire.to_dict()


class TotalPersonnelSensor(PyrovigilEntity, SensorEntity):
    """Total personnel deployed to nearby fires."""

    _attr_icon = "mdi:account-group"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_personnel"
        self._attr_name = "Total personnel"

    @property
    def native_value(self) -> int:
        data: AnepcData = self.coordinator.data
        return data.total_personnel


class TotalGroundVehiclesSensor(PyrovigilEntity, SensorEntity):
    """Total ground vehicles deployed to nearby fires."""

    _attr_icon = "mdi:fire-truck"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_ground_vehicles"
        self._attr_name = "Total ground vehicles"

    @property
    def native_value(self) -> int:
        data: AnepcData = self.coordinator.data
        return data.total_ground_vehicles


class TotalAircraftSensor(PyrovigilEntity, SensorEntity):
    """Total aircraft deployed to nearby fires."""

    _attr_icon = "mdi:helicopter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_aircraft"
        self._attr_name = "Total aircraft"

    @property
    def native_value(self) -> int:
        data: AnepcData = self.coordinator.data
        return data.total_aircraft


class FireRiskSensor(PyrovigilEntity, SensorEntity):
    """Fire risk level (RCM) for today."""

    _attr_icon = "mdi:fire-circle"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fire_risk"
        self._attr_name = "Fire risk"

    @property
    def native_value(self) -> int | None:
        data: FireRiskData = self.coordinator.data
        if data.today is None:
            return None
        return data.today.rcm

    @property
    def extra_state_attributes(self) -> dict:
        data: FireRiskData = self.coordinator.data
        if data.today is None:
            return {}
        return {
            "risk_label": RCM_LABELS.get(data.today.rcm, "Desconhecido"),
            "dico_code": data.dico_code,
            "forecast_date": data.forecast_date,
        }


class FireRiskTomorrowSensor(PyrovigilEntity, SensorEntity):
    """Fire risk level (RCM) for tomorrow."""

    _attr_icon = "mdi:fire-circle"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fire_risk_tomorrow"
        self._attr_name = "Fire risk tomorrow"

    @property
    def native_value(self) -> int | None:
        data: FireRiskData = self.coordinator.data
        if data.tomorrow is None:
            return None
        return data.tomorrow.rcm

    @property
    def extra_state_attributes(self) -> dict:
        data: FireRiskData = self.coordinator.data
        if data.tomorrow is None:
            return {}
        return {
            "risk_label": RCM_LABELS.get(data.tomorrow.rcm, "Desconhecido"),
            "dico_code": data.dico_code,
        }


class WeatherWarningsSensor(PyrovigilEntity, SensorEntity):
    """Number of active weather warnings for the user's area."""

    _attr_icon = "mdi:weather-lightning"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_weather_warnings"
        self._attr_name = "Weather warnings"

    @property
    def native_value(self) -> int:
        data: WeatherWarningData = self.coordinator.data
        return len(data.warnings)

    @property
    def extra_state_attributes(self) -> dict:
        data: WeatherWarningData = self.coordinator.data
        return {
            "highest_level": data.highest_level,
            "warnings": [w.to_dict() for w in data.warnings],
        }


class FirmsHotspotsSensor(PyrovigilEntity, SensorEntity):
    """Number of NASA FIRMS satellite hotspots nearby."""

    _attr_icon = "mdi:satellite-variant"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_firms_hotspots"
        self._attr_name = "Satellite hotspots"

    @property
    def native_value(self) -> int:
        data: FirmsData = self.coordinator.data
        return data.count

    @property
    def extra_state_attributes(self) -> dict:
        data: FirmsData = self.coordinator.data
        return {
            "nearest_hotspot_km": (
                round(data.nearest_hotspot_km, 1) if data.nearest_hotspot_km is not None else None
            ),
        }


class NearestHotspotSensor(PyrovigilEntity, SensorEntity):
    """Distance to the nearest NASA FIRMS satellite hotspot."""

    _attr_icon = "mdi:satellite-variant"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_suggested_display_precision = 1
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_nearest_hotspot"
        self._attr_name = "Nearest satellite hotspot"

    @property
    def native_value(self) -> float | None:
        data: FirmsData = self.coordinator.data
        return round(data.nearest_hotspot_km, 1) if data.nearest_hotspot_km is not None else None


class WindSensor(PyrovigilEntity, SensorEntity):
    """Wind conditions at the nearest weather station."""

    _attr_icon = "mdi:weather-windy"
    _attr_native_unit_of_measurement = "km/h"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_wind"
        self._attr_name = "Wind speed"

    @property
    def native_value(self) -> float:
        data: WindData = self.coordinator.data
        return data.speed_kmh

    @property
    def extra_state_attributes(self) -> dict:
        data: WindData = self.coordinator.data
        return {
            "direction": data.direction_label,
            "direction_degrees": data.direction_degrees,
            "station": data.station_name,
            "station_distance_km": round(data.station_distance_km, 1),
        }


class AirQualitySensor(PyrovigilEntity, SensorEntity):
    """Air Quality Index from AQICN."""

    _attr_icon = "mdi:air-filter"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_air_quality"
        self._attr_name = "Air quality index"

    @property
    def native_value(self) -> int | None:
        data: AirQualityData = self.coordinator.data
        return data.aqi

    @property
    def extra_state_attributes(self) -> dict:
        data: AirQualityData = self.coordinator.data
        return {
            "dominant_pollutant": data.dominant_pollutant,
            "station": data.station_name,
            "pm25": data.pm25,
            "pm10": data.pm10,
        }


class FiresThisWeekSensor(PyrovigilEntity, SensorEntity):
    """Cumulative count of unique fires detected this week."""

    _attr_icon = "mdi:calendar-week"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fires_this_week"
        self._attr_name = "Fires this week"
        self._seen_ids: set[str] = set()
        self._week_number: int = -1

    @property
    def native_value(self) -> int:
        from datetime import datetime

        data: AnepcData = self.coordinator.data
        now = datetime.now()
        current_week = now.isocalendar()[1]

        if current_week != self._week_number:
            self._seen_ids.clear()
            self._week_number = current_week

        for fire in data.fires:
            self._seen_ids.add(fire.fire_id)

        return len(self._seen_ids)


class FiresThisMonthSensor(PyrovigilEntity, SensorEntity):
    """Cumulative count of unique fires detected this month."""

    _attr_icon = "mdi:calendar-month"
    _attr_state_class = SensorStateClass.TOTAL
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fires_this_month"
        self._attr_name = "Fires this month"
        self._seen_ids: set[str] = set()
        self._current_month: int = -1

    @property
    def native_value(self) -> int:
        from datetime import datetime

        data: AnepcData = self.coordinator.data
        now = datetime.now()

        if now.month != self._current_month:
            self._seen_ids.clear()
            self._current_month = now.month

        for fire in data.fires:
            self._seen_ids.add(fire.fire_id)

        return len(self._seen_ids)


class ClosestFireRecordSensor(PyrovigilEntity, SensorEntity):
    """Distance of the closest fire ever recorded by this instance."""

    _attr_icon = "mdi:map-marker-alert"
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_suggested_display_precision = 1
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_closest_fire_record"
        self._attr_name = "Closest fire ever"
        self._closest_km: float | None = None
        self._closest_fire_id: str = ""

    @property
    def native_value(self) -> float | None:
        data: AnepcData = self.coordinator.data
        if data.nearest_fire is not None:
            dist = data.nearest_fire.effective_distance_km
            if self._closest_km is None or dist < self._closest_km:
                self._closest_km = dist
                self._closest_fire_id = data.nearest_fire.fire_id
        return round(self._closest_km, 1) if self._closest_km is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        return {"fire_id": self._closest_fire_id}
