import logging
from typing import Any, Optional

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_PILL_AGENT,
    CONF_PILL_NAME,
    CONF_PILL_SIZE,
    CONF_PILL_VENDOR,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PILL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PILL_NAME): cv.string,
        vol.Optional(CONF_PILL_SIZE): cv.string,
        vol.Optional(CONF_PILL_AGENT): cv.string,
        vol.Optional(CONF_PILL_VENDOR): cv.string,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
    }
)


class InventoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    data: Optional[dict[str, Any]]

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """Bla."""

        errors: dict[str, str] = {}
        if user_input is not None:
            # Input is valid, set data.
            self.data = user_input
            # Return the form of the next step.
            title = self.data[CONF_PILL_NAME]
            if CONF_PILL_SIZE in self.data:
                title += " " + self.data.get(CONF_PILL_SIZE, "")
            return self.async_create_entry(
                title=title,
                data=self.data,
            )

        return self.async_show_form(
            step_id="user", data_schema=PILL_SCHEMA, errors=errors
        )
