"""config flow for inventory manager."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries

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
# TODO: Add option to change options after initial setup.
# TODO: Add option to select platforms to enable/disable.


class InventoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    data: dict[str, Any] | None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
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
