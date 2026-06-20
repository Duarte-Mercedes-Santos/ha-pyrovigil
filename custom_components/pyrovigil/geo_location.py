"""Geo-location platform for Pyrovigil — shows fires on the HA map."""

from __future__ import annotations

import logging

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import AnepcData, FireIncident

_LOGGER = logging.getLogger(__name__)
SOURCE = "pyrovigil"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pyrovigil geo_location entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["anepc"]
    manager = FireGeoLocationManager(coordinator, entry, async_add_entities)
    manager.start()


class FireGeoLocationManager:
    """Manages dynamic creation/removal of fire geo_location entities."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._tracked: dict[str, FireGeoLocationEvent] = {}

    def start(self) -> None:
        """Start listening for coordinator updates."""
        self._coordinator.async_add_listener(self._update)
        self._update()

    @callback
    def _update(self) -> None:
        """Handle coordinator data update — add/remove/update fire entities."""
        data: AnepcData = self._coordinator.data
        if data is None:
            return

        current_ids = {f.fire_id for f in data.fires}
        tracked_ids = set(self._tracked.keys())

        # Remove entities for fires that are no longer active
        for fire_id in tracked_ids - current_ids:
            entity = self._tracked.pop(fire_id)
            entity.async_remove()

        # Add new entities
        new_entities = []
        for fire in data.fires:
            if fire.fire_id not in self._tracked:
                entity = FireGeoLocationEvent(self._coordinator, self._entry, fire)
                self._tracked[fire.fire_id] = entity
                new_entities.append(entity)
            else:
                self._tracked[fire.fire_id].update_fire(fire)

        if new_entities:
            self._async_add_entities(new_entities)


class FireGeoLocationEvent(CoordinatorEntity, GeolocationEvent):
    """A fire shown on the HA map."""

    _attr_source = SOURCE

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        fire: FireIncident,
    ) -> None:
        super().__init__(coordinator)
        self._fire = fire
        self._attr_unique_id = f"{entry.entry_id}_geo_{fire.fire_id}"
        self._attr_name = f"🔥 {fire.concelho}"

    def update_fire(self, fire: FireIncident) -> None:
        """Update the fire data."""
        self._fire = fire
        self.async_write_ha_state()

    @property
    def latitude(self) -> float:
        return self._fire.latitude

    @property
    def longitude(self) -> float:
        return self._fire.longitude

    @property
    def distance(self) -> float:
        return round(self._fire.effective_distance_km, 1)

    @property
    def icon(self) -> str:
        return "mdi:fire"

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "fire_id": self._fire.fire_id,
            "nature": self._fire.nature,
            "status": self._fire.status,
            "severity": self._fire.severity,
            "personnel": self._fire.personnel,
            "ground_vehicles": self._fire.ground_vehicles,
            "aircraft": self._fire.aircraft,
            "resource_trend": self._fire.resource_trend,
            "distance_trend": self._fire.distance_trend,
        }
