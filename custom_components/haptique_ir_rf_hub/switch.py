"""Switch platform for Haptique IR/RF hub."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device import build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Haptique IR/RF hub switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    
    switches = [
        HaptiqueAPSwitch(coordinator, api, entry),
    ]
    
    async_add_entities(switches)


class HaptiqueAPSwitch(CoordinatorEntity, SwitchEntity):
    """Access Point on/off switch."""

    def __init__(self, coordinator, api, entry):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._api = api
        self._attr_name = "Access Point"
        self._attr_unique_id = f"{entry.entry_id}_ap_switch"
        self._attr_icon = "mdi:access-point"

        self._attr_device_info = build_device_info(
            entry.entry_id,
            entry.title,
            coordinator.data.get("status", {}),
        )

    @property
    def is_on(self):
        """Return true if AP is on."""
        status = self.coordinator.data.get("status", {})
        return status.get("ap_enabled", False)

    async def async_turn_on(self, **kwargs):
        """Turn AP on - not supported via API."""
        _LOGGER.warning("Turning AP on is not supported via API")

    async def async_turn_off(self, **kwargs):
        """Turn AP off."""
        try:
            await self._api._request("POST", "/api/ap/disable")
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to disable AP: %s", err)
