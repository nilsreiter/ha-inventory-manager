"""Actions to consume and store supplies."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)

from .const import (
    DOMAIN,
    PREDEFINED_AMOUNTS,
    SERVICE_AMOUNT,
    SERVICE_AMOUNT_SPECIFICATION,
    SERVICE_CONSUME,
    SERVICE_PREDEFINED_AMOUNT,
    SERVICE_STORE,
)
from .entity import InventoryManagerEntityType

if TYPE_CHECKING:
    from .coordinator import InventoryManagerItem

_LOGGER = logging.getLogger(__name__)

# Amounts may be fractional (e.g. half a tablet), but must be positive
AMOUNT_SCHEMA = vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False))

# Items are targeted by their device, or by any of their entities
_HAS_TARGET = cv.has_at_least_one_key(*(key.schema for key in cv.ENTITY_SERVICE_FIELDS))

CONSUME_SCHEMA = vol.All(
    vol.Schema(
        {
            **cv.ENTITY_SERVICE_FIELDS,
            vol.Exclusive(SERVICE_AMOUNT, SERVICE_AMOUNT_SPECIFICATION): AMOUNT_SCHEMA,
            vol.Exclusive(
                SERVICE_PREDEFINED_AMOUNT, SERVICE_AMOUNT_SPECIFICATION
            ): vol.In(PREDEFINED_AMOUNTS),
        }
    ),
    cv.has_at_least_one_key(SERVICE_AMOUNT, SERVICE_PREDEFINED_AMOUNT),
    _HAS_TARGET,
)

STORE_SCHEMA = vol.All(
    vol.Schema(
        {
            **cv.ENTITY_SERVICE_FIELDS,
            vol.Required(SERVICE_AMOUNT): AMOUNT_SCHEMA,
        }
    ),
    _HAS_TARGET,
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the consume and store actions."""

    @callback
    def consume(call: ServiceCall) -> None:
        for item in _targeted_items(hass, call):
            if SERVICE_PREDEFINED_AMOUNT in call.data:
                dose = InventoryManagerEntityType[
                    call.data[SERVICE_PREDEFINED_AMOUNT].upper()
                ]
                _LOGGER.debug(
                    "Consuming predefined amount %s of %s, which is %f",
                    call.data[SERVICE_PREDEFINED_AMOUNT],
                    item.config_entry.title,
                    item.get(dose),
                )
                item.take_dose(dose)
            else:
                _LOGGER.debug(
                    "Consuming %f of %s",
                    call.data[SERVICE_AMOUNT],
                    item.config_entry.title,
                )
                item.take_number(call.data[SERVICE_AMOUNT])

    @callback
    def store(call: ServiceCall) -> None:
        for item in _targeted_items(hass, call):
            item.take_number(-1 * call.data[SERVICE_AMOUNT])

    hass.services.async_register(DOMAIN, SERVICE_CONSUME, consume, CONSUME_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STORE, store, STORE_SCHEMA)


def _targeted_items(
    hass: HomeAssistant, call: ServiceCall
) -> list[InventoryManagerItem]:
    """
    Find the items targeted by an action call.

    Targeting a device (or area, ...) resolves to all of its entities, and
    every entity of an item leads to that item, so each item is only
    returned once.
    """
    selected = async_extract_referenced_entity_ids(hass, TargetSelection(call.data))
    registry = er.async_get(hass)

    entry_ids: set[str] = set()
    for entity_id in selected.referenced | selected.indirectly_referenced:
        entity = registry.async_get(entity_id)
        if entity is not None and entity.platform == DOMAIN and entity.config_entry_id:
            entry_ids.add(entity.config_entry_id)

    items = []
    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.state is ConfigEntryState.LOADED:
            items.append(entry.runtime_data.coordinator)

    if not items:
        msg = "No inventory item found for the given target"
        raise ServiceValidationError(msg)
    return items
