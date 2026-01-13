"""Number entities for inventory manager."""

from __future__ import annotations

import logging
from abc import ABCMeta
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_platform

from .const import (
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_UNIT,
    DOMAIN,
    ENTITY_ID,
    NATIVE_VALUE,
    SERVICE_AMOUNT,
    SERVICE_AMOUNT_SPECIFICATION,
    SERVICE_CONSUME,
    SERVICE_PREDEFINED_AMOUNT,
    STRING_EVENING_ENTITY,
    STRING_MORNING_ENTITY,
    STRING_NIGHT_ENTITY,
    STRING_NOON_ENTITY,
    STRING_SUPPLY_ENTITY,
    UNIQUE_ID,
    UNIT_PCS,
)
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from types import NoneType

    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)


# TODO: Add option to change number parameters (min, max, step) from config flow.
# TODO: Use EntityDescription for number entities.
async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> NoneType:
    """Set up number entities and register service."""
    # Get the item object
    coordinator: InventoryManagerItem = hass.data[DOMAIN][config_entry.entry_id]

    # Create numeric entities
    entities = [
        SupplyEntity(coordinator),
        ConsumptionEntity(coordinator, InventoryManagerEntityType.MORNING),
        ConsumptionEntity(coordinator, InventoryManagerEntityType.NOON),
        ConsumptionEntity(coordinator, InventoryManagerEntityType.EVENING),
        ConsumptionEntity(coordinator, InventoryManagerEntityType.NIGHT),
    ]

    async_add_entities(entities, update_before_add=False)

    # Register service, if needed
    if not hass.services.has_service(DOMAIN, SERVICE_CONSUME):
        _LOGGER.debug("Registering service %s.%s", DOMAIN, SERVICE_CONSUME)
        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            SERVICE_CONSUME,
            {
                vol.Exclusive(
                    SERVICE_AMOUNT, SERVICE_AMOUNT_SPECIFICATION
                ): cv.positive_int,
                vol.Exclusive(
                    SERVICE_PREDEFINED_AMOUNT, SERVICE_AMOUNT_SPECIFICATION
                ): cv.string,
            },
            lambda target, payload: target.take(payload),
        )


class InventoryNumber(InventoryManagerEntity, RestoreNumber, metaclass=ABCMeta):
    """
    Represents a numeric entity.

    Abstract base class for several entities.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        item: InventoryManagerItem,
        entity_type: InventoryManagerEntityType,
    ) -> None:
        """Create a new number entity."""
        super().__init__(item)
        self.entity_type: InventoryManagerEntityType = entity_type

        # register self with the item object
        self.coordinator.entity[entity_type] = self

        entity_config: dict = item.entity_config[entity_type]
        self.entity_id: str = entity_config[ENTITY_ID]
        self.unique_id: str = entity_config[UNIQUE_ID]

        self._available: bool = True
        self._attr_native_unit_of_measurement = item.config_entry.data.get(
            CONF_ITEM_UNIT, UNIT_PCS
        )
        self._attr_native_step = 0.25
        self._attr_native_min_value = 0

    @property
    def native_value(self) -> float:
        """The native value."""
        return self.coordinator.get(self.entity_type)

    @native_value.setter
    def native_value(self, value: float) -> None:
        _LOGGER.debug("Setting native value of %s to %2.1f.", self.entity_id, value)
        self.coordinator.set(self.entity_type, value)
        self.schedule_update_ha_state()

    def set_native_value(self, value: float) -> None:
        """Set the native value."""
        self.native_value = value
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore the number from last time."""
        try:
            last_data = await self.async_get_last_number_data()
            if last_data is not None:
                last_number_data = last_data.as_dict()
                if isinstance(last_number_data[NATIVE_VALUE], float):
                    self.native_value = last_number_data[NATIVE_VALUE]
                else:
                    self.native_value = 0.0
        except AttributeError:
            self.set_native_value(0.0)
            self.schedule_update_ha_state()

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        if self.entity_type == InventoryManagerEntityType.MORNING:
            return STRING_MORNING_ENTITY
        if self.entity_type == InventoryManagerEntityType.NOON:
            return STRING_NOON_ENTITY
        if self.entity_type == InventoryManagerEntityType.EVENING:
            return STRING_EVENING_ENTITY
        if self.entity_type == InventoryManagerEntityType.NIGHT:
            return STRING_NIGHT_ENTITY
        return STRING_SUPPLY_ENTITY


class ConsumptionEntity(InventoryNumber):
    """Represents the dose consumed at a certain time during the day."""

    def __init__(
        self,
        coordinator: InventoryManagerItem,
        time: InventoryManagerEntityType,
    ) -> None:
        """Create a new consumption entity."""
        super().__init__(coordinator, time)
        self.native_max_value = float(
            coordinator.config_entry.data.get(CONF_ITEM_MAX_CONSUMPTION, 5)
        )
        self.icon = "mdi:pill-multiple"
        self.entity_category = EntityCategory.CONFIG


class SupplyEntity(InventoryNumber):
    """Represents the supply of the current item."""

    def __init__(self, coordinator: InventoryManagerItem) -> None:
        """Create a new suppy entity."""
        _LOGGER.debug("Initializing SupplyEntity")
        super().__init__(coordinator, InventoryManagerEntityType.SUPPLY)
        self.native_max_value = 1000000
        self.icon = "mdi:medication"

    @property
    def supported_features(self) -> int:
        """
        Return 4.

        This is a hack, because apparently custom features are not possible.
        This is only used to allow restriction of target entity in service call.
        """
        return 4  # LightEntityFeature.EFFECT

    def take(self, call: core.ServiceCall) -> None:
        """Execute the consume service call."""
        if SERVICE_PREDEFINED_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with predefined amount %s",
                call.data[SERVICE_PREDEFINED_AMOUNT],
            )
            self.coordinator.take_dose(
                InventoryManagerEntityType[call.data[SERVICE_PREDEFINED_AMOUNT].upper()]
            )
        elif SERVICE_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with amount %f",
                call.data[SERVICE_AMOUNT],
            )
            self.coordinator.take_number(call.data[SERVICE_AMOUNT])
