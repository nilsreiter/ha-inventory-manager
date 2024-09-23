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
    CONF_ITEM_NAME,
    CONF_ITEM_SIZE,
    CONF_ITEM_VENDOR,
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


PLATFORMS: list[str] = [Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})

    item = InventoryManagerItem(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = item

    dr = device_registry.async_get(hass)
    friendly_name = entry.data[CONF_ITEM_NAME]
    if CONF_ITEM_SIZE in entry.data:
        friendly_name = friendly_name + SPACE + entry.data[CONF_ITEM_SIZE]
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        entry_type=item.device_info["entry_type"],
        manufacturer=item.device_info["manufacturer"],
        model=friendly_name,
        name=friendly_name,
        identifiers=item.device_info["identifiers"],
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


class InventoryManagerItem:
    """This class represents the item data itself."""

    def __init__(self, hass: core.HomeAssistant, d) -> None:
        """Create a new item."""
        self._hass = hass
        self.data = d
        self._numbers = {}

        self.device_id = d[CONF_ITEM_NAME].lower()
        if CONF_ITEM_SIZE in d:
            self.device_id = self.device_id + "-" + d[CONF_ITEM_SIZE].lower()
        self.name = self.data[CONF_ITEM_NAME] + " " + self.data.get(CONF_ITEM_SIZE, "")
        self.device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer=d.get(CONF_ITEM_VENDOR, None),
            entry_type=DeviceEntryType.SERVICE,
            name=self.name,
        )
        self.entity = {}
        self.entity_config = {
            entity_type: self._generate_entity_config(entity_type)
            for entity_type in InventoryManagerEntityType
        }

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

    def take_dose(self, dose: InventoryManagerEntityType) -> None:
        """Consume one dose."""
        if dose not in [
            InventoryManagerEntityType.MORNING,
            InventoryManagerEntityType.NOON,
            InventoryManagerEntityType.EVENING,
            InventoryManagerEntityType.NIGHT,
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

            return s
        except (KeyError, AttributeError):
            return 0
