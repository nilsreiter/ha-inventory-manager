"""Inventory manager integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    CONF_ITEM_VENDOR,
    DOMAIN,
)
from .coordinator import InventoryManagerItem
from .data import (
    InventoryManagerConfigEntry,
    InventoryManagerData,
)

if TYPE_CHECKING:
    from homeassistant import core


_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[str] = [Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: InventoryManagerConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = InventoryManagerItem(
        entry, hass, logger=_LOGGER, name=DOMAIN, update_interval=timedelta(hours=1)
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.runtime_data = InventoryManagerData(
        device_info=DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=entry.data.get(CONF_ITEM_VENDOR),
            entry_type=DeviceEntryType.SERVICE,
            name=entry.title,
        ),
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener to handle option changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: InventoryManagerConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: core.HomeAssistant, entry: InventoryManagerConfigEntry
) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
