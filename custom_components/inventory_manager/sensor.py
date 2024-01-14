from datetime import datetime, timedelta
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.util.dt import now

from . import Item
from .const import ATTR_DAILY, ATTR_DAYS_REMAINING, DOMAIN, STRING_SENSOR_ENTITY


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [ConsumptionSensor(hass, config)]
    async_add_entities(sensors, update_before_add=True)


class ConsumptionSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hass: core.HomeAssistant, pill: Item) -> None:
        super().__init__()
        self.pill = pill
        self.pill.add_listener(self)
        self._device_id = self.pill.device_id
        self._unique_id = self._device_id + "_supply_empty"
        self._state = datetime.fromisoformat("2024-11-04 00:05:23.283+00:00")
        self._available = True
        self.attrs = {}
        self.entity_id = generate_entity_id("number.{}", self._unique_id, hass=hass)

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def translation_key(self) -> str | None:
        return STRING_SENSOR_ENTITY

    @property
    def native_value(self):
        daily = self.pill.daily

        supply = self.pill.supply
        self.attrs[ATTR_DAILY] = daily

        if daily > 0:
            daysRemaining = supply / daily
        else:
            daysRemaining = 10000

        self.attrs[ATTR_DAYS_REMAINING] = daysRemaining
        self._state = now() + timedelta(days=daysRemaining)
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self.pill.name,
        )
