"""Button platform for Haptique IR/RF hub."""
import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Haptique IR/RF hub buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    
    entities = []
    
    # Create button entities for saved RF commands
    rf_saved = coordinator.data.get("rf_saved", [])
    for command in rf_saved:
        entities.append(
            HaptiqueRFButton(coordinator, api, entry, command["name"])
        )
    
    # Create button entities for saved IR commands
    ir_saved = coordinator.data.get("ir_saved", [])
    for command in ir_saved:
        entities.append(
            HaptiqueIRButton(coordinator, api, entry, command["name"])
        )
    
    async_add_entities(entities)


class HaptiqueRFButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Haptique RF command button."""

    def __init__(self, coordinator, api, entry, command_name):
        """Initialize the button."""
        super().__init__(coordinator)
        self._api = api
        self._command_name = command_name
        self._attr_name = f"RF {command_name}"
        self._attr_unique_id = f"{entry.entry_id}_rf_{command_name}"

        self._attr_device_info = build_device_info(
            entry.entry_id,
            entry.title,
            coordinator.data.get("status", {}),
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self._api.send_rf_saved(self._command_name)
            _LOGGER.info("RF command '%s' sent successfully", self._command_name)
        except Exception as err:
            _LOGGER.error("Failed to send RF command '%s': %s", self._command_name, err)


class HaptiqueIRButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Haptique IR command button."""

    def __init__(self, coordinator, api, entry, command_name):
        """Initialize the button."""
        super().__init__(coordinator)
        self._api = api
        self._command_name = command_name
        self._attr_name = f"IR {command_name}"
        self._attr_unique_id = f"{entry.entry_id}_ir_{command_name}"

        self._attr_device_info = build_device_info(
            entry.entry_id,
            entry.title,
            coordinator.data.get("status", {}),
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            await self._api.send_ir_saved(self._command_name)
            _LOGGER.info("IR command '%s' sent successfully", self._command_name)
        except Exception as err:
            _LOGGER.error("Failed to send IR command '%s': %s", self._command_name, err)
