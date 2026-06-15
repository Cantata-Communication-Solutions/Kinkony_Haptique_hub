"""Haptique IR/RF hub integration for Home Assistant."""
import asyncio
import logging
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any

import aiohttp
import async_timeout
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, MODEL
from .device import get_firmware_version

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]
STATIC_FILES_REGISTERED = "_static_files_registered"
SERVICES_REGISTERED = "_services_registered"


def _copy_static_files(integration_path: str, destination_path: str) -> Path | None:
    """Copy bundled frontend assets into Home Assistant's www directory."""
    src_www = Path(integration_path) / "www"
    if not src_www.is_dir():
        return None

    dest = Path(destination_path)
    dest.mkdir(parents=True, exist_ok=True)

    for src_file in src_www.iterdir():
        if src_file.is_file():
            shutil.copy2(src_file, dest / src_file.name)

    return dest


async def async_register_static_files(hass: HomeAssistant) -> None:
    """Copy and register the integration's static assets once per HA instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(STATIC_FILES_REGISTERED):
        return

    try:
        dest = await hass.async_add_executor_job(
            _copy_static_files,
            hass.config.path("custom_components", DOMAIN),
            hass.config.path("www", "community", DOMAIN),
        )
    except OSError as err:
        _LOGGER.warning("Unable to copy static files for %s: %s", DOMAIN, err)
        return

    if dest is None:
        _LOGGER.debug("No static files found for %s", DOMAIN)
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(f"/{DOMAIN}", str(dest), False)]
        )
    except Exception as err:  # pragma: no cover - Home Assistant handles specifics
        _LOGGER.warning("Unable to register static files for %s: %s", DOMAIN, err)
        return

    domain_data[STATIC_FILES_REGISTERED] = True
    _LOGGER.info("Static files served at: /%s/", DOMAIN)


def _get_default_api(hass: HomeAssistant):
    """Return the first configured API instance for service handlers."""
    domain_data = hass.data.get(DOMAIN, {})
    for value in domain_data.values():
        if isinstance(value, dict) and "api" in value:
            return value["api"]

    raise HomeAssistantError("No configured Haptique IR/RF hub entry is available")





async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Haptique IR/RF hub from a config entry."""
    host = entry.data[CONF_HOST]
    token = entry.data.get(CONF_TOKEN, "")
    
  
    session = async_get_clientsession(hass)
    api = HaptiqueGatewayAPI(host, token, session)
    
    try:
        await api.get_status()
    except Exception as err:
        _LOGGER.error("Failed to connect to  Haptique IR/RF hub: %s", err)
        return False
    
   
    coordinator = HaptiqueDataUpdateCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    status = coordinator.data.get("status", {})
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=entry.title,
        sw_version=get_firmware_version(status),
    )

    await async_setup_services(hass)
    await async_register_static_files(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok



async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Haptique IR/RF hub."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(SERVICES_REGISTERED):
        return

    async def send_rf_code(call):
        """Send RF code service."""
        api = _get_default_api(hass)
        code = call.data.get("code")
        bits = call.data.get("bits", 24)
        protocol = call.data.get("protocol", 1)
        repeat = call.data.get("repeat", 8)

        await api.send_rf_code(code, bits, protocol, repeat)

    async def send_rf_saved(call):
        """Send saved RF command service."""
        api = _get_default_api(hass)
        name = call.data.get("name")
        await api.send_rf_saved(name)

    async def send_ir_code(call):
        """Send IR code service."""
        api = _get_default_api(hass)
        freq = call.data.get("frequency", 38000)
        duty = call.data.get("duty", 33)
        raw_data = call.data.get("raw_data", [])

        await api.send_ir_code(freq, duty, raw_data)

    async def send_ir_saved(call):
        """Send saved IR command service."""
        api = _get_default_api(hass)
        name = call.data.get("name")
        await api.send_ir_saved(name)

    async def save_rf_last(call):
        """Save last received RF command."""
        api = _get_default_api(hass)
        name = call.data.get("name")
        await api.save_rf_command(name)

    async def save_ir_last(call):
        api = _get_default_api(hass)
        name = call.data.get("name")
        frame = call.data.get("frame", "B")  # default frame B
        await api.save_ir_command(name, frame)

    async def delete_rf_command(call):
        """Delete saved RF command."""
        api = _get_default_api(hass)
        name = call.data.get("name")
        await api.delete_rf_command(name)

    async def delete_ir_command(call):
        """Delete saved IR command."""
        api = _get_default_api(hass)
        name = call.data.get("name")
        await api.delete_ir_command(name)

    # Register all services
    hass.services.async_register(DOMAIN, "send_rf_code", send_rf_code)
    hass.services.async_register(DOMAIN, "send_rf_saved", send_rf_saved)
    hass.services.async_register(DOMAIN, "send_ir_code", send_ir_code)
    hass.services.async_register(DOMAIN, "send_ir_saved", send_ir_saved)
    hass.services.async_register(DOMAIN, "save_rf_last", save_rf_last)
    hass.services.async_register(DOMAIN, "save_ir_last", save_ir_last)
    hass.services.async_register(DOMAIN, "delete_rf_command", delete_rf_command)
    hass.services.async_register(DOMAIN, "delete_ir_command", delete_ir_command)
    domain_data[SERVICES_REGISTERED] = True



class HaptiqueDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Haptique IR/RF hub data."""

    def __init__(self, hass: HomeAssistant, api) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                status = await self.api.get_status()
                rf_status = await self.api.get_rf_status()
                rf_saved = await self.api.get_rf_saved()
                ir_saved = await self.api.get_ir_saved()
                
                return {
                    "status": status,
                    "rf_status": rf_status,
                    "rf_saved": rf_saved,
                    "ir_saved": ir_saved,
                }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}")



class HaptiqueGatewayAPI:
    """API client for Haptique IR/RF hub."""

    def __init__(self, host: str, token: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self.host = host
        self.token = token
        self.session = session
        self.base_url = f"http://{host}"
        
    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make API request with authentication."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            async with async_timeout.timeout(10):
                async with self.session.request(
                    method, url, headers=headers, **kwargs
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to {url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error connecting to {url}: {err}") from err
    
    async def get_status(self) -> dict:
        """Get device status."""
        return await self._request("GET", "/api/status")
    
    async def get_rf_status(self) -> dict:
        """Get RF status."""
        return await self._request("GET", "/api/rf/status")
    
    async def get_rf_saved(self) -> list:
        """Get saved RF commands."""
        result = await self._request("GET", "/api/rf/saved")
        return result.get("commands", [])
    
    async def get_ir_saved(self) -> list:
        """Get saved IR commands."""
        result = await self._request("GET", "/api/ir/saved")
        return result.get("commands", [])
    
    async def send_rf_code(self, code: int, bits: int, protocol: int, repeat: int) -> dict:
        """Send RF code."""
        return await self._request(
            "POST",
            "/api/rf/send",
            json={
                "code": code,
                "bits": bits,
                "protocol": protocol,
                "repeat": repeat
            }
        )
    
    async def send_rf_saved(self, name: str) -> dict:
        """Send saved RF command."""
        return await self._request("POST", "/api/rf/send/name", json={"name": name})
    
    async def send_ir_code(self, freq: int, duty: int, raw_data: list) -> dict:
        """Send IR code."""
        return await self._request(
            "POST",
            "/api/ir/send",
            json={
                "freq": freq,
                "duty": duty,
                "raw": raw_data
            }
        )
    
    async def send_ir_saved(self, name: str) -> dict:
        """Send saved IR command."""
        return await self._request("POST", "/api/ir/send/name", json={"name": name})
    
    async def save_rf_command(self, name: str) -> dict:
        """Save last received RF command."""
        return await self._request("POST", "/api/rf/save", json={"name": name})
    
    async def save_ir_command(self, name: str, frame: str) -> dict:
        return await self._request(
            "POST",
            "/api/ir/save",
            json={
                "name": name,
                "frame": frame
            }
        )

    
    async def delete_rf_command(self, name: str) -> dict:
        """Delete saved RF command."""
        return await self._request("DELETE", "/api/rf/delete", json={"name": name})
    
    async def delete_ir_command(self, name: str) -> dict:
        """Delete saved IR command."""
        return await self._request("DELETE", "/api/ir/delete", json={"name": name})
