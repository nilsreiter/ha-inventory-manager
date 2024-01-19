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
    SPACE,
    UNDERSCORE,
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
    CONSUMPTION = 256


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
        entry_type=DeviceEntryType.SERVICE,
        manufacturer=entry.data.get(CONF_ITEM_VENDOR, None),
        model=friendly_name,
        name=friendly_name,
        identifiers={
            (
                DOMAIN,
                entry.data[CONF_ITEM_NAME].lower()
                + "-"
                + entry.data.get(CONF_ITEM_SIZE, "").lower(),
            )
        },
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


class EntityConfig:
    def __init__(
        self, hass: core.HomeAssistant, device_id: str, t: InventoryManagerEntityType
    ) -> None:
        self.entity_type = t

        if t == InventoryManagerEntityType.CONSUMPTION:
            fmt = "sensor.{}"
        elif t == InventoryManagerEntityType.WARNING:
            fmt = "binary_sensor.{}"
        else:
            fmt = "number.{}"
        self.unique_id = device_id + UNDERSCORE + t.name.lower()
        self.entity_id = generate_entity_id(
            fmt,
            self.unique_id,
            hass=hass,
        )


class InventoryManagerItem:
    """Bla."""

    def __init__(self, hass: core.HomeAssistant, d) -> None:
        self._hass = hass
        self._data = d
        self._numbers = {}

        _LOGGER.debug(d)
        self.device_id = d[CONF_ITEM_NAME].lower()
        if CONF_ITEM_SIZE in d:
            self.device_id = self.device_id + "-" + d[CONF_ITEM_SIZE].lower()
        self.name = (
            self._data[CONF_ITEM_NAME] + " " + self._data.get(CONF_ITEM_SIZE, "")
        )
        self.device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.name,
        )
        self.entity = {}
        self.entity_config = {
            InventoryManagerEntityType.SUPPLY: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.SUPPLY
            ),
            InventoryManagerEntityType.MORNING: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.MORNING
            ),
            InventoryManagerEntityType.NOON: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.NOON
            ),
            InventoryManagerEntityType.EVENING: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.EVENING
            ),
            InventoryManagerEntityType.NIGHT: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.NIGHT
            ),
            InventoryManagerEntityType.CONSUMPTION: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.CONSUMPTION
            ),
            InventoryManagerEntityType.WARNING: EntityConfig(
                hass, self.device_id, InventoryManagerEntityType.WARNING
            ),
        }

    def d(self):
        return self._data

    def take_dose(self, dose: InventoryManagerEntityType) -> None:
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
        if number != 0:
            self.set(
                InventoryManagerEntityType.SUPPLY,
                self.get(InventoryManagerEntityType.SUPPLY) - number,
            )

    def set(self, spec: InventoryManagerEntityType, val: float) -> None:
        if val < 0:
            self._numbers[spec] = 0.0
        else:
            self._numbers[spec] = val

        for et in [
            InventoryManagerEntityType.CONSUMPTION,
            InventoryManagerEntityType.WARNING,
        ]:
            if et in self.entity and self.entity[et] is not None:
                self.entity[et].update()
            else:
                _LOGGER.debug("%s cannot be updated yet", et)

    def get(self, entity_type: InventoryManagerEntityType) -> float:
        return self._numbers.setdefault(entity_type, 0)

    def days_remaining(self) -> float:
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
