import logging

import voluptuous as vol

from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.number import RestoreNumber
from homeassistant.components.light import LightEntityFeature
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.input_number import InputNumber
from . import InventoryManagerItem, InventoryManagerEntityType, EntityConfig
from .const import (
    DOMAIN,
    NATIVE_VALUE,
    SERVICE_AMOUNT,
    SERVICE_CONSUME,
    SERVICE_PREDEFINED_AMOUNT,
    STRING_EVENING_ENTITY,
    STRING_MORNING_ENTITY,
    STRING_NIGHT_ENTITY,
    STRING_NOON_ENTITY,
    STRING_SUPPLY_ENTITY,
    UNIT,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    item: InventoryManagerItem = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        SupplyEntity(hass, item),
        ConsumptionEntity(hass, item, InventoryManagerEntityType.MORNING),
        ConsumptionEntity(hass, item, InventoryManagerEntityType.NOON),
        ConsumptionEntity(hass, item, InventoryManagerEntityType.EVENING),
        ConsumptionEntity(hass, item, InventoryManagerEntityType.NIGHT),
    ]

    async_add_entities(sensors, update_before_add=False)

    if not hass.services.has_service(DOMAIN, SERVICE_CONSUME):
        _LOGGER.debug("Registering service %s.%s", DOMAIN, SERVICE_CONSUME)
        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            SERVICE_CONSUME,
            {
                vol.Exclusive("amount", "amount-specification"): cv.Number,
                vol.Exclusive("predefined-amount", "amount-specification"): cv.string,
            },
            lambda o1, o2: o1.take(o2),
            required_features=[InventoryManagerEntityType.SUPPLY],
        )


class InventoryNumber(RestoreNumber):
    """Represents a numeric entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: core.HomeAssistant,
        item: InventoryManagerItem,
        entity_type: InventoryManagerEntityType,
    ) -> None:
        super().__init__()
        self.hass: core.HomeAssistant = hass
        self.item: InventoryManagerItem = item
        self.entity_type: InventoryManagerEntityType = entity_type
        self.item.entity[entity_type] = self
        self.device_info = item.device_info

        entity_config: EntityConfig = item.entity_config[entity_type]
        self._available: bool = True
        self.entity_id: str = entity_config.entity_id
        self.unique_id: str = entity_config.unique_id

        self.native_unit_of_measurement = UNIT
        self.native_step = 0.25
        self.native_min_value = 0

    @property
    def native_value(self) -> float:
        return self.item.get(self.entity_type)

    @native_value.setter
    def native_value(self, value: float) -> None:
        _LOGGER.debug("Setting native value of %s to %2.1f.", self.entity_id, value)
        self.item.set(self.entity_type, value)

    def set_native_value(self, value: float) -> None:
        self.native_value = value

    async def async_added_to_hass(self):
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

    @property
    def translation_key(self) -> str:
        if self.entity_type == InventoryManagerEntityType.MORNING:
            return STRING_MORNING_ENTITY
        elif self.entity_type == InventoryManagerEntityType.NOON:
            return STRING_NOON_ENTITY
        elif self.entity_type == InventoryManagerEntityType.EVENING:
            return STRING_EVENING_ENTITY
        elif self.entity_type == InventoryManagerEntityType.NIGHT:
            return STRING_NIGHT_ENTITY
        else:
            return STRING_SUPPLY_ENTITY


class ConsumptionEntity(InventoryNumber):
    """Represents the dose consumed at a certain time during the day."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        config: InventoryManagerItem,
        time: InventoryManagerEntityType,
    ) -> None:
        super().__init__(hass, config, time)
        self.native_max_value = 5.0
        self.icon = "mdi:pill-multiple"
        self.entity_category = EntityCategory.CONFIG


class SupplyEntity(InventoryNumber):
    """Represents the supply of the current item."""

    def __init__(self, hass: core.HomeAssistant, pill) -> None:
        _LOGGER.debug("Initializing SupplyEntity")
        super().__init__(hass, pill, InventoryManagerEntityType.SUPPLY)
        self.native_max_value = 1000000
        self.icon = "mdi:medication"

    @property
    def supported_features(self):
        return 4  # LightEntityFeature.EFFECT

    def take(self, call: core.ServiceCall):
        """Execute the consume service call."""
        if SERVICE_PREDEFINED_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with predefined amount %s",
                call.data[SERVICE_PREDEFINED_AMOUNT],
            )
            self.item.take_dose(
                InventoryManagerEntityType[call.data[SERVICE_PREDEFINED_AMOUNT].upper()]
            )
        elif SERVICE_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with amount %f",
                call.data[SERVICE_AMOUNT],
            )
            self.item.take_number(call.data[SERVICE_AMOUNT])
