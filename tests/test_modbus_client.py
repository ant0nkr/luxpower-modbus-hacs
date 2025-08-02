import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient

# Import dummy data
from tests.test_data import INPUT_RESPONSES, HOLD_RESPONSES

DUMMY_HOST = "127.0.0.1"
DUMMY_PORT = 8000

@pytest.fixture
def api_client():
    lock = asyncio.Lock()
    return LxpModbusApiClient(
        host=DUMMY_HOST,
        port=DUMMY_PORT,
        dongle_serial="DUMMY_DONGLE",
        inverter_serial="DUMMY00001",
        lock=lock,
        block_size=2
    )


import itertools

@pytest.mark.parametrize("response_key,response_dict", INPUT_RESPONSES.items())
@patch("custom_components.lxp_modbus.classes.modbus_client.asyncio.open_connection")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpRequestBuilder")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpResponse")
def test_async_get_data_input_response(mock_response, mock_builder, mock_open_conn, api_client, response_key, response_dict):
    reader = MagicMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.close = AsyncMock()
    writer.wait_closed = AsyncMock()
    mock_open_conn.return_value = (reader, writer)
    mock_builder.prepare_packet_for_read.return_value = b"request"
    # Simulate valid responses for input and hold
    input_response = MagicMock()
    input_response.packet_error = False
    input_response.serial_number = api_client._inverter_serial.encode()
    input_response.device_function = 4
    input_response.parsed_values_dictionary = {i: i*10 for i in range(1, 3)}
    hold_response = MagicMock()
    hold_response.packet_error = False
    hold_response.serial_number = api_client._inverter_serial.encode()
    hold_response.device_function = 3
    hold_response.parsed_values_dictionary = {i: i*10 for i in range(1, 3)}
    mock_response.side_effect = [input_response, hold_response]
    input_bytes = bytes.fromhex(response_dict["response_hex"])
    reader.read = AsyncMock(side_effect=[input_bytes, input_bytes])

    with (
        patch("custom_components.lxp_modbus.classes.modbus_client.TOTAL_REGISTERS", 2),
        patch("custom_components.lxp_modbus.classes.modbus_client.RESPONSE_OVERHEAD", 0)
    ):
        result = asyncio.run(api_client.async_get_data())
        expected = {i: i*10 for i in range(1, 3)}
        assert result["input"] == expected
        assert result["hold"] == expected


@pytest.mark.parametrize("response_key,response_dict", HOLD_RESPONSES.items())
@patch("custom_components.lxp_modbus.classes.modbus_client.asyncio.open_connection")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpRequestBuilder")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpResponse")
def test_async_get_data_hold_response(mock_response, mock_builder, mock_open_conn, api_client, response_key, response_dict):
    reader = MagicMock()
    writer = MagicMock()
    writer.drain = AsyncMock()
    writer.close = AsyncMock()
    writer.wait_closed = AsyncMock()
    mock_open_conn.return_value = (reader, writer)
    mock_builder.prepare_packet_for_read.return_value = b"request"
    # Simulate valid responses for input and hold
    input_response = MagicMock()
    input_response.packet_error = False
    input_response.serial_number = api_client._inverter_serial.encode()
    input_response.device_function = 4
    input_response.parsed_values_dictionary = {i: i*100 for i in range(1, 3)}
    hold_response = MagicMock()
    hold_response.packet_error = False
    hold_response.serial_number = api_client._inverter_serial.encode()
    hold_response.device_function = 3
    hold_response.parsed_values_dictionary = {i: i*100 for i in range(1, 3)}
    mock_response.side_effect = [input_response, hold_response]
    hold_bytes = bytes.fromhex(response_dict["response_hex"])
    reader.read = AsyncMock(side_effect=[hold_bytes, hold_bytes])

    with (
        patch("custom_components.lxp_modbus.classes.modbus_client.TOTAL_REGISTERS", 2),
        patch("custom_components.lxp_modbus.classes.modbus_client.RESPONSE_OVERHEAD", 0)
    ):
        result = asyncio.run(api_client.async_get_data())
        expected = {i: i*100 for i in range(1, 3)}
        assert result["input"] == expected
        assert result["hold"] == expected
