"""
Unit tests for FunASR WebSocket client.

Tests WebSocket connection, reconnection, error handling, and protocol integration.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, InvalidStatusCode

from nextalk.network.ws_client import (
    FunASRWebSocketClient,
    ConnectionState,
    WebSocketError
)
from nextalk.network.protocol import RecognitionResult
from nextalk.config.models import NexTalkConfig


class TestConnectionState:
    """Test ConnectionState enum."""
    
    def test_connection_states(self):
        """Test all connection states are defined."""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.AUTHENTICATING.value == "authenticating"
        assert ConnectionState.READY.value == "ready"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.ERROR.value == "error"
        assert ConnectionState.DEGRADED.value == "degraded"


class TestFunASRWebSocketClient:
    """Test FunASR WebSocket client functionality."""
    
    @pytest.fixture
    def ws_config(self, default_nextalk_config):
        """Create WebSocket client configuration."""
        config = default_nextalk_config
        config.server.host = "localhost"
        config.server.port = 10095
        config.server.use_ssl = False
        config.server.timeout = 5.0
        config.server.reconnect_attempts = 2
        config.server.reconnect_interval = 1.0
        return config
    
    @pytest.fixture
    def ws_client(self, ws_config):
        """Create WebSocket client instance."""
        return FunASRWebSocketClient(ws_config)
    
    def test_client_initialization(self, ws_client, ws_config):
        """Test WebSocket client initialization."""
        assert ws_client.config == ws_config
        assert ws_client.get_state() == ConnectionState.DISCONNECTED
        assert ws_client._websocket is None
        assert ws_client._reconnect_attempts == 0
        assert ws_client._connection_quality == 1.0
    
    def test_callback_setters(self, ws_client):
        """Test callback setter methods."""
        result_callback = Mock()
        error_callback = Mock()
        status_callback = Mock()
        
        ws_client.set_result_callback(result_callback)
        ws_client.set_error_callback(error_callback)
        ws_client.set_status_callback(status_callback)
        
        assert ws_client._result_callback == result_callback
        assert ws_client._error_callback == error_callback
        assert ws_client._status_callback == status_callback
    
    def test_websocket_url_generation(self, ws_client):
        """Test WebSocket URL generation."""
        # Test without SSL
        url = ws_client._get_websocket_url()
        assert url == "ws://localhost:10095"
        
        # Test with SSL
        ws_client.config.server.use_ssl = True
        url = ws_client._get_websocket_url()
        assert url == "wss://localhost:10095"
    
    def test_ssl_context_creation(self, ws_client):
        """Test SSL context creation."""
        # Test without SSL
        ws_client.config.server.use_ssl = False
        context = ws_client._create_ssl_context()
        assert context is None
        
        # Test with SSL but no verification
        ws_client.config.server.use_ssl = True
        ws_client.config.server.ssl_verify = False
        context = ws_client._create_ssl_context()
        assert context is not None
    
    def test_state_management(self, ws_client):
        """Test connection state management."""
        status_callback = Mock()
        ws_client.set_status_callback(status_callback)
        
        # Test state change
        ws_client._set_state(ConnectionState.CONNECTING)
        assert ws_client.get_state() == ConnectionState.CONNECTING
        status_callback.assert_called_once_with(ConnectionState.CONNECTING)
        
        # Test same state (should not call callback again)
        status_callback.reset_mock()
        ws_client._set_state(ConnectionState.CONNECTING)
        status_callback.assert_not_called()
    
    def test_error_recording(self, ws_client):
        """Test error recording functionality."""
        # Record some errors
        ws_client._record_error("test_error", "Test error message")
        ws_client._record_error("network_error", "Network issue", Exception("test"))
        
        # Check error history
        errors = ws_client.get_error_history()
        assert len(errors) == 2
        
        error1 = errors[0]
        assert error1["type"] == "test_error"
        assert error1["message"] == "Test error message"
        assert error1["exception_type"] is None
        
        error2 = errors[1]
        assert error2["type"] == "network_error"
        assert error2["exception_type"] == "Exception"
    
    def test_connection_quality_updates(self, ws_client):
        """Test connection quality tracking."""
        initial_quality = ws_client._connection_quality
        assert initial_quality == 1.0
        
        # Test quality improvement
        ws_client._update_connection_quality(True)
        assert ws_client._connection_quality >= initial_quality
        assert ws_client._ping_failures == 0
        
        # Test quality degradation
        for _ in range(5):  # Multiple failures
            ws_client._update_connection_quality(False)
        
        assert ws_client._connection_quality < initial_quality
        assert ws_client._ping_failures > 0
    
    @pytest.mark.asyncio
    async def test_connect_success(self, ws_client):
        """Test successful connection."""
        mock_websocket = AsyncMock()
        
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            
            # Mock initialization message sending
            with patch.object(ws_client, '_send_init_message') as mock_init:
                mock_init.return_value = None
                
                await ws_client.connect()
                
                assert ws_client.get_state() == ConnectionState.READY
                assert ws_client._websocket == mock_websocket
                assert ws_client._reconnect_attempts == 0
                assert ws_client._connection_quality == 1.0
                
                # Verify connect was called with correct parameters
                mock_connect.assert_called_once()
                call_args = mock_connect.call_args
                assert call_args[0][0] == "ws://localhost:10095"  # URL
                
                # Verify init message was sent
                mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self, ws_client):
        """Test connection timeout."""
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(WebSocketError, match="Connection timeout"):
                await ws_client.connect()
            
            assert ws_client.get_state() == ConnectionState.ERROR
    
    @pytest.mark.asyncio
    async def test_connect_invalid_status_code(self, ws_client):
        """Test connection with invalid status code."""
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.side_effect = InvalidStatusCode(404, {})
            
            with pytest.raises(WebSocketError, match="Server rejected connection"):
                await ws_client.connect()
            
            assert ws_client.get_state() == ConnectionState.ERROR
    
    @pytest.mark.asyncio
    async def test_connect_already_connected(self, ws_client):
        """Test connecting when already connected."""
        ws_client._state = ConnectionState.CONNECTED
        
        # Should not attempt connection
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            await ws_client.connect()
            mock_connect.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, ws_client):
        """Test disconnection."""
        # Set up mock connection state
        mock_websocket = AsyncMock()
        mock_receive_task = AsyncMock()
        mock_ping_task = AsyncMock()
        
        ws_client._websocket = mock_websocket
        ws_client._receive_task = mock_receive_task
        ws_client._ping_task = mock_ping_task
        ws_client._state = ConnectionState.READY
        
        await ws_client.disconnect()
        
        # Verify cleanup
        mock_receive_task.cancel.assert_called_once()
        mock_ping_task.cancel.assert_called_once()
        mock_websocket.close.assert_called_once()
        assert ws_client.get_state() == ConnectionState.DISCONNECTED
        assert ws_client._websocket is None
    
    @pytest.mark.asyncio
    async def test_send_audio(self, ws_client):
        """Test sending audio data."""
        mock_websocket = AsyncMock()
        ws_client._websocket = mock_websocket
        ws_client._state = ConnectionState.READY
        
        audio_data = b"fake_audio_data"
        await ws_client.send_audio(audio_data)
        
        mock_websocket.send.assert_called_once_with(audio_data)
        assert ws_client._messages_sent == 1
    
    @pytest.mark.asyncio
    async def test_send_audio_not_ready(self, ws_client):
        """Test sending audio when not ready."""
        ws_client._state = ConnectionState.DISCONNECTED
        
        with pytest.raises(WebSocketError, match="Cannot send audio"):
            await ws_client.send_audio(b"data")
    
    @pytest.mark.asyncio
    async def test_send_end_signal(self, ws_client):
        """Test sending end signal."""
        mock_websocket = AsyncMock()
        ws_client._websocket = mock_websocket
        ws_client._state = ConnectionState.READY
        
        with patch.object(ws_client.protocol, 'create_end_message') as mock_end:
            mock_end.return_value = '{"is_speaking": false}'
            
            await ws_client.send_end_signal()
            
            mock_websocket.send.assert_called_once()
            assert ws_client._messages_sent == 1
    
    @pytest.mark.asyncio
    async def test_handle_message_recognition_result(self, ws_client):
        """Test handling recognition result message."""
        result_callback = Mock()
        ws_client.set_result_callback(result_callback)
        
        # Mock message parsing
        with patch.object(ws_client.protocol, 'parse_message') as mock_parse:
            mock_parse.return_value = {"message_type": "result", "text": "test"}
            
            with patch.object(ws_client.protocol, 'is_error_message') as mock_is_error:
                mock_is_error.return_value = False
                
                with patch.object(ws_client.protocol, 'extract_recognition_result') as mock_extract:
                    mock_result = RecognitionResult(text="test result", confidence=0.9)
                    mock_extract.return_value = mock_result
                    
                    await ws_client._handle_message('{"text": "test"}')
                    
                    result_callback.assert_called_once_with(mock_result)
    
    @pytest.mark.asyncio
    async def test_handle_message_error(self, ws_client):
        """Test handling error message."""
        error_callback = Mock()
        ws_client.set_error_callback(error_callback)
        
        with patch.object(ws_client.protocol, 'parse_message') as mock_parse:
            mock_parse.return_value = {"message_type": "error"}
            
            with patch.object(ws_client.protocol, 'is_error_message') as mock_is_error:
                mock_is_error.return_value = True
                
                with patch.object(ws_client.protocol, 'get_error_info') as mock_error_info:
                    mock_error_info.return_value = ("500", "Server error")
                    
                    await ws_client._handle_message('{"error": "test"}')
                    
                    error_callback.assert_called_once_with("500", "Server error")
    
    @pytest.mark.asyncio
    async def test_receive_loop_normal_closure(self, ws_client):
        """Test receive loop with normal connection closure."""
        mock_websocket = AsyncMock()
        
        # Mock async iteration that raises ConnectionClosedOK
        async def mock_async_iter():
            yield '{"text": "test message"}'
            raise ConnectionClosedOK(None, None)
        
        mock_websocket.__aiter__ = mock_async_iter
        ws_client._websocket = mock_websocket
        
        with patch.object(ws_client, '_handle_message') as mock_handle:
            await ws_client._receive_loop()
            
            # Should handle message and then close normally
            mock_handle.assert_called_once()
            assert ws_client.get_state() == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_receive_loop_unexpected_closure(self, ws_client):
        """Test receive loop with unexpected connection closure."""
        mock_websocket = AsyncMock()
        
        # Mock async iteration that raises ConnectionClosedError
        async def mock_async_iter():
            raise ConnectionClosedError(None, None)
        
        mock_websocket.__aiter__ = mock_async_iter
        ws_client._websocket = mock_websocket
        ws_client._max_reconnect_attempts = 1
        
        with patch.object(ws_client, '_reconnect') as mock_reconnect:
            await ws_client._receive_loop()
            
            assert ws_client.get_state() == ConnectionState.DISCONNECTED
            # Should attempt reconnection for unexpected closure
    
    @pytest.mark.asyncio
    async def test_connection_monitor_successful_ping(self, ws_client):
        """Test connection monitoring with successful ping."""
        mock_websocket = AsyncMock()
        mock_pong_waiter = AsyncMock()
        
        ws_client._websocket = mock_websocket
        ws_client._state = ConnectionState.READY
        mock_websocket.closed = False
        mock_websocket.ping.return_value = mock_pong_waiter
        
        # Mock one iteration of monitoring
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, Exception("Stop")]  # Stop after first iteration
            
            with pytest.raises(Exception, match="Stop"):
                await ws_client._connection_monitor()
            
            # Should have called ping
            mock_websocket.ping.assert_called_once()
            
            # Connection quality should remain good
            assert ws_client._connection_quality > 0.5
    
    @pytest.mark.asyncio
    async def test_connection_monitor_ping_timeout(self, ws_client):
        """Test connection monitoring with ping timeout."""
        mock_websocket = AsyncMock()
        mock_pong_waiter = AsyncMock()
        
        ws_client._websocket = mock_websocket
        ws_client._state = ConnectionState.READY
        mock_websocket.closed = False
        mock_websocket.ping.return_value = mock_pong_waiter
        
        # Mock ping timeout
        with patch('asyncio.wait_for') as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()
            
            with patch('asyncio.sleep') as mock_sleep:
                mock_sleep.side_effect = [None, Exception("Stop")]
                
                with pytest.raises(Exception, match="Stop"):
                    await ws_client._connection_monitor()
                
                # Connection quality should degrade
                assert ws_client._ping_failures > 0
    
    @pytest.mark.asyncio
    async def test_reconnect_with_backoff(self, ws_client):
        """Test reconnection with exponential backoff."""
        ws_client._max_reconnect_attempts = 2
        ws_client._reconnect_interval = 0.1  # Short for testing
        
        with patch('asyncio.sleep') as mock_sleep:
            with patch.object(ws_client, 'connect') as mock_connect:
                mock_connect.side_effect = WebSocketError("Connection failed")
                
                await ws_client._reconnect()
                
                # Should have slept for backoff
                mock_sleep.assert_called()
                
                # Should have attempted connection
                mock_connect.assert_called_once()
                
                # Should increment attempts
                assert ws_client._reconnect_attempts == 1
    
    @pytest.mark.asyncio
    async def test_reconnect_max_attempts_exceeded(self, ws_client):
        """Test reconnection when max attempts exceeded."""
        ws_client._reconnect_attempts = ws_client._max_reconnect_attempts
        
        await ws_client._reconnect()
        
        assert ws_client.get_state() == ConnectionState.ERROR
    
    @pytest.mark.asyncio
    async def test_reconnect_success(self, ws_client):
        """Test successful reconnection."""
        ws_client._reconnect_attempts = 0
        
        with patch('asyncio.sleep'):
            with patch.object(ws_client, 'connect') as mock_connect:
                with patch.object(ws_client, '_cleanup_connection_state') as mock_cleanup:
                    await ws_client._reconnect()
                    
                    mock_cleanup.assert_called_once()
                    mock_connect.assert_called_once()
                    assert ws_client._reconnect_attempts == 1
    
    def test_should_retry_reconnection(self, ws_client):
        """Test reconnection retry logic."""
        # Should retry for network errors
        assert ws_client._should_retry_reconnection(WebSocketError("Network error"))
        assert ws_client._should_retry_reconnection(WebSocketError("Connection failed"))
        
        # Should not retry for auth errors
        assert not ws_client._should_retry_reconnection(WebSocketError("Invalid WebSocket connection"))
        assert not ws_client._should_retry_reconnection(WebSocketError("Server rejected connection"))
        assert not ws_client._should_retry_reconnection(WebSocketError("Authentication failed"))
    
    @pytest.mark.asyncio
    async def test_cleanup_connection_state(self, ws_client):
        """Test connection state cleanup."""
        mock_receive_task = AsyncMock()
        mock_ping_task = AsyncMock()
        mock_websocket = AsyncMock()
        
        ws_client._receive_task = mock_receive_task
        ws_client._ping_task = mock_ping_task
        ws_client._websocket = mock_websocket
        ws_client._ping_failures = 5
        
        await ws_client._cleanup_connection_state()
        
        # Tasks should be cancelled
        mock_receive_task.cancel.assert_called_once()
        mock_ping_task.cancel.assert_called_once()
        
        # WebSocket should be closed
        mock_websocket.close.assert_called_once()
        
        # State should be reset
        assert ws_client._websocket is None
        assert ws_client._receive_task is None
        assert ws_client._ping_task is None
        assert ws_client._ping_failures == 0
    
    def test_connection_stats(self, ws_client):
        """Test connection statistics."""
        ws_client._messages_sent = 10
        ws_client._messages_received = 15
        ws_client._reconnect_attempts = 2
        ws_client._connection_quality = 0.8
        ws_client._ping_failures = 1
        
        stats = ws_client.get_connection_stats()
        
        assert stats["state"] == ConnectionState.DISCONNECTED.value
        assert stats["connected"] is False
        assert stats["messages_sent"] == 10
        assert stats["messages_received"] == 15
        assert stats["reconnect_attempts"] == 2
        assert stats["connection_quality"] == 0.8
        assert stats["ping_failures"] == 1
        assert stats["server_url"] == "ws://localhost:10095"
    
    def test_connection_health_assessment(self, ws_client):
        """Test connection health assessment."""
        # Test good health
        ws_client._state = ConnectionState.READY
        ws_client._connection_quality = 0.9
        
        health = ws_client.get_connection_health()
        assert health["status"] == "good"
        assert health["quality_score"] == 0.9
        
        # Test poor health
        ws_client._connection_quality = 0.2
        ws_client._ping_failures = 3
        
        health = ws_client.get_connection_health()
        assert health["status"] == "poor"
        assert len(health["issues"]) > 0
        assert len(health["recommendations"]) > 0
    
    def test_config_validation(self, ws_client):
        """Test connection configuration validation."""
        # Valid config should pass
        errors = ws_client.validate_connection_config()
        assert len(errors) == 0
        
        # Invalid host
        ws_client.config.server.host = ""
        errors = ws_client.validate_connection_config()
        assert any("host is required" in error for error in errors)
        
        # Invalid port
        ws_client.config.server.host = "localhost"
        ws_client.config.server.port = 70000
        errors = ws_client.validate_connection_config()
        assert any("Invalid server port" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_test_connection(self, ws_client):
        """Test connection testing functionality."""
        mock_websocket = AsyncMock()
        
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.return_value.__aenter__ = AsyncMock(return_value=mock_websocket)
            mock_connect.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await ws_client.test_connection()
            
            assert result is True
            mock_websocket.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, ws_client):
        """Test connection testing with failure."""
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = await ws_client.test_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self, ws_client):
        """Test async context manager functionality."""
        with patch.object(ws_client, 'connect') as mock_connect:
            with patch.object(ws_client, 'disconnect') as mock_disconnect:
                async with ws_client:
                    pass
                
                mock_connect.assert_called_once()
                mock_disconnect.assert_called_once()
    
    def test_reset_connection_stats(self, ws_client):
        """Test resetting connection statistics."""
        # Set some stats
        ws_client._messages_sent = 10
        ws_client._messages_received = 15
        ws_client._reconnect_attempts = 2
        ws_client._ping_failures = 3
        ws_client._connection_quality = 0.5
        ws_client._error_history.append({"test": "error"})
        
        # Reset stats
        ws_client.reset_connection_stats()
        
        # Verify reset
        assert ws_client._messages_sent == 0
        assert ws_client._messages_received == 0
        assert ws_client._reconnect_attempts == 0
        assert ws_client._ping_failures == 0
        assert ws_client._connection_quality == 1.0
        assert len(ws_client._error_history) == 0


# Integration tests
@pytest.mark.integration
class TestWebSocketClientIntegration:
    """Integration tests for WebSocket client."""
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, default_nextalk_config):
        """Test complete connection lifecycle with mocked WebSocket."""
        client = FunASRWebSocketClient(default_nextalk_config)
        
        # Mock WebSocket server
        mock_websocket = AsyncMock()
        
        # Mock message sequence
        messages = [
            '{"text": "Hello", "is_final": false}',
            '{"text": "Hello world", "is_final": true, "confidence": 0.95}'
        ]
        
        async def message_generator():
            for msg in messages:
                yield msg
        
        mock_websocket.__aiter__ = message_generator
        
        results = []
        def result_callback(result):
            results.append(result)
        
        client.set_result_callback(result_callback)
        
        with patch('nextalk.network.ws_client.websockets.connect') as mock_connect:
            mock_connect.return_value = mock_websocket
            
            # Test connection and message handling
            await client.connect()
            assert client.is_connected()
            
            # Let receive loop process messages
            receive_task = asyncio.create_task(client._receive_loop())
            await asyncio.sleep(0.1)  # Allow processing
            receive_task.cancel()
            
            # Should have received results
            assert len(results) >= 1
            
            # Test disconnection
            await client.disconnect()
            assert client.get_state() == ConnectionState.DISCONNECTED