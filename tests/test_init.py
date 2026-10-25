"""Tests for setting up, restoring and migrating items."""

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.inventory_manager.const import (
    CONF_ITEM_ID,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
)

from .common import item_entry, setup_entry, state


def _number_data(native_value: float, max_value: float) -> dict:
    return {
        "native_value": native_value,
        "native_min_value": 0,
        "native_max_value": max_value,
        "native_step": 0.25,
        "native_unit_of_measurement": "pcs.",
    }


async def test_restore_int_supply(hass: HomeAssistant) -> None:
    """A supply that was stored as an int is restored, not reset to 0."""
    mock_restore_cache_with_extra_data(
        hass,
        [
            (State("number.pills_supply", "30"), _number_data(30, 1e6)),
            (State("number.pills_morning", "1"), _number_data(1.0, 5)),
        ],
    )
    await setup_entry(hass, item_entry())

    assert state(hass, "number.pills_supply") == "30.0"
    assert state(hass, "number.pills_morning") == "1.0"
    sensor = hass.states.get("sensor.pills_emptyprediction")
    assert sensor is not None
    assert sensor.attributes["days_remaining"] == 30


async def test_migration_keeps_unique_ids(hass: HomeAssistant) -> None:
    """Items from before version 1.2 keep their title-based unique ids."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Pills 30",
        data={
            CONF_ITEM_NAME: "Pills",
            CONF_ITEM_SIZE: 30,
            CONF_ITEM_MAX_CONSUMPTION: 5.0,
            CONF_SENSOR_BEFORE_EMPTY: 10,
        },
        version=1,
        minor_version=1,
    )
    await setup_entry(hass, entry)

    assert entry.minor_version == 2
    assert entry.data[CONF_ITEM_ID] == "Pills 30"
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("number", DOMAIN, "pills-30-supply")


async def test_reload(hass: HomeAssistant) -> None:
    """Values survive reloading the item, as after changing its options."""
    entry = item_entry()
    await setup_entry(hass, entry)
    await hass.services.async_call(
        DOMAIN,
        "store",
        {"entity_id": "number.pills_supply", "amount": 10},
        blocking=True,
    )

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    await hass.services.async_call(
        DOMAIN,
        "consume",
        {"entity_id": "number.pills_supply", "amount": 1},
        blocking=True,
    )
    assert state(hass, "number.pills_supply") == "9.0"
