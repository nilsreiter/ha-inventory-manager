import logging

import voluptuous as vol

from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.input_number import InputNumber
from . import InventoryManagerConfig, InventoryManagerEntityType, EntityConfig
from .const import (
    DOMAIN,
    SERVICE_TAKE_E,
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
    config = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        SupplyEntity(hass, config),
        ConsumptionEntity(hass, config, InventoryManagerEntityType.MORNING),
        ConsumptionEntity(hass, config, InventoryManagerEntityType.NOON),
        ConsumptionEntity(hass, config, InventoryManagerEntityType.EVENING),
        ConsumptionEntity(hass, config, InventoryManagerEntityType.NIGHT),
    ]

    async_add_entities(sensors, update_before_add=True)

    if not hass.services.has_service(DOMAIN, SERVICE_TAKE_E):
        _LOGGER.debug("Registering service %s", SERVICE_TAKE_E)
        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            SERVICE_TAKE_E,
            {
                vol.Exclusive("amount", "amount-specification"): cv.Number,
                vol.Exclusive("predefined-amount", "amount-specification"): cv.string,
            },
            lambda o1, o2: o1.take(o2),
        )


class InventoryNumber(RestoreNumber):
    """Represents a numeric entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: core.HomeAssistant,
        config: InventoryManagerConfig,
        time: InventoryManagerEntityType,
    ) -> None:
        super().__init__()
        self.config: InventoryManagerConfig = config
        entity_config: EntityConfig = config.entity_config[time]
        self._spec: InventoryManagerEntityType = entity_config.entity_type
        self._device_id: str = entity_config.device_id
        self._available: bool = True
        self.hass: core.HomeAssistant = hass
        self.native_value: float = 0.0
        self.entity_id: str = entity_config.entity_id
        self.unique_id: str = entity_config.unique_id

    def set_native_value(self, value: float) -> None:
        _LOGGER.debug("Setting native value of %s to %2.1f.", self.entity_id, value)
        self.native_value = value

    async def async_added_to_hass(self):
        try:
            last_data = await self.async_get_last_number_data()
            if last_data is not None:
                last_number_data = last_data.as_dict()
                if isinstance(last_number_data["native_value"], float):
                    self.native_value = last_number_data["native_value"]
                else:
                    self.native_value = 0.0
        except AttributeError:
            self.set_native_value(0.0)

    @property
    def native_step(self) -> float:
        """Return 0.25."""
        return 0.25

    @property
    def translation_key(self) -> str:
        if self._spec == InventoryManagerEntityType.MORNING:
            return STRING_MORNING_ENTITY
        elif self._spec == InventoryManagerEntityType.NOON:
            return STRING_NOON_ENTITY
        elif self._spec == InventoryManagerEntityType.EVENING:
            return STRING_EVENING_ENTITY
        elif self._spec == InventoryManagerEntityType.NIGHT:
            return STRING_NIGHT_ENTITY
        else:
            return STRING_SUPPLY_ENTITY

    @property
    def native_min_value(self):
        """Return 0.0."""
        return 0.0

    @property
    def native_unit_of_measurement(self):
        return UNIT

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)}, name=self.config.name
        )


class ConsumptionEntity(InventoryNumber):
    """Represents the dose consumed at a certain time during the day."""

    def __init__(
        self,
        hass: core.HomeAssistant,
        config: InventoryManagerConfig,
        time: InventoryManagerEntityType,
    ) -> None:
        super().__init__(hass, config, time)

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def supported_features(self) -> InventoryManagerEntityType:
        return self._attr_supported_features

    @property
    def native_max_value(self):
        return 5.0

    @property
    def icon(self):
        return "mdi:pill-multiple"


class SupplyEntity(InventoryNumber):
    """Represents the supply of the current item."""

    def __init__(self, hass: core.HomeAssistant, pill) -> None:
        super().__init__(hass, pill, InventoryManagerEntityType.SUPPLY)
        _LOGGER.debug("Initializing SupplyEntity")

        # def react_to_statemachine_change(event):
        #     _LOGGER.debug(event)
        #     if event.new_state.state != self.native_value:
        #         self.set_native_value(float(event.new_state.state))

        # self._unsub = async_track_state_change_event(
        #     hass,
        #     [self.entity_id],
        #     react_to_statemachine_change,
        # )

    @property
    def supported_features(self) -> InventoryManagerEntityType:
        return InventoryManagerEntityType.SUPPLY

    @property
    def native_max_value(self):
        return 100000.0

    def take(self, call: core.ServiceCall):
        _LOGGER.debug("Calling service 'consume'")
        _LOGGER.debug(call.data)
        if "amount-entity" in call.data:
            for entity_id in call.data["amount-entity"]:
                amount = self.hass.states.get(entity_id).state
                self.config.take_number(float(amount))
        elif "predefined-amount" in call.data:
            if call.data["predefined-amount"] == "morning":
                self.config.take_dose(InventoryManagerEntityType.MORNING)
            elif call.data["predefined-amount"] == "noon":
                self.config.take_dose(InventoryManagerEntityType.NOON)
            elif call.data["predefined-amount"] == "evening":
                self.config.take_dose(InventoryManagerEntityType.EVENING)
            elif call.data["predefined-amount"] == "night":
                self.config.take_dose(InventoryManagerEntityType.NIGHT)
        elif "amount" in call.data:
            self.set_native_value(self.native_value - call.data["amount"])

    # def set_value(self, value):
    #    self.set_native_value(float(value))

    @property
    def icon(self):
        return "mdi:medication"
