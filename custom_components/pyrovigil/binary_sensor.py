"""Binary sensor platform for Pyrovigil."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_HIGH_RISK_THRESHOLD, DEFAULT_HIGH_RISK_THRESHOLD, DOMAIN
from .entity import PyrovigilEntity
from .models import AnepcData, FireRiskData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pyrovigil binary sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    anepc = data["anepc"]
    fire_risk = data["fire_risk"]
    threshold = entry.options.get(CONF_HIGH_RISK_THRESHOLD, DEFAULT_HIGH_RISK_THRESHOLD)

    async_add_entities(
        [
            FireNearbyBinarySensor(anepc, entry),
            HighFireRiskBinarySensor(fire_risk, entry, threshold),
        ]
    )


class FireNearbyBinarySensor(PyrovigilEntity, BinarySensorEntity):
    """Binary sensor indicating whether any fire is nearby."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:fire-alert"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fire_nearby"
        self._attr_name = "Fire nearby"

    @property
    def is_on(self) -> bool:
        data: AnepcData = self.coordinator.data
        return len(data.fires) > 0

    @property
    def extra_state_attributes(self) -> dict:
        data: AnepcData = self.coordinator.data
        return {
            "count": len(data.fires),
            "nearest_distance_km": (
                round(data.nearest_fire.distance_km, 1) if data.nearest_fire else None
            ),
        }


class HighFireRiskBinarySensor(PyrovigilEntity, BinarySensorEntity):
    """Binary sensor indicating high fire risk (RCM >= threshold)."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_icon = "mdi:fire-circle"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        threshold: int,
    ) -> None:
        super().__init__(coordinator, entry)
        self._threshold = threshold
        self._attr_unique_id = f"{entry.entry_id}_high_fire_risk"
        self._attr_name = "High fire risk"

    @property
    def is_on(self) -> bool:
        data: FireRiskData = self.coordinator.data
        if data.today is None:
            return False
        return data.today.rcm >= self._threshold

    @property
    def extra_state_attributes(self) -> dict:
        data: FireRiskData = self.coordinator.data
        rcm = data.today.rcm if data.today else None
        return {
            "risk_level": rcm,
            "threshold": self._threshold,
            "dico_code": data.dico_code,
        }
