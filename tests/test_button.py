"""Tests for the fill button."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.inventory_manager.const import DOMAIN

from .common import item_entry, setup_entry, state


async def test_fill_button(hass: HomeAssistant) -> None:
    """Pressing the button adds one package quantity to the supply."""
    pills = item_entry()
    await setup_entry(hass, pills)

    button = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"{pills.entry_id}_fill_button"
    )
    assert button is not None

    async def press() -> None:
        await hass.services.async_call(
            "button", "press", {"entity_id": button}, blocking=True
        )

    # Without a package quantity, pressing raises an error shown in the UI
    with pytest.raises(ServiceValidationError):
        await press()
    assert state(hass, "number.pills_supply") == "0.0"

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.pills_package_quantity", "value": 30},
        blocking=True,
    )
    await press()
    await press()

    assert state(hass, "number.pills_supply") == "60.0"
