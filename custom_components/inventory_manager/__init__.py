"""Inventory manager integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from slugify import slugify

from .const import SPACE

from homeassistant.const import Platform
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .entity import InventoryManagerEntityType

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


PLATFORMS: list[str] = [
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]


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
    await _async_migrate_unique_ids(hass, entry)
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


async def _async_migrate_unique_ids(hass, entry) -> None:
    """Move entities from title-based unique IDs to entry_id-based ones."""
    ent_reg = er.async_get(hass)

    @callback
    def _migrate(entity_entry: er.RegistryEntry):
        for entity_type in InventoryManagerEntityType:
            if entity_entry.unique_id != slugify(
                entry.title + SPACE + entity_type.name
            ):
                continue
            new_id = slugify(entry.entry_id + "_" + entity_type.name)
            if ent_reg.async_get_entity_id(entity_entry.domain, DOMAIN, new_id):
                _LOGGER.warning(
                    "Not migrating %s: unique ID %s is already used by another entity",
                    entity_entry.entity_id,
                    new_id,
                )
                return None
            return {"new_unique_id": new_id}
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)
