import logging
import uuid
from typing import Any

from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ENTITY_ID,
    ENTITY_TYPE,
    UNDERSCORE,
    UNIQUE_ID,
)
from .data import (
    InventoryManagerConfigEntry,
)
from .entity import InventoryManagerEntityType

_LOGGER = logging.getLogger(__name__)


class InventoryManagerItem(DataUpdateCoordinator):
    """The class represents the item data itself."""

    def __init__(
        self, config_entry: InventoryManagerConfigEntry, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        """Create a new item."""
        self.data = dict(config_entry.data)
        self._numbers = {}
        self.config_entry = config_entry

        self.entity = {}
        self.entity_config = {
            entity_type: self._generate_entity_config(entity_type)
            for entity_type in InventoryManagerEntityType
        }

    async def _async_update_data(self) -> Any:
        """Update data via library."""

    def _generate_entity_config(self, entity_type: InventoryManagerEntityType) -> dict:
        if entity_type == InventoryManagerEntityType.EMPTYPREDICTION:
            fmt = "sensor.{}"
        elif entity_type == InventoryManagerEntityType.WARNING:
            fmt = "binary_sensor.{}"
        else:
            fmt = "number.{}"

        # We try to generate a sensible unique id
        if self.config_entry.entry_id is not None and entity_type.name is not None:
            unique_id = self.config_entry.entry_id + UNDERSCORE + entity_type.name
        else:
            unique_id = str(uuid.uuid4())
        return {
            UNIQUE_ID: unique_id,
            ENTITY_ID: generate_entity_id(fmt, unique_id, hass=self.hass),
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

    def take_number(self, number: float) -> None:
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
