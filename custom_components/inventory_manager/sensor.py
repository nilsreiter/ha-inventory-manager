"""Sensor platform for inventory manager.

The sensor predicts when we run out of supplies.
"""
import logging

from datetime import datetime, timedelta

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.util.dt import now
from homeassistant.helpers import entity_platform

from . import InventoryManagerItem, InventoryManagerEntityType
from .const import (
    ATTR_DAYS_REMAINING,
    DOMAIN,
    ENTITY_ID,
    STRING_SENSOR_ENTITY,
    UNIQUE_ID,
)


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up sensors from a config entry created in the integrations UI."""

    config = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [EmptyPredictionSensor(hass, config)]
    async_add_entities(sensors, update_before_add=True)


class EmptyPredictionSensor(SensorEntity):
    """Represents a sensor to predict when we run out of supplies, given our daily consumption."""

    _attr_has_entity_name = True
    _attr_name = "Supply empty"

    should_poll = False
    device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, hass: core.HomeAssistant, item: InventoryManagerItem) -> None:
        """Construct a new EmptyPredictionSensor."""
        _LOGGER.debug("Initializing ConsumptionSensor")

        self.hass = hass
        self.item = item
        self.platform = entity_platform.async_get_current_platform()

        self.item.entity[InventoryManagerEntityType.EMPTYPREDICTION] = self

        entity_config: dict = item.entity_config[
            InventoryManagerEntityType.EMPTYPREDICTION
        ]

        self._device_id = item.device_id
        self._available = True
        self.device_info = item.device_info
        self.unique_id = entity_config[UNIQUE_ID]
        self.extra_state_attributes = {}
        self.entity_id = entity_config[ENTITY_ID]
        self.native_value: datetime = now() + timedelta(days=10000)

        self.device_class = SensorDeviceClass.TIMESTAMP
        self.translation_key = STRING_SENSOR_ENTITY

    def update(self):
        """Recalculate the remaining time until supply is empty."""
        _LOGGER.debug("Updating sensor")

        self.extra_state_attributes[ATTR_DAYS_REMAINING] = self.item.days_remaining()
        self.native_value = now() + timedelta(days=self.item.days_remaining())
        _LOGGER.debug(
            "Setting native value of %s to %s", self.entity_id, self.native_value
        )
        self.available = True
        self.schedule_update_ha_state()
