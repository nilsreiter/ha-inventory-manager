"""Tests for the prediction and warning sensors."""

from homeassistant.core import HomeAssistant

from custom_components.inventory_manager.const import DOMAIN

from .common import item_entry, setup_entry, state


async def test_unknown_without_consumption(hass: HomeAssistant) -> None:
    """Without consumption, the prediction is unknown and there is no warning."""
    await setup_entry(hass, item_entry())
    await hass.services.async_call(
        DOMAIN,
        "store",
        {"entity_id": "number.pills_supply", "amount": 3},
        blocking=True,
    )

    sensor = hass.states.get("sensor.pills_emptyprediction")
    assert sensor is not None
    assert sensor.state == "unknown"
    assert sensor.attributes["days_remaining"] is None
    assert state(hass, "binary_sensor.pills_warning") == "off"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.pills_evening", "value": 1},
        blocking=True,
    )

    sensor = hass.states.get("sensor.pills_emptyprediction")
    assert sensor is not None
    assert sensor.state not in ("unknown", "unavailable")
    assert sensor.attributes["days_remaining"] == 3
    assert state(hass, "binary_sensor.pills_warning") == "on"
