import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from custom_components.lxp_modbus.classes.modbus_client import LxpModbusApiClient

@pytest.fixture
def api_client():
    lock = asyncio.Lock()  # Use real lock, not AsyncMock
    return LxpModbusApiClient(
        host="127.0.0.1",
        port=1234,
        dongle_serial="DONGLE123",
        inverter_serial="INV123",
        lock=lock
    )

@patch("custom_components.lxp_modbus.classes.modbus_client.asyncio.open_connection")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpRequestBuilder")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpResponse")
def test_async_get_data_success(mock_response, mock_builder, mock_open_conn, api_client):
    # Setup mocks
    reader = AsyncMock()
    writer = AsyncMock()
    reader.read = AsyncMock(return_value=b"x" * 64)  # or 16 for write test
    writer.write = MagicMock()
    writer.drain = AsyncMock()

    mock_open_conn.return_value = (reader, writer)
    mock_builder.prepare_packet_for_read.return_value = b"request"
    # Simulate valid response
    response_instance = MagicMock()
    response_instance.packet_error = False
    response_instance.parsed_values_dictionary = {1: 100}
    mock_response.return_value = response_instance
    reader.read.return_value = b"x" * 64  # RESPONSE_LENGTH_EXPECTED

    # Patch constants
    with patch("custom_components.lxp_modbus.classes.modbus_client.TOTAL_REGISTERS", 1), \
         patch("custom_components.lxp_modbus.classes.modbus_client.REGISTER_BLOCK_SIZE", 1), \
         patch("custom_components.lxp_modbus.classes.modbus_client.RESPONSE_LENGTH_EXPECTED", 64):
        data = asyncio.run(api_client.async_get_data())
        assert data["input"] == {1: 100}
        assert data["hold"] == {1: 100}

@patch("custom_components.lxp_modbus.classes.modbus_client.asyncio.open_connection")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpRequestBuilder")
@patch("custom_components.lxp_modbus.classes.modbus_client.LxpResponse")
def test_async_write_register_success(mock_response, mock_builder, mock_open_conn, api_client):
    reader = AsyncMock()
    writer = AsyncMock()
    reader.read = AsyncMock(return_value=b"x" * 64)  # or 16 for write test
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    
    mock_open_conn.return_value = (reader, writer)
    mock_builder.prepare_packet_for_write.return_value = b"request"
    response_instance = MagicMock()
    response_instance.packet_error = False
    response_instance.parsed_values_dictionary = {5: 200}
    mock_response.return_value = response_instance
    reader.read.return_value = b"x" * 16  # WRITE_RESPONSE_LENGTH

    with patch("custom_components.lxp_modbus.classes.modbus_client.MAX_RETRIES", 1), \
         patch("custom_components.lxp_modbus.classes.modbus_client.WRITE_RESPONSE_LENGTH", 16):
        result = asyncio.run(api_client.async_write_register(5, 200))
        assert result is True

@patch("custom_components.lxp_modbus.classes.modbus_client.asyncio.open_connection", side_effect=Exception("fail"))
def test_async_get_data_exception(mock_open_conn, api_client):
    with patch("custom_components.lxp_modbus.classes.modbus_client.TOTAL_REGISTERS", 1), \
         patch("custom_components.lxp_modbus.classes.modbus_client.REGISTER_BLOCK_SIZE", 1), \
         patch("custom_components.lxp_modbus.classes.modbus_client.RESPONSE_LENGTH_EXPECTED", 64):
        with pytest.raises(Exception):
            asyncio.run(api_client.async_get_data())