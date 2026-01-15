"""Binary sensor entity to indicate the need to resupply."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_platform

from .const import (
    CONF_SENSOR_BEFORE_EMPTY,
    ENTITY_ID,
    STRING_PROBLEM_ENTITY,
    UNIQUE_ID,
)
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from homeassistant import core

    from .coordinator import (
        InventoryManagerConfigEntry,
        InventoryManagerItem,
    )

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: core.HomeAssistant,
    config_entry: InventoryManagerConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    # TODO: Switch to the use of entity descriptions
    async_add_entities(
        [WarnSensor(config_entry.runtime_data.coordinator)], update_before_add=True
    )


# TODO: Add tests for this entity.
# TODO: Verify that attributes are correctly set and updated.
class WarnSensor(InventoryManagerEntity, BinarySensorEntity):
    """Represents a warning entity."""

    _attr_has_entity_name = True

    def __init__(self, item: InventoryManagerItem) -> None:
        """Create a new object."""
        super().__init__(item)
        _LOGGER.debug("Initializing WarnSensor")
        self.coordinator.entity[InventoryManagerEntityType.WARNING] = self
        self.platform = entity_platform.async_get_current_platform()

        self._attr_should_poll = False
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_unique_id = self.coordinator.entity_config[
            InventoryManagerEntityType.WARNING
        ][UNIQUE_ID]

        self.translation_key = STRING_PROBLEM_ENTITY
        self._attr_available = False
        self.is_on = False
        self.entity_id = item.entity_config[InventoryManagerEntityType.WARNING][
            ENTITY_ID
        ]

    async def async_added_to_hass(self) -> None:
        """Call update to get initial state after entity is added."""
        await super().async_added_to_hass()
        self.update()

    def update(self) -> None:
        """Update the state of the entity."""
        _LOGGER.debug("Updating binary sensor")

        days_remaining = self.coordinator.days_remaining()
        if days_remaining == STATE_UNAVAILABLE:
            self.is_on = False
            self._attr_available = False
        else:
            self._attr_available = True
            self.is_on = days_remaining < self.coordinator.config_entry.data.get(
                CONF_SENSOR_BEFORE_EMPTY, 0
            )
        self.schedule_update_ha_state()
