"""Binary sensor entity to indicate the need to resupply."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
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

SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="warning",
        translation_key=STRING_PROBLEM_ENTITY,
        device_class=BinarySensorDeviceClass.PROBLEM,
        has_entity_name=True,
    ),
)


async def async_setup_entry(
    _hass: core.HomeAssistant,
    config_entry: InventoryManagerConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    async_add_entities(
        [
            WarnSensor(config_entry.runtime_data.coordinator, description)
            for description in SENSOR_TYPES
        ],
    )


class WarnSensor(InventoryManagerEntity, BinarySensorEntity):
    """Represents a warning entity."""

    _attr_has_entity_name = True
    entity_type = InventoryManagerEntityType.WARNING

    def __init__(
        self, item: InventoryManagerItem, description: BinarySensorEntityDescription
    ) -> None:
        """Create a new object."""
        super().__init__(item)
        self.entity_description = description

        _LOGGER.debug("Initializing WarnSensor")
        self.platform = entity_platform.async_get_current_platform()

        self._attr_should_poll = False
        self._attr_unique_id = self.coordinator.entity_config[
            InventoryManagerEntityType.WARNING
        ][UNIQUE_ID]

        self._attr_is_on = False
        self.entity_id = item.entity_config[InventoryManagerEntityType.WARNING][
            ENTITY_ID
        ]

    def _update_from_item(self) -> None:
        """Update the state of the entity."""
        _LOGGER.debug("Updating binary sensor")

        days_remaining = self.coordinator.days_remaining()
        self._attr_is_on = days_remaining is not None and days_remaining < (
            self.coordinator.config_entry.data.get(CONF_SENSOR_BEFORE_EMPTY, 0)
        )
