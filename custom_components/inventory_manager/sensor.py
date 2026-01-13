"""
Sensor platform for inventory manager.

The sensor predicts when we run out of supplies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers import entity_platform
from homeassistant.util.dt import now

from .const import (
    ATTR_DAYS_REMAINING,
    ENTITY_ID,
    STRING_SENSOR_ENTITY,
    UNIQUE_ID,
)
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    # TODO: Switch to the use of entity descriptions
    sensors = [EmptyPredictionSensor(config_entry.runtime_data.coordinator)]
    async_add_entities(sensors, update_before_add=True)


class EmptyPredictionSensor(InventoryManagerEntity, SensorEntity):
    """Represents a sensor to predict when we run out of supplies."""

    _attr_has_entity_name = True
    _attr_name = "Supply empty"

    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, item: InventoryManagerItem) -> None:
        """Construct a new EmptyPredictionSensor."""
        super().__init__(item)
        _LOGGER.debug("Initializing EmptyPredictionSensor")

        self.platform = entity_platform.async_get_current_platform()

        self.coordinator.entity[InventoryManagerEntityType.EMPTYPREDICTION] = self

        entity_config: dict = item.entity_config[
            InventoryManagerEntityType.EMPTYPREDICTION
        ]

        self._available = True
        self.unique_id = entity_config[UNIQUE_ID]
        self._attr_extra_state_attributes = {}
        self.entity_id = entity_config[ENTITY_ID]
        self._attr_native_value: datetime = now() + timedelta(days=10000)

        self.device_class = SensorDeviceClass.TIMESTAMP
        self.translation_key = STRING_SENSOR_ENTITY

    def update(self) -> None:
        """Recalculate the remaining time until supply is empty."""
        _LOGGER.debug("Updating sensor")

        self._attr_extra_state_attributes[ATTR_DAYS_REMAINING] = (
            self.coordinator.days_remaining()
        )
        self._attr_native_value = now() + timedelta(
            days=self.coordinator.days_remaining()
        )
        _LOGGER.debug(
            "Setting native value of %s to %s", self.entity_id, self._attr_native_value
        )
        self._available = True
        self.schedule_update_ha_state()
