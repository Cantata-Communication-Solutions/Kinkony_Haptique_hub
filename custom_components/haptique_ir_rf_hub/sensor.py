"""Sensor platform for Haptique IR/RF hub."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device import build_device_info, get_firmware_version

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Haptique IR/RF hub sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    sensors = [
        HaptiqueWifiStatusSensor(coordinator, entry),
        HaptiqueRfCountSensor(coordinator, entry),
        HaptiqueVersionSensor(coordinator, entry),
        HaptiqueHostnameSensor(coordinator, entry),
        HaptiqueIpAddressSensor(coordinator, entry),
    ]
    
    async_add_entities(sensors)


class HaptiqueBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Haptique sensors."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry

        self._attr_device_info = build_device_info(
            entry.entry_id,
            entry.title,
            coordinator.data.get("status", {}),
        )


class HaptiqueWifiStatusSensor(HaptiqueBaseSensor):
    """WiFi status sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "WiFi Status"
        self._attr_unique_id = f"{entry.entry_id}_wifi_status"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        status = self.coordinator.data.get("status", {})
        
        # Check for sta_ok field (boolean) first
        if "sta_ok" in status:
            return "Connected" if status.get("sta_ok") else "Disconnected"
        
        # Fall back to wifi_status (numeric) if sta_ok not present
        wifi_status = status.get("wifi_status", "unknown")
        if wifi_status == 3:
            return "Connected"
        elif wifi_status == 6:
            return "Disconnected"
        else:
            return f"Status {wifi_status}"

    @property
    def icon(self):
        """Return icon based on connection status."""
        status = self.coordinator.data.get("status", {})
        
        # Check sta_ok first
        if "sta_ok" in status:
            return "mdi:wifi" if status.get("sta_ok") else "mdi:wifi-off"
        
        # Fall back to wifi_status
        wifi_status = status.get("wifi_status", 0)
        return "mdi:wifi" if wifi_status == 3 else "mdi:wifi-off"

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        status = self.coordinator.data.get("status", {})
        attrs = {}
        
        # Try both field name variations
        if "sta_ssid" in status:
            attrs["ssid"] = status.get("sta_ssid", "N/A")
        else:
            attrs["ssid"] = status.get("ssid", "N/A")
        
        attrs["rssi"] = status.get("rssi", 0)
        
        # Try both IP field variations
        if "sta_ip" in status:
            attrs["local_ip"] = status.get("sta_ip", "N/A")
        else:
            attrs["local_ip"] = status.get("local_ip", "N/A")
        
        return attrs


class HaptiqueRfCountSensor(HaptiqueBaseSensor):
    """RF receive count sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "RF Received Count"
        self._attr_unique_id = f"{entry.entry_id}_rf_count"
        self._attr_icon = "mdi:radio-tower"
        self._attr_native_unit_of_measurement = "signals"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Try getting from rf_status first
        rf_status = self.coordinator.data.get("rf_status", {})
        if "rx_count" in rf_status:
            return rf_status.get("rx_count", 0)
        
        # Fall back to status.rf.rx_count
        status = self.coordinator.data.get("status", {})
        rf_data = status.get("rf", {})
        return rf_data.get("rx_count", 0)

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        # Try rf_status first
        rf_status = self.coordinator.data.get("rf_status", {})
        if rf_status:
            return {
                "last_code": rf_status.get("last_code", 0),
                "last_bits": rf_status.get("last_bits", 0),
                "last_protocol": rf_status.get("last_protocol", 0),
                "rf_rx_pin": rf_status.get("rf_rx_pin", 0),
                "rf_tx_pin": rf_status.get("rf_tx_pin", 0),
            }
        
        # Fall back to status.rf
        status = self.coordinator.data.get("status", {})
        rf_data = status.get("rf", {})
        return {
            "last_code": rf_data.get("last_code", 0),
            "last_bits": rf_data.get("last_bits", 0),
            "rf_rx_pin": status.get("rf_rx", 0),
            "rf_tx_pin": status.get("rf_tx", 0),
        }


class HaptiqueVersionSensor(HaptiqueBaseSensor):
    """Firmware version sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Firmware Version"
        self._attr_unique_id = f"{entry.entry_id}_version"
        self._attr_icon = "mdi:chip"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return get_firmware_version(self.coordinator.data.get("status", {}))


class HaptiqueHostnameSensor(HaptiqueBaseSensor):
    """Hostname sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "Hostname"
        self._attr_unique_id = f"{entry.entry_id}_hostname"
        self._attr_icon = "mdi:network"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        status = self.coordinator.data.get("status", {})
        return status.get("hostname", "Unknown")


class HaptiqueIpAddressSensor(HaptiqueBaseSensor):
    """IP Address sensor."""

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_name = "IP Address"
        self._attr_unique_id = f"{entry.entry_id}_ip"
        self._attr_icon = "mdi:ip-network"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        status = self.coordinator.data.get("status", {})
        # Try sta_ip first (actual API field), fall back to local_ip
        return status.get("sta_ip") or status.get("local_ip", "N/A")

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        status = self.coordinator.data.get("status", {})
        return {
            "mac": status.get("mac", "N/A"),
            "gateway": status.get("gateway", "N/A"),
        }
