"""The LuxPower Modbus Integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import *
from .classes.lxp_request_builder import LxpRequestBuilder
from .classes.lxp_response import LxpResponse
from .classes.modbus_client import LxpModbusApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the LuxPower Modbus component from a config entry."""
    # Ensure the top-level dictionary for our integration exists in hass.data
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration values from the config entry
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    dongle_serial = entry.data[CONF_DONGLE_SERIAL]
    inverter_serial = entry.data[CONF_INVERTER_SERIAL]
    poll_interval = entry.data[CONF_POLL_INTERVAL]

    # Create a single asyncio.Lock to prevent read/write race conditions
    lock = asyncio.Lock()
    api_client = LxpModbusApiClient(host, port, dongle_serial, inverter_serial, lock)

    # Create the DataUpdateCoordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{INTEGRATION_TITLE} ({entry.title})",
        update_method=api_client.async_get_data,
        update_interval=timedelta(seconds=poll_interval),
    )
    
    # Store the coordinator and other shared objects in hass.data for this entry
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "settings": {**entry.data, **entry.options},
        "lock": lock,
        "api_client": api_client
    }

    # Perform the first data refresh. This will block setup until the first poll is
    # successful. It also handles exceptions and configuration entry setup retries.
    await coordinator.async_config_entry_first_refresh()

    # Forward the setup to all platforms (sensor, number, etc.)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # The DataUpdateCoordinator handles its own background task cancellation.
    # We just need to unload the platforms and clean up our data.
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok