"""Config flow for Haptique IR/RF hub integration."""
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_NAME, DOMAIN
from .device import get_firmware_version

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_TOKEN, default=""): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    token = data.get(CONF_TOKEN, "")
    
    session = async_get_clientsession(hass)
    
    # Try to connect
    url = f"http://{host}/api/status"
    headers = {}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 401:
                raise Exception("Authentication required. Please provide a valid token from /api/token")
            
            resp.raise_for_status()
            device_info = await resp.json()
        
        # Return info that you want to store in the config entry
        return {
            "title": device_info.get("hostname", DEFAULT_NAME),
            "version": get_firmware_version(device_info),
        }
    except aiohttp.ClientError as err:
        raise Exception(f"Cannot connect to device: {err}")
    except Exception as err:
        raise Exception(f"Validation error: {err}")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Haptique IR/RF hub."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except Exception as err:
                _LOGGER.error("Validation failed: %s", err)
                errors["base"] = "cannot_connect"
            else:
                # Create unique ID from host
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
