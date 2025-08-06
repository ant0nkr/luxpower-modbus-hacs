from typing import Final
from homeassistant.const import Platform

DOMAIN = "lxp_modbus"

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.TIME,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.SWITCH,
]

CONF_HOST = "host"
CONF_PORT = "port"
CONF_DONGLE_SERIAL = "dongle_serial"
CONF_INVERTER_SERIAL = "inverter_serial"
CONF_POLL_INTERVAL = "poll_interval"
CONF_ENTITY_PREFIX = "entity_prefix"
CONF_RATED_POWER = "rated_power"
CONF_READ_ONLY = "read_only"

INTEGRATION_TITLE = "LuxPower Inverter (Modbus)"


DEFAULT_POLL_INTERVAL = 10  # or whatever default you prefer, in seconds
DEFAULT_ENTITY_PREFIX = ""
DEFAULT_RATED_POWER = 5000
DEFAULT_READ_ONLY = False
DEFAULT_PORT = 8000

REGISTER_BLOCK_SIZE = 40
TOTAL_REGISTERS = 250
RESPONSE_OVERHEAD: Final = 37 # minimum resposne length received from inverter (technical information)
MAX_RETRIES = 3
WRITE_RESPONSE_LENGTH = 76 # Based on documentation for a single write ack