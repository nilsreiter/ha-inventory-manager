"""config flow for inventory manager."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback

from .const import (
    CONF_ITEM_AGENT,
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_VENDOR,
    CONF_ITEM_UNIT,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
)

from .options_flow import InventoryOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ITEM_NAME): cv.string,
        vol.Optional(CONF_ITEM_SIZE): cv.string,
        vol.Optional(CONF_ITEM_UNIT): cv.string,
        vol.Optional(CONF_ITEM_AGENT): cv.string,
        vol.Optional(CONF_ITEM_VENDOR): cv.string,
        vol.Required(CONF_ITEM_MAX_CONSUMPTION, default=5): cv.positive_float,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
    }
)


class InventoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    data: dict[str, Any] | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Bla."""

        errors: dict[str, str] = {}
        if user_input is not None:
            # Input is valid, set data.
            self.data = user_input

            # Create title
            title = user_input[CONF_ITEM_NAME]
            if CONF_ITEM_SIZE in user_input:
                title += " " + user_input[CONF_ITEM_SIZE]
            if CONF_ITEM_UNIT in user_input:
                title += user_input[CONF_ITEM_UNIT]

            # Unchangeable info
            data = {}
            data[CONF_ITEM_NAME] = user_input[CONF_ITEM_NAME]

            # Changeable
            options = {}
            if CONF_ITEM_AGENT in user_input:
                options[CONF_ITEM_AGENT] = user_input[CONF_ITEM_AGENT]
            if CONF_ITEM_VENDOR in user_input:
                options[CONF_ITEM_VENDOR] = user_input[CONF_ITEM_VENDOR]
            options[CONF_SENSOR_BEFORE_EMPTY] = user_input[CONF_SENSOR_BEFORE_EMPTY]
            if CONF_ITEM_MAX_CONSUMPTION in user_input:
                options[CONF_ITEM_MAX_CONSUMPTION] = user_input[
                    CONF_ITEM_MAX_CONSUMPTION
                ]
            if CONF_ITEM_SIZE in user_input:
                options[CONF_ITEM_SIZE] = user_input[CONF_ITEM_SIZE]
            if CONF_ITEM_UNIT in user_input:
                options[CONF_ITEM_UNIT] = user_input[CONF_ITEM_UNIT]

            return self.async_create_entry(title=title, data=data, options=options)

        return self.async_show_form(
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> InventoryOptionsFlowHandler:
        """Create the options flow."""
        return InventoryOptionsFlowHandler(config_entry)
