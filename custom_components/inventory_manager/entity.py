"""Entity classes for Inventory Manager integration."""

from __future__ import annotations

from enum import IntFlag
from typing import TYPE_CHECKING

from homeassistant.core import callback
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

    entity_type: InventoryManagerEntityType

    def __init__(self, coordinator: InventoryManagerItem) -> None:
        """Create a new object."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.config_entry.runtime_data.device_info
        self.coordinator: InventoryManagerItem = coordinator

    def _handle_coordinator_update(self) -> None:
        return super()._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Register with the item once the entity can write its state."""
        await super().async_added_to_hass()
        self.coordinator.entity[self.entity_type] = self
        self._update_from_item()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from the item."""
        self.coordinator.entity.pop(self.entity_type, None)
        await super().async_will_remove_from_hass()

    def _update_from_item(self) -> None:
        """Recalculate the state from the numbers of the item."""

    @callback
    def async_item_updated(self) -> None:
        """Recalculate and write the state after the numbers of the item changed."""
        self._update_from_item()
        self.async_write_ha_state()
