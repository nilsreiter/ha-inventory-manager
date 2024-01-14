from __future__ import annotations

from enum import IntFlag
import logging

from homeassistant import config_entries, core
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import CONF_PILL_NAME, CONF_PILL_SIZE, CONF_PILL_VENDOR, DOMAIN

PLATFORMS: list[str] = [Platform.NUMBER, Platform.SENSOR, Platform.BINARY_SENSOR]


_LOGGER = logging.getLogger(__name__)


class PillNumberEntityFeature(IntFlag):
    """Supported features of the number entities."""

    SUPPLY = 1
    NIGHT = 4
    MORNING = 8
    NOON = 32
    EVENING = 64


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})

    pill_object = Item(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = pill_object

    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        entry_type=DeviceEntryType.SERVICE,
        manufacturer=entry.data.get(CONF_PILL_VENDOR, None),
        model=entry.data[CONF_PILL_NAME] + " " + entry.data.get(CONF_PILL_SIZE, ""),
        name=entry.data[CONF_PILL_NAME] + " " + entry.data.get(CONF_PILL_SIZE, ""),
        identifiers={
            (
                DOMAIN,
                entry.data[CONF_PILL_NAME].lower()
                + "-"
                + entry.data.get(CONF_PILL_SIZE, "").lower(),
            )
        },
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


class Item:
    """Bla."""

    def __init__(self, hass: core.HomeAssistant, d) -> None:
        self._hass = hass
        self._data = d
        self._numbers = {}
        self._listeners = []
        self._entity_ids = {}

    def d(self):
        return self._data

    def take_dose(self, dose: PillNumberEntityFeature) -> None:
        self.set_n(self.supply - self._numbers[dose], PillNumberEntityFeature.SUPPLY)

    def take_number(self, number: int) -> None:
        if number != 0:
            self.set_n(self.supply - number, PillNumberEntityFeature.SUPPLY)

    @property
    def name(self) -> str:
        return self._data[CONF_PILL_NAME] + " " + self._data.get(CONF_PILL_SIZE, "")

    @property
    def days_remaining(self) -> int:
        daily = self.daily
        supply = self.supply

        if daily > 0:
            daysRemaining = supply / daily
        else:
            daysRemaining = "unavailable"
        return daysRemaining

    @property
    def device_id(self):
        return (
            self._data[CONF_PILL_NAME].lower()
            + "-"
            + self._data.get(CONF_PILL_SIZE, "").lower()
        )

    def add_listener(self, listener) -> None:
        self._listeners.append(listener)

    def set_supply_entity(self, number_entity) -> None:
        self._supply = number_entity

    def set_n(self, val: float, time: PillNumberEntityFeature, restoring=False) -> None:
        if val < 0:
            self._numbers[time] = 0.0
        else:
            self._numbers[time] = val
        if not restoring:
            [l.schedule_update_ha_state() for l in self._listeners]

    @property
    def daily(self) -> float:
        s = 0
        s += self.morning
        s += self.noon
        s += self.evening
        s += self.night
        return s

    def get_n(self, c) -> float:
        return self._numbers.setdefault(c, 0)

    @property
    def supply(self) -> float:
        return self._numbers.setdefault(PillNumberEntityFeature.SUPPLY, 0)

    @property
    def morning(self) -> float:
        return self._numbers.setdefault(PillNumberEntityFeature.MORNING, 0)

    @property
    def noon(self) -> float:
        return self._numbers.setdefault(PillNumberEntityFeature.NOON, 0)

    @property
    def evening(self) -> float:
        return self._numbers.setdefault(PillNumberEntityFeature.EVENING, 0)

    @property
    def night(self) -> float:
        return self._numbers.setdefault(PillNumberEntityFeature.NIGHT, 0)
