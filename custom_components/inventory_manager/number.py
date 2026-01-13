"""Number entities for inventory manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_platform

from .const import (
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_UNIT,
    DOMAIN,
    ENTITY_ID,
    NATIVE_VALUE,
    SERVICE_AMOUNT,
    SERVICE_AMOUNT_SPECIFICATION,
    SERVICE_CONSUME,
    SERVICE_PREDEFINED_AMOUNT,
    STRING_EVENING_ENTITY,
    STRING_MORNING_ENTITY,
    STRING_NIGHT_ENTITY,
    STRING_NOON_ENTITY,
    STRING_SUPPLY_ENTITY,
    UNIQUE_ID,
    UNIT_PCS,
)
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from types import NoneType

    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class InventoryManagerNumberEntityDescription(NumberEntityDescription):
    """Describes Inventory Manager number entity."""

    entity_type: InventoryManagerEntityType | None = None
    icon_override: str | None = None
    entity_category_override: EntityCategory | None = None


# TODO: Add option to change number parameters (min, max, step) from config flow.
NUMBER_TYPES: tuple[InventoryManagerNumberEntityDescription, ...] = (
    InventoryManagerNumberEntityDescription(
        key="supply",
        translation_key=STRING_SUPPLY_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.SUPPLY,
        icon_override="mdi:medication",
    ),
    InventoryManagerNumberEntityDescription(
        key="morning",
        translation_key=STRING_MORNING_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.MORNING,
        icon_override="mdi:pill-multiple",
        entity_category_override=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="noon",
        translation_key=STRING_NOON_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.NOON,
        icon_override="mdi:pill-multiple",
        entity_category_override=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="evening",
        translation_key=STRING_EVENING_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.EVENING,
        icon_override="mdi:pill-multiple",
        entity_category_override=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="night",
        translation_key=STRING_NIGHT_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.NIGHT,
        icon_override="mdi:pill-multiple",
        entity_category_override=EntityCategory.CONFIG,
    ),
)
async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> NoneType:
    """Set up number entities and register service."""
    # Get the item object
    coordinator: InventoryManagerItem = hass.data[DOMAIN][config_entry.entry_id]

    # Create numeric entities
    entities = [
        InventoryNumber(coordinator, description) for description in NUMBER_TYPES
    ]

    async_add_entities(entities, update_before_add=False)

    # Register service, if needed
    if not hass.services.has_service(DOMAIN, SERVICE_CONSUME):
        _LOGGER.debug("Registering service %s.%s", DOMAIN, SERVICE_CONSUME)
        platform = entity_platform.async_get_current_platform()

        platform.async_register_entity_service(
            SERVICE_CONSUME,
            {
                vol.Exclusive(
                    SERVICE_AMOUNT, SERVICE_AMOUNT_SPECIFICATION
                ): cv.positive_int,
                vol.Exclusive(
                    SERVICE_PREDEFINED_AMOUNT, SERVICE_AMOUNT_SPECIFICATION
                ): cv.string,
            },
            lambda target, payload: target.take(payload),
        )


class InventoryNumber(InventoryManagerEntity, RestoreNumber):
    """Represents a numeric entity."""

    entity_description: InventoryManagerNumberEntityDescription

    def __init__(
        self,
        item: InventoryManagerItem,
        description: InventoryManagerNumberEntityDescription,
    ) -> None:
        """Create a new number entity."""
        super().__init__(item)
        self.entity_description = description

        if description.entity_type is None:
            msg = "entity_type must be specified in the entity description"
            raise ValueError(msg)

        self.entity_type: InventoryManagerEntityType = description.entity_type

        # register self with the item object
        self.coordinator.entity[self.entity_type] = self

        entity_config: dict = item.entity_config[self.entity_type]
        self.entity_id: str = entity_config[ENTITY_ID]
        self.unique_id: str = entity_config[UNIQUE_ID]

        self._available: bool = True
        self.native_unit_of_measurement = item.data.get(CONF_ITEM_UNIT, UNIT_PCS)
        self.native_step = 0.25
        self.native_min_value = 0

        # Set max value based on entity type
        if self.entity_type == InventoryManagerEntityType.SUPPLY:
            self.native_max_value = 1000000
        else:
            self.native_max_value = float(
                item.data.get(CONF_ITEM_MAX_CONSUMPTION, 5)
            )

        # Set icon and entity_category from description
        if description.icon_override:
            self.icon = description.icon_override
        if description.entity_category_override:
            self.entity_category = description.entity_category_override

    @property
    def native_value(self) -> float:
        """The native value."""
        return self.coordinator.get(self.entity_type)

    @native_value.setter
    def native_value(self, value: float) -> None:
        _LOGGER.debug("Setting native value of %s to %2.1f.", self.entity_id, value)
        self.coordinator.set(self.entity_type, value)

    def set_native_value(self, value: float) -> None:
        """Set the native value."""
        self.native_value = value

    async def async_added_to_hass(self) -> None:
        """Restore the number from last time."""
        try:
            last_data = await self.async_get_last_number_data()
            if last_data is not None:
                last_number_data = last_data.as_dict()
                if isinstance(last_number_data[NATIVE_VALUE], float):
                    self.native_value = last_number_data[NATIVE_VALUE]
                else:
                    self.native_value = 0.0
        except AttributeError:
            self.set_native_value(0.0)

    @property
    def supported_features(self) -> int:
        """
        Return 4 for supply entity.

        This is a hack, because apparently custom features are not possible.
        This is only used to allow restriction of target entity in service call.
        """
        if self.entity_type == InventoryManagerEntityType.SUPPLY:
            return 4  # LightEntityFeature.EFFECT
        return 0

    def take(self, call: core.ServiceCall) -> None:
        """Execute the consume service call."""
        if SERVICE_PREDEFINED_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with predefined amount %s",
                call.data[SERVICE_PREDEFINED_AMOUNT],
            )
            self.coordinator.take_dose(
                InventoryManagerEntityType[call.data[SERVICE_PREDEFINED_AMOUNT].upper()]
            )
        elif SERVICE_AMOUNT in call.data:
            _LOGGER.debug(
                "Calling service 'consume' with amount %f",
                call.data[SERVICE_AMOUNT],
            )
            self.coordinator.take_number(call.data[SERVICE_AMOUNT])
