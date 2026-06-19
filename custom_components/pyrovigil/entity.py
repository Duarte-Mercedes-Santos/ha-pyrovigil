"""Base entity for Pyrovigil."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN


class PyrovigilEntity(CoordinatorEntity):
    """Base class for Pyrovigil entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Pyrovigil",
            manufacturer="ANEPC / IPMA",
            model="Wildfire Monitor",
            entry_type=DeviceEntryType.SERVICE,
        )
