from __future__ import annotations

from enum import IntFlag
import logging

from homeassistant import config_entries, core
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import (
    CONF_PILL_NAME,
    CONF_PILL_SIZE,
    CONF_PILL_VENDOR,
    DOMAIN,
    SERVICE_TAKE,
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

    pill_object = InventoryManagerConfig(hass, entry.data)
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


def setup(hass: core.HomeAssistant, config):
    def consume_service(call: core.ServiceCall):
        _LOGGER.debug(call)
        amount = 0

        if "amount" in call.data:
            amount = call.data["amount"]
            for entity_id in call.data["entity_id"]:
                hass.states.set(
                    entity_id, float(hass.states.get(entity_id).state) - amount
                )
        elif "predefined-amount" in call.data:
            amount_entity = call.data["predefined-amount"]
            for e in call.data["entity_id"]:
                if amount_entity == "morning":
                    amount = hass.states.get(e).attributes.get(
                        InventoryManagerEntityType.MORNING
                    )
                    # hass.states.set(e, hass.states.get(e))

    hass.services.register(DOMAIN, SERVICE_TAKE, consume_service)

    return True


class EntityConfig:
    def __init__(
        self, hass: core.HomeAssistant, d: dict, t: InventoryManagerEntityType
    ) -> None:
        self.device_id = (
            d[CONF_PILL_NAME].lower() + "-" + d.get(CONF_PILL_SIZE, "").lower()
        )
        self.entity_type = t

        if t == InventoryManagerEntityType.CONSUMPTION:
            fmt = "sensor.{}"
        elif t == InventoryManagerEntityType.WARNING:
            fmt = "binary_sensor.{}"
        else:
            fmt = "number.{}"
        self.unique_id = self.device_id + "_" + t.name
        self.entity_id = generate_entity_id(
            fmt,
            self.unique_id,
            hass=hass,
        )


class InventoryManagerConfig:
    """Bla."""

    def __init__(self, hass: core.HomeAssistant, d) -> None:
        self._hass = hass
        self._data = d

        self.device_id = (
            d[CONF_PILL_NAME].lower() + "-" + d.get(CONF_PILL_SIZE, "").lower()
        )
        self.entity_config = {
            InventoryManagerEntityType.SUPPLY: EntityConfig(
                hass, d, InventoryManagerEntityType.SUPPLY
            ),
            InventoryManagerEntityType.MORNING: EntityConfig(
                hass, d, InventoryManagerEntityType.MORNING
            ),
            InventoryManagerEntityType.NOON: EntityConfig(
                hass, d, InventoryManagerEntityType.NOON
            ),
            InventoryManagerEntityType.EVENING: EntityConfig(
                hass, d, InventoryManagerEntityType.EVENING
            ),
            InventoryManagerEntityType.NIGHT: EntityConfig(
                hass, d, InventoryManagerEntityType.NIGHT
            ),
            InventoryManagerEntityType.CONSUMPTION: EntityConfig(
                hass, d, InventoryManagerEntityType.CONSUMPTION
            ),
            InventoryManagerEntityType.WARNING: EntityConfig(
                hass, d, InventoryManagerEntityType.WARNING
            ),
        }

    def d(self):
        return self._data

    # def take_dose(self, dose: InventoryManagerEntityType) -> None:
    #    self.entities[InventoryManagerEntityType.SUPPLY].set_native_value(
    #        self.supply - self.entities[dose].native_value
    #    )
    # self.set_n(, InventoryManagerEntityType.SUPPLY)

    # def take_number(self, number: int) -> None:
    #    if number != 0:
    #        self.set_n(self.supply - number, InventoryManagerEntityType.SUPPLY)

    @property
    def name(self) -> str:
        return self._data[CONF_PILL_NAME] + " " + self._data.get(CONF_PILL_SIZE, "")

    # def set_n(self, val: float, time: PillNumberEntityFeature, restoring=False) -> None:
    #     if val < 0:
    #         self._numbers[time] = 0.0
    #     else:
    #         self._numbers[time] = val
    #     if not restoring:
    #         [l.schedule_update_ha_state() for l in self._listeners]

    # def get_n(self, c) -> float:
    #   return self._numbers.setdefault(c, 0)
