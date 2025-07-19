import asyncio
import logging

from homeassistant.helpers.update_coordinator import UpdateFailed

from ..const import *
from .lxp_request_builder import LxpRequestBuilder
from .lxp_response import LxpResponse


_LOGGER = logging.getLogger(__name__)

class LxpModbusApiClient:
    """A client for communicating with a LuxPower inverter."""

    def __init__(self, host: str, port: int, dongle_serial: str, inverter_serial: str, lock: asyncio.Lock):
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._dongle_serial = dongle_serial
        self._inverter_serial = inverter_serial
        self._lock = lock
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

                # Poll INPUT registers
                for reg in range(0, TOTAL_REGISTERS, REGISTER_BLOCK_SIZE):
                    count = min(REGISTER_BLOCK_SIZE, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 4)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(RESPONSE_LENGTH_EXPECTED)
                    
                    _LOGGER.debug(
                        "Polling INPUT %d-%d: Req[%d]: %s, Resp[%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        response_buf.hex() if response_buf else "None"
                    )

                    if response_buf and len(response_buf) == RESPONSE_LENGTH_EXPECTED:
                        response = LxpResponse(response_buf)
                        if not response.packet_error:
                            newly_polled_input_regs.update(response.parsed_values_dictionary)
                        else:
                            input_read_success = False # Mark as failed
                    else:
                        input_read_success = False # Mark as failed

                # Poll HOLD registers
                for reg in range(0, TOTAL_REGISTERS, REGISTER_BLOCK_SIZE):
                    count = min(REGISTER_BLOCK_SIZE, TOTAL_REGISTERS - reg)
                    req = LxpRequestBuilder.prepare_packet_for_read(self._dongle_serial.encode(), self._inverter_serial.encode(), reg, count, 3)
                    writer.write(req)
                    await writer.drain()
                    response_buf = await reader.read(RESPONSE_LENGTH_EXPECTED)
                    
                    _LOGGER.debug(
                        "Polling HOLD %d-%d: Req[%d]: %s, Resp[%d]: %s",
                        reg, reg + count - 1,
                        len(req),
                        req.hex(),
                        len(response_buf) if response_buf else 0,
                        response_buf.hex() if response_buf else "None"
                    )
                    
                    if response_buf and len(response_buf) == RESPONSE_LENGTH_EXPECTED:
                        response = LxpResponse(response_buf)
                        if not response.packet_error:
                            newly_polled_hold_regs.update(response.parsed_values_dictionary)
                        else:
                            hold_read_success = False # Mark as failed
                    else:
                        hold_read_success = False # Mark as failed

                await writer.close()
                await writer.wait_closed()
            
            # Merge new data with the last known good data
            if input_read_success:
                self._last_good_input_regs = newly_polled_input_regs
            else:
                _LOGGER.warning("Input poll failed; retaining previous input register data.")

            if hold_read_success:
                self._last_good_hold_regs = newly_polled_hold_regs
            else:
                _LOGGER.warning("Hold poll failed; retaining previous hold register data.")

            # Always return a complete (though possibly stale) dataset
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

                    await writer.close()
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