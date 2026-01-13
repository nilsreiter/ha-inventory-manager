"""Inventory manager integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from re import A
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from homeassistant.const import Platform
from homeassistant.helpers import device_registry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import generate_entity_id

from .const import (
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_ITEM_VENDOR,
    DOMAIN,
    ENTITY_ID,
    ENTITY_TYPE,
    SPACE,
    UNDERSCORE,
    UNIQUE_ID,
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


# TODO: Fix issues with device info creation.
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
            name=entry.data[CONF_ITEM_NAME] + " " + entry.data.get(CONF_ITEM_SIZE, ""),
        ),
        coordinator=coordinator,
    )

    friendly_name = entry.data[CONF_ITEM_NAME]
    if CONF_ITEM_SIZE in entry.data:
        friendly_name = friendly_name + SPACE + entry.data[CONF_ITEM_SIZE]
    # dr.async_get_or_create(
    #     config_entry_id=entry.entry_id,
    #     entry_type=item.device_info["entry_type"],
    #     manufacturer=item.device_info["manufacturer"],
    #     model=friendly_name,
    #     name=friendly_name,
    #     identifiers=item.device_info["identifiers"],
    # )
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

