import logging

from datetime import timedelta
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import DeviceInfo, generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util.dt import now
from homeassistant.helpers.event import async_track_state_change_event

from . import InventoryManagerConfig, InventoryManagerEntityType
from .sensor import ConsumptionSensor
from .const import (
    ATTR_DAILY,
    ATTR_DAYS_REMAINING,
    CONF_SENSOR_BEFORE_EMPTY,
    DOMAIN,
    STRING_PROBLEM_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


# def setup_platform(
#     hass: core.HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the sensor platform."""
#     # We only want this platform to be set up via discovery.
#     if discovery_info is None:
#         return
#     add_entities([WarnSensor(hass, config)])


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [WarnSensor(hass, config)]
    async_add_entities(sensors, update_before_add=False)


class WarnSensor(BinarySensorEntity):
    """Represents a warning entity."""

    _attr_has_entity_name = True

    def __init__(self, hass: core.HomeAssistant, config: InventoryManagerConfig):
        super().__init__()
        _LOGGER.debug("Initializing WarnSensor")

        self._config: InventoryManagerConfig = config
        self._device_id = config.device_id
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=config.name,
        )
        self.unique_id = config.entity_config[
            InventoryManagerEntityType.WARNING
        ].unique_id

        self.available = False
        self.is_on = False
        self.attrs = {}
        self.entity_id = config.entity_config[
            InventoryManagerEntityType.WARNING
        ].entity_id

        self._unsub = async_track_state_change_event(
            hass,
            [config.entity_config[InventoryManagerEntityType.CONSUMPTION].entity_id],
            self.schedule_update_ha_state,
        )

    def update(self):
        _LOGGER.debug("Updating binary sensor")
        state = self.hass.states.get(
            self._config.entity_config[InventoryManagerEntityType.CONSUMPTION].entity_id
        )
        if state is None:
            self.is_on = False
            self.available = False
            return
        _LOGGER.debug(state)
        if ATTR_DAYS_REMAINING not in state.attributes:
            self.is_on = False
            self.available = False
            return
        days_remaining = state.attributes[ATTR_DAYS_REMAINING]
        if days_remaining == "unavailable":
            self.is_on = False
            self.available = False
            return
        self.available = True
        self.is_on = days_remaining < self._config.d()[CONF_SENSOR_BEFORE_EMPTY]

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        return BinarySensorDeviceClass.PROBLEM

    @property
    def translation_key(self) -> str | None:
        return STRING_PROBLEM_ENTITY

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device_info
