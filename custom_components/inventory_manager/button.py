"""Button entities for inventory manager."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant import config_entries, core
from homeassistant.components.button import ButtonEntity

from .const import DOMAIN
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: InventoryManagerItem = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([FillButton(coordinator)], update_before_add=False)


class FillButton(InventoryManagerEntity, ButtonEntity):
    """Button to fill supply by one package quantity."""

    def __init__(self, item: InventoryManagerItem) -> None:
        super().__init__(item)
        self._attr_name = "Fill"
        self._attr_unique_id = f"{item.config_entry.entry_id}_fill_button"
        self._attr_icon = "mdi:package-variant-plus"

    def press(self) -> None:
        """Handle the button press."""
        size_entity = self.coordinator.entity.get(
            InventoryManagerEntityType.PACKAGE_QUANTITY
        )
        if size_entity is not None and size_entity.native_value > 0:
            self.coordinator.take_number(-1 * size_entity.native_value)
        else:
            _LOGGER.warning("Fill button pressed but package quantity is 0 or not set")
