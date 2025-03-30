"""Options flow."""
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_ITEM_SIZE,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_UNIT,
    CONF_SENSOR_BEFORE_EMPTY,
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ITEM_SIZE): cv.string,
        vol.Optional(CONF_ITEM_UNIT): cv.string,
        vol.Required(CONF_ITEM_MAX_CONSUMPTION, default=5): cv.positive_float,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
    }
)


class InventoryOptionsFlowHandler(config_entries.OptionsFlow):
    """Flow handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Create a new options flow handler."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""

        # User has entered something
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Form is shown
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self._config_entry.options
            ),
        )
