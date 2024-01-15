import logging

import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components.number import RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import Item, PillNumberEntityFeature
from .const import (
    DOMAIN,
    SERVICE_TAKE,
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
        ConsumptionEntity(hass, config, PillNumberEntityFeature.MORNING),
        ConsumptionEntity(hass, config, PillNumberEntityFeature.NOON),
        ConsumptionEntity(hass, config, PillNumberEntityFeature.EVENING),
        ConsumptionEntity(hass, config, PillNumberEntityFeature.NIGHT),
    ]

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_TAKE,
        {
            vol.Exclusive("amount", "amount-specification"): cv.Number,
            vol.Exclusive("predefined-amount", "amount-specification"): cv.string,
        },
        sensors[0].take,
    )
    async_add_entities(sensors, update_before_add=True)


class InventoryNumber(RestoreNumber):
    """Represents a numeric entity."""

    _attr_has_entity_name = True

    def __init__(
        self, hass: core.HomeAssistant, pill: Item, spec: PillNumberEntityFeature
    ) -> None:
        super().__init__()
        self.pill = pill
        self._spec = spec
        self._device_id = self.pill.device_id
        self._unique_id = self._device_id + "_" + spec.name
        self._available = True
        self.hass = hass
        self.entity_id = generate_entity_id("number.{}", self._unique_id, hass=hass)
        self.pill.add_listener(self)

    def set_native_value(self, value: float) -> None:
        self.pill.set_n(value, self._spec)

    async def async_added_to_hass(self):
        try:
            last_data = await self.async_get_last_number_data()
            if last_data is not None:
                last_number_data = last_data.as_dict()
                self.pill.set_n(
                    last_number_data["native_value"], self._spec, restoring=True
                )
        except AttributeError:
            self.set_native_value(0.0)

    @property
    def native_value(self):
        return self.pill[self._spec]

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def native_step(self) -> float:
        return 0.25

    @property
    def translation_key(self) -> str:
        if self._spec == PillNumberEntityFeature.MORNING:
            return STRING_MORNING_ENTITY
        elif self._spec == PillNumberEntityFeature.NOON:
            return STRING_NOON_ENTITY
        elif self._spec == PillNumberEntityFeature.EVENING:
            return STRING_EVENING_ENTITY
        elif self._spec == PillNumberEntityFeature.NIGHT:
            return STRING_NIGHT_ENTITY
        else:
            return STRING_SUPPLY_ENTITY

    @property
    def native_min_value(self):
        return 0.0

    @property
    def native_unit_of_measurement(self):
        return UNIT

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(identifiers={(DOMAIN, self._device_id)}, name=self.pill.name)


class ConsumptionEntity(InventoryNumber):
    """Represents the dose consumed at a certain time during the day."""

    def __init__(
        self, hass: core.HomeAssistant, pill: Item, time: PillNumberEntityFeature
    ) -> None:
        super().__init__(hass, pill, time)

    @property
    def entity_category(self):
        return EntityCategory.CONFIG

    @property
    def supported_features(self) -> PillNumberEntityFeature:
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
        super().__init__(hass, pill, PillNumberEntityFeature.SUPPLY)

    @property
    def supported_features(self) -> PillNumberEntityFeature:
        return PillNumberEntityFeature.SUPPLY

    @property
    def native_max_value(self):
        return 100000.0

    def take(self, targetEntity, call: core.ServiceCall):
        _LOGGER.debug("Calling service 'consume'")
        if "amount-entity" in call.data:
            for entity_id in call.data["amount-entity"]:
                amount = self.hass.states.get(entity_id).state
                self.pill.take_number(float(amount))
        elif "predefined-amount" in call.data:
            if call.data["predefined-amount"] == "morning":
                self.pill.take_dose(PillNumberEntityFeature.MORNING)
            elif call.data["predefined-amount"] == "noon":
                self.pill.take_dose(PillNumberEntityFeature.NOON)
            elif call.data["predefined-amount"] == "evening":
                self.pill.take_dose(PillNumberEntityFeature.EVENING)
            elif call.data["predefined-amount"] == "night":
                self.pill.take_dose(PillNumberEntityFeature.NIGHT)
        elif "amount" in call.data:
            self.pill.take_number(call.data["amount"])

    @property
    def icon(self):
        return "mdi:medication"
