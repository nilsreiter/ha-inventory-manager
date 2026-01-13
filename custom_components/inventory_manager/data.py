"""Data classes for Inventory Manager integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

    from .coordinator import InventoryManagerItem

type InventoryManagerConfigEntry = ConfigEntry[InventoryManagerData]


@dataclass
class InventoryManagerData:
    """The class represents the inventory manager data."""

    device_info: DeviceInfo
    coordinator: InventoryManagerItem
