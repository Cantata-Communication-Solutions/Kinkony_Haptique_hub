"""Shared device metadata helpers for the Haptique IR/RF hub integration."""

from typing import Any

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL


def get_firmware_version(status: dict[str, Any] | None) -> str:
    """Return the firmware version from the device status payload."""
    if not status:
        return "Unknown"

    return status.get("fw_ver") or status.get("version") or "Unknown"


def build_device_info(
    entry_id: str, entry_title: str, status: dict[str, Any] | None
) -> DeviceInfo:
    """Build a consistent device-info payload for all entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=entry_title,
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=get_firmware_version(status),
    )
