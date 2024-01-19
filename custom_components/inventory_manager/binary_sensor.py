import logging

from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers import entity_platform
from homeassistant.const import STATE_UNAVAILABLE
from . import InventoryManagerItem, InventoryManagerEntityType
from .const import (
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
    STRING_PROBLEM_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [WarnSensor(hass, config)]
    async_add_entities(sensors, update_before_add=True)


class WarnSensor(BinarySensorEntity):
    """Represents a warning entity."""

    _attr_has_entity_name = True

    def __init__(self, hass: core.HomeAssistant, item: InventoryManagerItem):
        super().__init__()
        _LOGGER.debug("Initializing WarnSensor")
        self.hass = hass
        self.item: InventoryManagerItem = item
        self.item.entity[InventoryManagerEntityType.WARNING] = self
        self.platform = entity_platform.async_get_current_platform()

        self.device_id = item.device_id
        self.device_info = item.device_info

        self.should_poll = False
        self.device_class = BinarySensorDeviceClass.PROBLEM
        self.unique_id = item.entity_config[
            InventoryManagerEntityType.WARNING
        ].unique_id

        self.translation_key = STRING_PROBLEM_ENTITY
        self.available = False
        self.is_on = False
        self.entity_id = item.entity_config[
            InventoryManagerEntityType.WARNING
        ].entity_id

    def update(self):
        """Update the state of the entity."""
        _LOGGER.debug("Updating binary sensor")

        days_remaining = self.item.days_remaining()
        if days_remaining == STATE_UNAVAILABLE:
            self.is_on = False
            self.available = False
        else:
            self.available = True
            self.is_on = days_remaining < self.item.data[CONF_SENSOR_BEFORE_EMPTY]
        self.schedule_update_ha_state()
