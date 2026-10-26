"""Button entities for inventory manager."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant import config_entries, core
from homeassistant.components.button import ButtonEntity


if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InventoryManagerItem


async def async_setup_entry(
    _hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: InventoryManagerItem = config_entry.runtime_data.coordinator
    async_add_entities([FillButton(coordinator)], update_before_add=False)


class FillButton(ButtonEntity):
    """Button to fill supply by one package quantity."""

    def __init__(self, item: InventoryManagerItem) -> None:
        """Create the fill button."""
        self._item = item
        self._attr_device_info = item.config_entry.runtime_data.device_info
        self._attr_name = "Fill"
        self._attr_unique_id = f"{item.config_entry.entry_id}_fill_button"
        self._attr_icon = "mdi:package-variant-plus"

    async def async_press(self) -> None:
        """Add one package worth of supply."""
        self._item.fill()
