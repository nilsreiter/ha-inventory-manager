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
from slugify import slugify

from .const import (
    CONF_ITEM_AGENT,
    CONF_ITEM_ID,
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
        if data.get(CONF_ITEM_UNIT):
            title += str(data[CONF_ITEM_UNIT])
    return title


INVENTORY_MANAGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ITEM_NAME): cv.string,
        vol.Required(CONF_ITEM_MAX_CONSUMPTION, default=5.0): cv.positive_float,
        vol.Required(CONF_SENSOR_BEFORE_EMPTY, default=10): cv.positive_int,
        vol.Optional(CONF_ITEM_SIZE): cv.positive_int,
        vol.Optional(CONF_ITEM_UNIT): cv.string,
        vol.Optional(CONF_ITEM_AGENT): cv.string,
        vol.Optional(CONF_ITEM_VENDOR): cv.string,
    }
)
INVENTORY_MANAGER_FIELDS = {marker.schema for marker in INVENTORY_MANAGER_SCHEMA.schema}


class InventoryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Inventory Manager integration."""

    VERSION = 1
    MINOR_VERSION = 2

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
        """Handle user step to configure the integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Input is valid, set data.
            self.data = {
                **user_input,
                CONF_ITEM_ID: self._new_item_id(user_input[CONF_ITEM_NAME]),
            }
            # Return the form of the next step.
            return self.async_create_entry(
                title=_build_entry_title(self.data),
                data=self.data,
            )

        return self.async_show_form(
            step_id="user", data_schema=INVENTORY_MANAGER_SCHEMA, errors=errors
        )

    def _new_item_id(self, name: str) -> str:
        """Derive an item id from the name that no other entry uses yet."""
        taken = {
            slugify(entry.data.get(CONF_ITEM_ID, ""))
            for entry in self._async_current_entries(include_ignore=False)
        }
        item_id = name
        suffix = 2
        while slugify(item_id) in taken:
            item_id = f"{name} {suffix}"
            suffix += 1
        return item_id


class InventoryOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Inventory Manager."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Keep data that is not part of the form (e.g. the item id), but
            # take all form fields from the input so cleared fields are removed
            data = {
                key: value
                for key, value in self.config_entry.data.items()
                if key not in INVENTORY_MANAGER_FIELDS
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=_build_entry_title(user_input),
                data={**data, **user_input},
            )
            # Return empty entry to signal completion (data is already saved above)
            return self.async_create_entry(title="", data={})

        # Same form as when creating the entry, pre-filled with current values
        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                INVENTORY_MANAGER_SCHEMA, current_data
            ),
            description_placeholders={
                "name": current_data.get(CONF_ITEM_NAME, "Item name")
            },
        )
