import asyncio
import logging

from homeassistant.helpers.update_coordinator import UpdateFailed

from ..const import *
from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse

from ..constants.hold_registers import (
    H_AC_CHARGE_START_TIME, H_AC_CHARGE_END_TIME, H_AC_CHARGE_START_TIME_1, H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2, H_AC_CHARGE_END_TIME_2, H_AC_FIRST_START_TIME, H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1, H_AC_FIRST_END_TIME_1, H_PEAK_SHAVING_START_TIME, H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1, H_PEAK_SHAVING_END_TIME_1
)

_LOGGER = logging.getLogger(__name__)

HOLD_TIME_REGISTERS = {
    H_AC_CHARGE_START_TIME,
    H_AC_CHARGE_END_TIME,
    H_AC_CHARGE_START_TIME_1,
    H_AC_CHARGE_END_TIME_1,
    H_AC_CHARGE_START_TIME_2,
    H_AC_CHARGE_END_TIME_2,
    H_AC_FIRST_START_TIME,
    H_AC_FIRST_END_TIME,
    H_AC_FIRST_START_TIME_1,
    H_AC_FIRST_END_TIME_1,
    H_PEAK_SHAVING_START_TIME,
    H_PEAK_SHAVING_END_TIME,
    H_PEAK_SHAVING_START_TIME_1,
    H_PEAK_SHAVING_END_TIME_1,
}
INPUT_TIME_REGISTERS = set()


def _is_data_sane(registers: dict, register_type: str) -> bool:
    """Performs a sanity check on key values to detect data corruption."""
    time_registers = HOLD_TIME_REGISTERS if register_type == "hold" else INPUT_TIME_REGISTERS
    
    for register, value in registers.items():
        if register in time_registers:
            # The value is packed as Hour | (Minute << 8)
            hour = value & 0xFF
            minute = (value >> 8) & 0xFF
            _LOGGER.debug(f"Sanity check for {register_type} register {register} value: {value}: H={hour}, M={minute}")
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                _LOGGER.warning(f"Sanity check failed for {register_type} register {register}: H={hour}, M={minute}")
                return False
    return True

