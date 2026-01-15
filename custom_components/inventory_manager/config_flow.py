"""Config flow for inventory manager."""

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
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


def _build_entry_title(data: dict[str, Any]) -> str:
    """Build entry title from configuration data."""
    title = data.get(CONF_ITEM_NAME, "")
    if data.get(CONF_ITEM_SIZE):
        title += " " + str(data[CONF_ITEM_SIZE])
    return title


REQUIRED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ITEM_NAME): cv.string,
        vol.Required(CONF_ITEM_MAX_CONSUMPTION, default=5.0): cv.positive_float,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
    }
)

OPTIONAL_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ITEM_SIZE): cv.positive_int,
        vol.Optional(CONF_ITEM_UNIT): cv.string,
        vol.Optional(CONF_ITEM_AGENT): cv.string,
        vol.Optional(CONF_ITEM_VENDOR): cv.string,
    }
)
# TODO: Add option to select platforms to enable/disable.


class InventoryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Inventory Manager integration."""

    VERSION = 1
    MINOR_VERSION = 1

    data: dict[str, Any] | None

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return InventoryOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user step to configure the integration (required fields)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Store required fields and proceed to optional fields
            self.data = user_input
            return await self.async_step_optional()

        return self.async_show_form(
            step_id="user", data_schema=REQUIRED_SCHEMA, errors=errors
        )

    async def async_step_optional(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle optional fields step."""
        if user_input is not None:
            # Merge optional fields with required fields
            if self.data is None:
                self.data = {}
            self.data.update(user_input)
            # Create the entry with all data
            return self.async_create_entry(
                title=_build_entry_title(self.data),
                data=self.data,
            )

        return self.async_show_form(
            step_id="optional", data_schema=OPTIONAL_SCHEMA
        )


class InventoryOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Inventory Manager."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update config entry with new data (merging with existing)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=_build_entry_title(user_input),
                data={**self.config_entry.data, **user_input},
            )
            # Return empty entry to signal completion (data is already saved above)
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
                    default=current_data.get(CONF_ITEM_SIZE),
                ): cv.positive_int,
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
                    default=current_data.get(CONF_ITEM_MAX_CONSUMPTION, 5.0),
                ): cv.positive_float,
                vol.Required(
                    CONF_SENSOR_BEFORE_EMPTY,
                    default=current_data.get(CONF_SENSOR_BEFORE_EMPTY, 10),
                ): cv.positive_int,
            }
        )
        # TODO: Check if translations are complete for options flow.
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "name": current_data.get(CONF_ITEM_NAME, "Item name")
            },
        )
