"""Number entities for inventory manager."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.const import EntityCategory

from .const import (
    CONF_ITEM_MAX_CONSUMPTION,
    CONF_ITEM_UNIT,
    ENTITY_ID,
    NATIVE_VALUE,
    STRING_EVENING_ENTITY,
    STRING_MONTH_ENTITY,
    STRING_MORNING_ENTITY,
    STRING_NIGHT_ENTITY,
    STRING_NOON_ENTITY,
    STRING_SUPPLY_ENTITY,
    STRING_WEEK_ENTITY,
    UNIQUE_ID,
    UNIT_PCS,
)
from .entity import InventoryManagerEntity, InventoryManagerEntityType

if TYPE_CHECKING:
    from types import NoneType

    from homeassistant import config_entries, core
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class InventoryManagerNumberEntityDescription(NumberEntityDescription):
    """Describes Inventory Manager number entity."""

    entity_type: InventoryManagerEntityType | None = None


NUMBER_TYPES: tuple[InventoryManagerNumberEntityDescription, ...] = (
    InventoryManagerNumberEntityDescription(
        key="supply",
        translation_key=STRING_SUPPLY_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.SUPPLY,
        icon="mdi:medication",
    ),
    InventoryManagerNumberEntityDescription(
        key="morning",
        translation_key=STRING_MORNING_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.MORNING,
        icon="mdi:pill-multiple",
        entity_category=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="noon",
        translation_key=STRING_NOON_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.NOON,
        icon="mdi:pill-multiple",
        entity_category=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="evening",
        translation_key=STRING_EVENING_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.EVENING,
        icon="mdi:pill-multiple",
        entity_category=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="night",
        translation_key=STRING_NIGHT_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.NIGHT,
        icon="mdi:pill-multiple",
        entity_category=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="week",
        translation_key=STRING_WEEK_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.WEEK,
        icon="mdi:pill-multiple",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    InventoryManagerNumberEntityDescription(
        key="month",
        translation_key=STRING_MONTH_ENTITY,
        has_entity_name=True,
        entity_type=InventoryManagerEntityType.MONTH,
        icon="mdi:pill-multiple",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    _hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> NoneType:
    """Set up number entities."""
    # Get the item object
    coordinator: InventoryManagerItem = config_entry.runtime_data.coordinator

    # Create numeric entities
    entities = [
        InventoryNumber(coordinator, description) for description in NUMBER_TYPES
    ]

    async_add_entities(entities, update_before_add=False)


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
            msg = (
                f"entity_type must be specified in the entity description "
                f"(key: {description.key})"
            )
            raise ValueError(msg)

        self.entity_type: InventoryManagerEntityType = description.entity_type

        entity_config: dict = item.entity_config[self.entity_type]
        self.entity_id: str = entity_config[ENTITY_ID]
        self.unique_id: str = entity_config[UNIQUE_ID]

        self._available: bool = True
        self._attr_native_unit_of_measurement = item.config_entry.data.get(
            CONF_ITEM_UNIT, UNIT_PCS
        )
        self._attr_native_step = 0.25
        self._attr_native_min_value = 0

        # Set max value based on entity type
        if self.entity_type == InventoryManagerEntityType.SUPPLY:
            self.native_max_value = 1000000
        else:
            self.native_max_value = float(
                item.config_entry.data.get(CONF_ITEM_MAX_CONSUMPTION, 5)
            )

    @property
    def native_value(self) -> float:
        """The native value."""
        return self.coordinator.get(self.entity_type)

    async def async_set_native_value(self, value: float) -> None:
        """Set the native value."""
        _LOGGER.debug("Setting native value of %s to %2.1f.", self.entity_id, value)
        self.coordinator.set(self.entity_type, value)

    async def async_added_to_hass(self) -> None:
        """Restore the number from last time."""
        # Restore before registering with the item, so the restored value is
        # part of the first state that is written
        last_data = await self.async_get_last_number_data()
        if last_data is not None:
            last_number_data = last_data.as_dict()
            if isinstance(last_number_data[NATIVE_VALUE], (int, float)):
                self.coordinator.set(
                    self.entity_type, float(last_number_data[NATIVE_VALUE])
                )
        await super().async_added_to_hass()
