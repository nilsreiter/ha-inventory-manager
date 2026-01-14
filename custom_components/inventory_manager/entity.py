"""Entity classes for Inventory Manager integration."""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from .coordinator import InventoryManagerItem


class InventoryManagerEntityType(IntFlag):
    """Supported features of the number entities."""

    SUPPLY = 1
    NIGHT = 4
    MORNING = 8
    NOON = 32
    EVENING = 64
    WARNING = 128
    EMPTYPREDICTION = 256
    WEEK = 512
    MONTH = 1024


class InventoryManagerEntity(CoordinatorEntity, Entity):
    """Base Inventory Manager Entity."""

    def __init__(self, coordinator: InventoryManagerItem) -> None:
        """Create a new object."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.config_entry.runtime_data.device_info
        self.coordinator: InventoryManagerItem = coordinator

    def _handle_coordinator_update(self) -> None:
        return super()._handle_coordinator_update()