class LxpModbusApiClient:
    """A client for communicating with a LuxPower inverter."""

    def __init__(self, host: str, port: int, dongle_serial: str, inverter_serial: str, lock: asyncio.Lock, block_size: int):
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._dongle_serial = dongle_serial
        self._inverter_serial = inverter_serial
        self._lock = lock
        self._block_size = block_size
        self._last_good_input_regs = {}
        self._last_good_hold_regs = {}


    async def async_get_data(self) -> dict:
        """Fetch data from the inverter, backfilling with old data on partial failure."""
        _LOGGER.debug("API Client: Polling the inverter for new data...")
        
        try:
            async with self._lock:
                reader, writer = await asyncio.open_connection(self._host, self._port)
                
                newly_polled_input_regs = {}
                newly_polled_hold_regs = {}
                input_read_success = True
                hold_read_success = True

                # Poll INPUT registers (expecting function code 4)
                for reg in range(0, TOTAL_REGISTERS, self._block_size):
                    count = min(self._block_size, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 4)
                    expected_length = RESPONSE_OVERHEAD + (count * 2)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(expected_length)
                    
                    _LOGGER.debug(
                        "Polling INPUT %d-%d: Req[%d]: %s, Resp[%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        response_buf.hex() if response_buf else "None"
                    )

                    if response_buf and len(response_buf) > RESPONSE_OVERHEAD:
                        response = LxpResponse(response_buf)
                        
                        # Check if the packet is generally valid first
                        if not response.packet_error and response.serial_number == self._inverter_serial.encode():
                            parsed_data = response.parsed_values_dictionary
                            # Now, check the ACTUAL function code in the response
                            if response.device_function == 4 and _is_data_sane(parsed_data, "input"):
                                newly_polled_input_regs.update(parsed_data)
                            elif response.device_function == 3 and _is_data_sane(parsed_data, "hold"):
                                _LOGGER.debug("Received HOLD data when expecting INPUT for regs %d-%d. Processing anyway.", reg, reg + count -1)
                                newly_polled_hold_regs.update(parsed_data)
                            else:
                                # The response function code was neither 3 nor 4, or it failed the sanity check
                                input_read_success = False
                        else:
                            input_read_success = False
                    else:
                        input_read_success = False

                # Poll HOLD registers (expecting function code 3)
                for reg in range(0, TOTAL_REGISTERS, self._block_size):
                    count = min(self._block_size, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 3)
                    expected_length = RESPONSE_OVERHEAD + (count * 2)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(expected_length)
                    
                    _LOGGER.debug(
                        "Polling HOLD %d-%d: Req[%d]: %s, Resp[%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        response_buf.hex() if response_buf else "None"
                    )
                    
                    if response_buf and len(response_buf) > RESPONSE_OVERHEAD:
                        response = LxpResponse(response_buf)
                        
                        if not response.packet_error and response.serial_number == self._inverter_serial.encode():
                            parsed_data = response.parsed_values_dictionary
                            
                            if response.device_function == 3 and _is_data_sane(parsed_data, "hold"):
                                newly_polled_hold_regs.update(parsed_data)
                            elif response.device_function == 4 and _is_data_sane(parsed_data, "input"):
                                _LOGGER.debug("Received INPUT data when expecting HOLD for regs %d-%d. Processing anyway.", reg, reg + count -1)
                                newly_polled_input_regs.update(parsed_data)
                            else:
                                hold_read_success = False
                        else:
                            hold_read_success = False
                    else:
                        hold_read_success = False

                writer.close()
                await writer.wait_closed()
            
            # This logic remains exactly as you provided it
            if input_read_success:
                self._last_good_input_regs = newly_polled_input_regs
            else:
                _LOGGER.warning("Input poll failed; retaining previous input register data.")

            if hold_read_success:
                self._last_good_hold_regs = newly_polled_hold_regs
            else:
                _LOGGER.warning("Hold poll failed; retaining previous hold register data.")

            return {"input": self._last_good_input_regs, "hold": self._last_good_hold_regs}

        except Exception as ex:
            _LOGGER.error("Total polling failure: %s", ex)
            raise UpdateFailed(f"Error communicating with inverter: {ex}")


    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register value to the inverter with validation and retries."""
        for attempt in range(MAX_RETRIES):
            try:
                # Use the shared lock to ensure atomicity
                async with self._lock:
                    _LOGGER.debug(f"Write attempt {attempt + 1}/{MAX_RETRIES} for register {register} with value {value}")

                    reader, writer = await asyncio.open_connection(self._host, self._port)

                    req = LxpRequestBuilder.prepare_packet_for_write(
                        self._dongle_serial.encode(), self._inverter_serial.encode(), register, value
                    )
                    writer.write(req)
                    await writer.drain()

                    response_buf = await reader.read(WRITE_RESPONSE_LENGTH)
                    
                    _LOGGER.debug(
                        "Modbus WRITE: Sent to reg %s, value %s, resp: %s",
                        register, value, response_buf.hex() if response_buf else "None"
                    )

                    writer.close()
                    await writer.wait_closed()
                    
                    # --- Response Validation ---
                    if not response_buf:
                        _LOGGER.warning("Write attempt %d failed: Response not received", attempt + 1)
                        await asyncio.sleep(1)
                        continue

                    response = LxpResponse(response_buf)
                    if response.packet_error:
                        _LOGGER.warning("Write attempt %d failed: Inverter returned a packet error.", attempt + 1)
                        await asyncio.sleep(1)
                        continue
                    
                    response_dict = response.parsed_values_dictionary
                    if response_dict.get(register) == value:
                        _LOGGER.info("Successfully wrote register %s with value %s.", register, value)
                        return True # Success!

                    _LOGGER.warning("Write attempt %d failed: Confirmation mismatch.", attempt + 1)
                    await asyncio.sleep(1)

            except Exception as ex:
                _LOGGER.error("Exception during write attempt %d for register %s: %s", attempt + 1, register, ex)
                await asyncio.sleep(1)

        _LOGGER.error("Failed to write register %s after %d attempts.", register, MAX_RETRIES)
        return False