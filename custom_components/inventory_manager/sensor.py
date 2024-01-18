import logging

from datetime import datetime, timedelta
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.dt import now

from . import InventoryManagerConfig, InventoryManagerEntityType
from .const import ATTR_DAILY, ATTR_DAYS_REMAINING, DOMAIN, STRING_SENSOR_ENTITY


_LOGGER = logging.getLogger(__name__)


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

    def __init__(
        self, hass: core.HomeAssistant, config: InventoryManagerConfig
    ) -> None:
        super().__init__()
        _LOGGER.debug("Initializing ConsumptionSensor")

        self._config = config

        self._device_id = config.device_id
        self._available = True
        self._device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=config.name,
        )
        self.unique_id = config.entity_config[
            InventoryManagerEntityType.CONSUMPTION
        ].unique_id
        self.attrs = {}
        self.entity_id = config.entity_config[
            InventoryManagerEntityType.CONSUMPTION
        ].entity_id
        self.native_value: datetime = now() + timedelta(days=10000)
        self._unsub = async_track_state_change_event(
            hass,
            [
                config.entity_config[numberEntity].entity_id
                for numberEntity in [
                    InventoryManagerEntityType.SUPPLY,
                    InventoryManagerEntityType.MORNING,
                    InventoryManagerEntityType.NOON,
                    InventoryManagerEntityType.EVENING,
                    InventoryManagerEntityType.NIGHT,
                ]
            ],
            self.schedule_update_ha_state,
        )

    @property
    def should_poll(self):
        return False

    @property
    def device_class(self):
        return SensorDeviceClass.TIMESTAMP

    @property
    def translation_key(self) -> str | None:
        return STRING_SENSOR_ENTITY

    def daily_consumption(self) -> float:
        """Calculate the daily consumption."""
        try:
            s = sum(
                float(
                    self.hass.states.get(
                        self._config.entity_config[entity_type].entity_id
                    ).state
                )
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

    def update(self):
        """Recalculate the remaining time until supply is empty."""
        _LOGGER.debug("Updating sensor")

        daily = self.daily_consumption()
        _LOGGER.debug(daily)

        supply_state = self.hass.states.get(
            self._config.entity_config[InventoryManagerEntityType.SUPPLY].entity_id
        )
        if supply_state is None:
            self.available = False
            return
        if supply_state.state == "unavailable":
            self.available = False
            return
        supply = float(supply_state.state)
        self.attrs[ATTR_DAILY] = daily
        if daily > 0:
            days_remaining = supply / daily
        else:
            days_remaining = 10000
        self.attrs[ATTR_DAYS_REMAINING] = days_remaining
        self.native_value = now() + timedelta(days=days_remaining)
        self.available = True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device_info
