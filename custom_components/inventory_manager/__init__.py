"""Inventory manager integration."""
from __future__ import annotations
from enum import IntFlag
import logging

from homeassistant import config_entries, core
from homeassistant.const import Platform
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from .const import (
    CONF_SENSOR_BEFORE_EMPTY,
    CONF_ITEM_NAME,
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_SIZE,
    CONF_ITEM_VENDOR,
    CONF_ITEM_UNIT,
    DOMAIN,
    ENTITY_ID,
    ENTITY_TYPE,
    SPACE,
    UNDERSCORE,
    UNIQUE_ID,
)


_LOGGER = logging.getLogger(__name__)


class InventoryManagerEntityType(IntFlag):
    """Supported features of the number entities."""

    SUPPLY = 1
    NIGHT = 4
    MORNING = 8
    NOON = 32
    EVENING = 64
    WARNING = 128
    EMPTYPREDICTION = 256
    WEEK = 512
    MONTH = 1024


PLATFORMS: list[str] = [Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    item = InventoryManagerItem(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = item

    dr = device_registry.async_get(hass)
    friendly_name = entry.data[CONF_ITEM_NAME]
    if CONF_ITEM_SIZE in entry.options:
        friendly_name += SPACE + entry.options[CONF_ITEM_SIZE]
    if CONF_ITEM_UNIT in entry.options:
        friendly_name += entry.options[CONF_ITEM_UNIT]
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        entry_type=item.device_info["entry_type"],
        manufacturer=item.device_info["manufacturer"],
        model=friendly_name,
        name=friendly_name,
        identifiers=item.device_info["identifiers"],
    )

    # Register listener for config changes in options flow
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_listener(hass, entry):
    """Handle options update."""
    item = hass.data[DOMAIN].get(entry.entry_id)
    item.update(entry.options)


class InventoryManagerItem:
    """This class represents the item data itself."""

    def __init__(
        self, hass: core.HomeAssistant, entry: config_entries.ConfigEntry
    ) -> None:
        """Create a new item."""
        self._hass = hass
        self.entry = entry
        data = entry.data
        options = entry.options
        self._numbers = {}

        # Determine device id and name
        self.device_id = data[CONF_ITEM_NAME].lower()
        self.name = data[CONF_ITEM_NAME]
        if CONF_ITEM_SIZE in options:
            # self.device_id += "-" + options[CONF_ITEM_SIZE].lower()
            self.name += " " + options[CONF_ITEM_SIZE]
        if CONF_ITEM_UNIT in options:
            # self.device_id += options[CONF_ITEM_UNIT].lower()
            self.name += options[CONF_ITEM_UNIT]

        self.device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer=options.get(CONF_ITEM_VENDOR, None),
            entry_type=DeviceEntryType.SERVICE,
            name=self.name,
        )
        self.entity = {}
        self.entity_config = {
            entity_type: self._generate_entity_config(entity_type)
            for entity_type in InventoryManagerEntityType
        }

    def update(self, d: dict) -> None:
        """Reflect changes of the configuration."""

    def _generate_entity_config(self, entity_type: InventoryManagerEntityType) -> dict:
        if entity_type == InventoryManagerEntityType.EMPTYPREDICTION:
            fmt = "sensor.{}"
        elif entity_type == InventoryManagerEntityType.WARNING:
            fmt = "binary_sensor.{}"
        else:
            fmt = "number.{}"

        unique_id = self.device_id + UNDERSCORE + entity_type.name.lower()
        return {
            UNIQUE_ID: unique_id,
            ENTITY_ID: generate_entity_id(fmt, unique_id, hass=self._hass),
            ENTITY_TYPE: entity_type,
        }

    def get_unit(self) -> str:
        """Return the unit of the item."""
        return self.entry.options.get(CONF_ITEM_UNIT, None)

    def get_days_before_warning(self) -> int:
        """Return number of days before warning is active."""
        return self.entry.options.get(CONF_SENSOR_BEFORE_EMPTY, 10)

    def get_max_consumption(self) -> float:
        return self.entry.options.get(CONF_ITEM_MAX_CONSUMPTION, 5)

    def take_dose(self, dose: InventoryManagerEntityType) -> None:
        """Consume one dose."""
        if dose not in [
            InventoryManagerEntityType.MORNING,
            InventoryManagerEntityType.NOON,
            InventoryManagerEntityType.EVENING,
            InventoryManagerEntityType.NIGHT,
            InventoryManagerEntityType.WEEK,
            InventoryManagerEntityType.MONTH,
        ]:
            _LOGGER.debug("Invalid argument for take_dose: %s", dose)
            return
        amount = self.get(dose)
        self.take_number(amount)

    def take_number(self, number: int) -> None:
        """Consume specified number."""
        if number != 0:
            self.set(
                InventoryManagerEntityType.SUPPLY,
                self.get(InventoryManagerEntityType.SUPPLY) - number,
            )

    def set(self, spec: InventoryManagerEntityType, val: float) -> None:
        """Set one number."""
        if val < 0:
            self._numbers[spec] = 0.0
        else:
            self._numbers[spec] = val

        for et in [
            InventoryManagerEntityType.EMPTYPREDICTION,
            InventoryManagerEntityType.WARNING,
        ]:
            if et in self.entity and self.entity[et] is not None:
                self.entity[et].update()
            else:
                _LOGGER.debug("%s cannot be updated yet", et)
        _LOGGER.debug("Stored %f as new value for %s", val, spec)

    def get(self, entity_type: InventoryManagerEntityType) -> float:
        """Get number."""
        return self._numbers.setdefault(entity_type, 0)

    def days_remaining(self) -> float:
        """Calculate days remaining."""
        supply = self.get(InventoryManagerEntityType.SUPPLY)
        daily = self.daily_consumption()
        if daily > 0:
            return supply / daily
        else:
            return 10000

    def daily_consumption(self) -> float:
        """Calculate the daily consumption."""
        try:
            s = sum(
                self.get(entity_type)
                for entity_type in [
                    InventoryManagerEntityType.MORNING,
                    InventoryManagerEntityType.NOON,
                    InventoryManagerEntityType.EVENING,
                    InventoryManagerEntityType.NIGHT,
                ]
            )
            if self.get(InventoryManagerEntityType.WEEK) > 0:
                s = s + self.get(InventoryManagerEntityType.WEEK) / 7
            if self.get(InventoryManagerEntityType.MONTH) > 0:
                s = s + self.get(InventoryManagerEntityType.MONTH) / 28
            return s
        except (KeyError, AttributeError):
            return 0
