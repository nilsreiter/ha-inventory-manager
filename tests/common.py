"""Helpers for the Inventory Manager tests."""

from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.inventory_manager.const import (
    CONF_ITEM_ID,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_NAME,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
)


def item_entry(name: str = "Pills", **data: Any) -> MockConfigEntry:
    """Create a config entry for an item, as created by the current version."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=name,
        data={
            CONF_ITEM_NAME: name,
            CONF_ITEM_ID: name,
            CONF_ITEM_MAX_CONSUMPTION: 5.0,
            CONF_SENSOR_BEFORE_EMPTY: 10,
            **data,
        },
        version=1,
        minor_version=2,
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add a config entry and set it up."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def state(hass: HomeAssistant, entity_id: str) -> str:
    """Return the state of an entity, which must exist."""
    entity_state = hass.states.get(entity_id)
    assert entity_state is not None, entity_id
    return entity_state.state
