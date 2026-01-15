"""Inventory manager integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import (
    CONF_ENABLED_PLATFORMS,
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_ITEM_VENDOR,
    DOMAIN,
    SPACE,
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
    friendly_name = entry.data[CONF_ITEM_NAME]
    if CONF_ITEM_SIZE in entry.data:
        friendly_name = friendly_name + SPACE + str(entry.data[CONF_ITEM_SIZE])

    entry.runtime_data = InventoryManagerData(
        device_info=DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=entry.data.get(CONF_ITEM_VENDOR),
            entry_type=DeviceEntryType.SERVICE,
            name=friendly_name,
        ),
        coordinator=coordinator,
    )

    # Use enabled platforms from config, or all platforms if not specified
    enabled_platforms = entry.data.get(CONF_ENABLED_PLATFORMS, PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, enabled_platforms)

    # Register update listener to handle option changes
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: InventoryManagerConfigEntry
) -> bool:
    """Unload a config entry."""
    # Use enabled platforms from config, or all platforms if not specified
    enabled_platforms = entry.data.get(CONF_ENABLED_PLATFORMS, PLATFORMS)
    return await hass.config_entries.async_unload_platforms(entry, enabled_platforms)


async def async_reload_entry(
    hass: core.HomeAssistant, entry: InventoryManagerConfigEntry
) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
