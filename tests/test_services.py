"""Tests for the consume and store actions."""

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from custom_components.inventory_manager.const import DOMAIN

from .common import item_entry, setup_entry, state


async def _call(hass: HomeAssistant, action: str, data: dict) -> None:
    await hass.services.async_call(DOMAIN, action, data, blocking=True)


async def test_consume_and_store(hass: HomeAssistant) -> None:
    """Store and consume update the supply, prediction and warning."""
    await setup_entry(hass, item_entry())
    assert state(hass, "number.pills_supply") == "0.0"
    assert state(hass, "binary_sensor.pills_warning") == "off"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.pills_morning", "value": 1},
        blocking=True,
    )
    assert state(hass, "number.pills_morning") == "1.0"

    supply = {"entity_id": "number.pills_supply"}
    await _call(hass, "store", {**supply, "amount": 10})
    await _call(hass, "consume", {**supply, "amount": 0.5})
    await _call(hass, "consume", {**supply, "predefined-amount": "morning"})

    assert state(hass, "number.pills_supply") == "8.5"
    sensor = hass.states.get("sensor.pills_emptyprediction")
    assert sensor is not None
    assert sensor.attributes["days_remaining"] == 8.5
    assert state(hass, "binary_sensor.pills_warning") == "on"


@pytest.mark.parametrize(
    ("action", "data"),
    [
        ("consume", {}),
        ("consume", {"amount": 0}),
        ("consume", {"amount": -1}),
        ("consume", {"amount": 1, "predefined-amount": "noon"}),
        ("consume", {"predefined-amount": "evenign"}),
        ("store", {}),
        ("store", {"amount": 0}),
    ],
)
async def test_invalid_data(hass: HomeAssistant, action: str, data: dict) -> None:
    """Invalid amounts are rejected."""
    await setup_entry(hass, item_entry())
    with pytest.raises(vol.Invalid):
        await _call(hass, action, {"entity_id": "number.pills_supply", **data})


async def test_device_and_entity_targets(hass: HomeAssistant) -> None:
    """Items can be targeted by device or entity, and change once per call."""
    pills = item_entry("Pills")
    await setup_entry(hass, pills)
    await setup_entry(hass, item_entry("Drops"))

    [device] = dr.async_entries_for_config_entry(dr.async_get(hass), pills.entry_id)

    # A device target changes the item once, not once per entity
    await _call(hass, "store", {"device_id": device.id, "amount": 10})
    assert state(hass, "number.pills_supply") == "10.0"
    assert state(hass, "number.drops_supply") == "0.0"

    # Any entity of an item works, and the item still changes only once
    await _call(
        hass,
        "consume",
        {"device_id": device.id, "entity_id": ["number.pills_morning"], "amount": 1},
    )
    assert state(hass, "number.pills_supply") == "9.0"

    # Several items at once
    await _call(
        hass,
        "store",
        {"entity_id": ["number.pills_supply", "number.drops_supply"], "amount": 2},
    )
    assert state(hass, "number.pills_supply") == "11.0"
    assert state(hass, "number.drops_supply") == "2.0"


async def test_invalid_targets(hass: HomeAssistant) -> None:
    """Targets that are not loaded items are rejected."""
    drops = item_entry("Drops")
    await setup_entry(hass, drops)

    hass.states.async_set("light.kitchen", "on")
    with pytest.raises(ServiceValidationError):
        await _call(hass, "store", {"entity_id": "light.kitchen", "amount": 1})

    with pytest.raises(vol.Invalid):
        await _call(hass, "store", {"amount": 1})

    # The actions stay registered after unloading, but skip unloaded items
    assert await hass.config_entries.async_unload(drops.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, "consume")
    with pytest.raises(ServiceValidationError):
        await _call(hass, "store", {"entity_id": "number.drops_supply", "amount": 1})
