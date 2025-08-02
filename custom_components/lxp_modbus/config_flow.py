import asyncio
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import *
from .classes.lxp_request_builder import LxpRequestBuilder
from .classes.lxp_response import LxpResponse
from .utils import decode_model_from_registers

_LOGGER = logging.getLogger(__name__)

def validate_serial(value):
    """Validate that the serial number is exactly 10 characters."""
    value = str(value)
    if len(value) != 10:
        raise vol.Invalid("Serial number must be exactly 10 characters.")
    return value

async def get_inverter_model_from_device(host, port, dongle_serial, inverter_serial):
    """Attempt to connect to the inverter and read the model."""
    try:
        reader, writer = await asyncio.open_connection(host, port)
        req = LxpRequestBuilder.prepare_packet_for_read(dongle_serial.encode(), inverter_serial.encode(), 7, 2, 3)
        writer.write(req)
        await writer.drain()
        response_buf = await reader.read(512)
        writer.close()
        await writer.wait_closed()
        if not response_buf: return None
        response = LxpResponse(response_buf)
        if response.packet_error: return None
        model = decode_model_from_registers(response.parsed_values_dictionary)
        return model
    except Exception:
        return None

class LxpModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow for the component."""
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return LxpModbusOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_serial(user_input[CONF_DONGLE_SERIAL])
                validate_serial(user_input[CONF_INVERTER_SERIAL])
                model = await get_inverter_model_from_device(user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_DONGLE_SERIAL], user_input[CONF_INVERTER_SERIAL])
                if not model:
                    errors["base"] = "model_fetch_failed"
                else:
                    user_input["model"] = model
                    title = user_input.get(CONF_ENTITY_PREFIX) or "Luxpower Inverter"
                    return self.async_create_entry(title=title, data=user_input)
            except vol.Invalid:
                errors["base"] = "invalid_serial"
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=8000): int,
            vol.Required(CONF_DONGLE_SERIAL): str,
            vol.Required(CONF_INVERTER_SERIAL): str,
            vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(int, vol.Range(min=2, max=600)),
            vol.Optional(CONF_ENTITY_PREFIX, default=DEFAULT_ENTITY_PREFIX): str,
            vol.Required(CONF_RATED_POWER, default=DEFAULT_RATED_POWER): vol.All(int, vol.Range(min=1000, max=100000)),
            vol.Required(CONF_REGISTER_BLOCK_SIZE, default=DEFAULT_REGISTER_BLOCK_SIZE): vol.In({40: "40 (Older Firmware)", 127: "127 (Newer Firmware)"}),
            vol.Optional(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
        })
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(data_schema, user_input), errors=errors)

# This class now explicitly defines __init__ to resolve the error.
class LxpModbusOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow (reconfiguration) for the component."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        # self.config_entry is automatically available here
        current_config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            try:
                validate_serial(user_input[CONF_DONGLE_SERIAL])
                validate_serial(user_input[CONF_INVERTER_SERIAL])

                model = await get_inverter_model_from_device(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_DONGLE_SERIAL],
                    user_input[CONF_INVERTER_SERIAL]
                )
                if not model:
                    errors["base"] = "model_fetch_failed"
                else:
                    new_data = {**current_config, **user_input}
                    new_data["model"] = model
                    
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data, options={}
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title="", data={})

            except vol.Invalid:
                errors["base"] = "invalid_serial"
        
        options_schema = vol.Schema({
            vol.Required(CONF_HOST, default=current_config.get(CONF_HOST)): str,
            vol.Required(CONF_PORT, default=current_config.get(CONF_PORT)): int,
            vol.Required(CONF_DONGLE_SERIAL, default=current_config.get(CONF_DONGLE_SERIAL)): str,
            vol.Required(CONF_INVERTER_SERIAL, default=current_config.get(CONF_INVERTER_SERIAL)): str,
            vol.Required(CONF_POLL_INTERVAL, default=current_config.get(CONF_POLL_INTERVAL)): vol.All(int, vol.Range(min=2, max=600)),
            vol.Optional(CONF_ENTITY_PREFIX, default=current_config.get(CONF_ENTITY_PREFIX, '')): vol.All(str),
            vol.Required(CONF_RATED_POWER, default=current_config.get(CONF_RATED_POWER)): vol.All(int, vol.Range(min=1000, max=100000)),
            vol.Required(CONF_REGISTER_BLOCK_SIZE, default=DEFAULT_REGISTER_BLOCK_SIZE): vol.In({40: "40 (Older Firmware)", 127: "127 (Newer Firmware)"}),
            vol.Optional(CONF_READ_ONLY, default=DEFAULT_READ_ONLY): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(options_schema, current_config),
            errors=errors,
        )