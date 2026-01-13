"""config flow for inventory manager."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ITEM_AGENT,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_ITEM_UNIT,
    CONF_ITEM_VENDOR,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PILL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ITEM_NAME): cv.string,
        vol.Optional(CONF_ITEM_SIZE): cv.string,
        vol.Required(CONF_ITEM_UNIT): cv.string,
        vol.Optional(CONF_ITEM_AGENT): cv.string,
        vol.Optional(CONF_ITEM_VENDOR): cv.string,
        vol.Optional(CONF_ITEM_MAX_CONSUMPTION): cv.string,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
    }
)
# TODO: Add validation to ensure max consumption is a number if provided.
# TODO: Add option to select platforms to enable/disable.


class InventoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    data: dict[str, Any] | None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return InventoryOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Bla."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Input is valid, set data.
            self.data = user_input
            # Return the form of the next step.
            title = self.data[CONF_ITEM_NAME]
            if CONF_ITEM_SIZE in self.data:
                title += " " + self.data.get(CONF_ITEM_SIZE, "")
            return self.async_create_entry(
                title=title,
                data=self.data,
            )

        return self.async_show_form(
            step_id="user", data_schema=PILL_SCHEMA, errors=errors
        )


class InventoryOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Inventory Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry with new data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **user_input},
            )
            return self.async_create_entry(title="", data={})

        # Get current values from config entry
        current_data = self.config_entry.data

        # Create schema with current values as defaults
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_ITEM_NAME,
                    default=current_data.get(CONF_ITEM_NAME, ""),
                ): cv.string,
                vol.Optional(
                    CONF_ITEM_SIZE,
                    default=current_data.get(CONF_ITEM_SIZE, ""),
                ): cv.string,
                vol.Required(
                    CONF_ITEM_UNIT,
                    default=current_data.get(CONF_ITEM_UNIT, ""),
                ): cv.string,
                vol.Optional(
                    CONF_ITEM_AGENT,
                    default=current_data.get(CONF_ITEM_AGENT, ""),
                ): cv.string,
                vol.Optional(
                    CONF_ITEM_VENDOR,
                    default=current_data.get(CONF_ITEM_VENDOR, ""),
                ): cv.string,
                vol.Optional(
                    CONF_ITEM_MAX_CONSUMPTION,
                    default=current_data.get(CONF_ITEM_MAX_CONSUMPTION, ""),
                ): cv.string,
                vol.Required(
                    CONF_SENSOR_BEFORE_EMPTY,
                    default=current_data.get(CONF_SENSOR_BEFORE_EMPTY, 10),
                ): cv.positive_int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
