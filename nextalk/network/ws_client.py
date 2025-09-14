"""
FunASR WebSocket client implementation for NexTalk.

Provides async WebSocket client with reconnection, error handling, and protocol support.
Based on funasr_wss_client.py with enhancements for NexTalk integration.
"""

import asyncio
import json
import logging
import ssl
import time
import websockets
from enum import Enum
from typing import Optional, Callable, Dict, Any, List, Union
try:
    # Try modern websockets import first
    from websockets import ConnectionClosedError, ConnectionClosedOK
    from websockets.exceptions import WebSocketException, InvalidURI, InvalidHandshake
    # Use generic exception for HTTP status codes instead of deprecated InvalidStatusCode
    WebSocketStatusError = WebSocketException
except ImportError:
    # Fallback for older versions
    from websockets.exceptions import (
        WebSocketException, 
        ConnectionClosedError, 
        ConnectionClosedOK,
        InvalidURI,
        InvalidHandshake
    )
    WebSocketStatusError = WebSocketException

from ..config.models import NexTalkConfig
from .protocol import FunASRProtocol, RecognitionResult, MessageType


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    DEGRADED = "degraded"  # Connected but experiencing issues


class WebSocketError(Exception):
    """WebSocket-related errors."""
    pass


class FunASRWebSocketClient:
    """
    Async WebSocket client for FunASR speech recognition service.
    
    Features:
    - Automatic reconnection with exponential backoff
    - SSL/TLS support
    - Protocol message handling
    - Connection state management
    - Callback-based result handling
    """
    
    def __init__(self, config: NexTalkConfig):
        """
        Initialize WebSocket client.
        
        Args:
            config: NexTalk configuration containing server and protocol settings
        """
        self.config = config
        self.protocol = FunASRProtocol(config)
        
        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connection_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._session_initialized = False  # Track if current session is initialized
        
        # Reconnection management
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = config.server.reconnect_attempts
        self._reconnect_interval = config.server.reconnect_interval
        self._last_connection_time = 0.0
        self._reconnect_task: Optional[asyncio.Task] = None
        
        # Connection monitoring
        self._ping_task: Optional[asyncio.Task] = None
        self._last_ping_time = 0.0
        self._ping_failures = 0
        self._max_ping_failures = 3
        self._connection_quality = 1.0  # 0.0 to 1.0
        
        # Error tracking
        self._error_history: List[Dict[str, Any]] = []
        self._max_error_history = 50
        
        # Callbacks
        self._result_callback: Optional[Callable[[RecognitionResult], None]] = None
        self._error_callback: Optional[Callable[[str, str], None]] = None
        self._status_callback: Optional[Callable[[ConnectionState], None]] = None
        
        # SSL context
        self._ssl_context = self._create_ssl_context()
        
        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        self._connection_start_time: Optional[float] = None
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context if SSL is enabled."""
        if not self.config.server.use_ssl:
            return None
        
        context = ssl.create_default_context()
        
        if not self.config.server.ssl_verify:
            # Disable certificate verification for local servers
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            logger.warning("SSL certificate verification disabled")
        
        return context
    
    def set_result_callback(self, callback: Callable[[RecognitionResult], None]) -> None:
        """Set callback for recognition results."""
        self._result_callback = callback
    
    def set_error_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for errors (error_code, error_message)."""
        self._error_callback = callback
    
    def set_status_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """Set callback for connection status changes."""
        self._status_callback = callback
    
    def _set_state(self, state: ConnectionState, error_info: Optional[str] = None) -> None:
        """Update connection state and notify callback."""
        if self._state != state:
            logger.debug(f"Connection state: {self._state.value} -> {state.value}")
            
            # Log state transitions with context
            if state == ConnectionState.ERROR and error_info:
                self._record_error("state_transition", error_info)
            
            self._state = state
            
            if self._status_callback:
                try:
                    self._status_callback(state)
                except Exception as e:
                    logger.error(f"Error in status callback: {e}")
    
    def _record_error(self, error_type: str, error_message: str, exception: Optional[Exception] = None) -> None:
        """Record error for analysis and monitoring."""
        error_record = {
            "timestamp": time.time(),
            "type": error_type,
            "message": error_message,
            "exception_type": type(exception).__name__ if exception else None,
            "reconnect_attempts": self._reconnect_attempts,
            "connection_quality": self._connection_quality
        }
        
        self._error_history.append(error_record)
        
        # Limit history size
        if len(self._error_history) > self._max_error_history:
            self._error_history.pop(0)
        
        logger.error(f"WebSocket error [{error_type}]: {error_message}")
    
    def _update_connection_quality(self, success: bool) -> None:
        """Update connection quality based on operation success."""
        if success:
            # Improve quality slowly
            self._connection_quality = min(1.0, self._connection_quality + 0.1)
            self._ping_failures = 0
        else:
            # Degrade quality faster
            self._connection_quality = max(0.0, self._connection_quality - 0.2)
            self._ping_failures += 1
        
        # Set degraded state if quality is poor
        if self._connection_quality < 0.5 and self._state == ConnectionState.READY:
            self._set_state(ConnectionState.DEGRADED)
    
    def _get_websocket_url(self) -> str:
        """Build WebSocket URL from configuration."""
        scheme = "wss" if self.config.server.use_ssl else "ws"
        return f"{scheme}://{self.config.server.host}:{self.config.server.port}"
    
    async def connect(self) -> None:
        """
        Connect to FunASR WebSocket server.
        
        Raises:
            WebSocketError: If connection fails
        """
        if self._state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING, ConnectionState.READY]:
            logger.warning("Already connected or connecting")
            return
        
        # Cancel any ongoing reconnection
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        
        self._set_state(ConnectionState.CONNECTING)
        self._session_initialized = False  # Reset session initialization on new connection
        
        try:
            url = self._get_websocket_url()
            logger.info(f"Connecting to FunASR server: {url}")
            
            # Connection parameters exactly matching funasr_wss_client.py
            connect_kwargs = {
                'ssl': self._ssl_context,
                'ping_interval': None,  # Disable ping (matches original client)
                'subprotocols': ['binary'],  # FunASR requires binary subprotocol
            }
            
            self._websocket = await asyncio.wait_for(
                websockets.connect(url, **connect_kwargs),
                timeout=self.config.server.timeout
            )
            
            # Set to CONNECTED, initialization will happen in send methods
            self._set_state(ConnectionState.CONNECTED)
            self._connection_start_time = time.time()
            self._last_connection_time = time.time()
            self._reconnect_attempts = 0
            self._connection_quality = 1.0
            self._ping_failures = 0
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            # Disable ping monitoring to match original client behavior
            # self._ping_task = asyncio.create_task(self._connection_monitor())
            
            logger.info("Successfully connected to FunASR server")
            
        except asyncio.TimeoutError as e:
            error_msg = f"Connection timeout after {self.config.server.timeout}s"
            self._set_state(ConnectionState.ERROR, error_msg)
            self._record_error("connection_timeout", error_msg, e)
            raise WebSocketError(error_msg)
        
        except (InvalidURI, InvalidHandshake) as e:
            error_msg = f"Invalid WebSocket connection: {e}"
            self._set_state(ConnectionState.ERROR, error_msg)
            self._record_error("connection_invalid", error_msg, e)
            raise WebSocketError(error_msg)
        
        except WebSocketStatusError as e:
            error_msg = f"Server rejected connection with status {e.status_code}"
            self._set_state(ConnectionState.ERROR, error_msg)
            self._record_error("connection_rejected", error_msg, e)
            raise WebSocketError(error_msg)
        
        except OSError as e:
            error_msg = f"Network error: {e}"
            self._set_state(ConnectionState.ERROR, error_msg)
            self._record_error("network_error", error_msg, e)
            # Network errors are often temporary, attempt reconnection
            if self._max_reconnect_attempts > 0:
                asyncio.create_task(self._reconnect())
            raise WebSocketError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected connection error: {e}"
            self._set_state(ConnectionState.ERROR, error_msg)
            self._record_error("connection_unexpected", error_msg, e)
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise WebSocketError(error_msg)
    
    async def _send_init_message(self, wav_name: str = "microphone", audio_fs: int = None, wav_format: str = None) -> None:
        """Send initialization message to server."""
        try:
            self._set_state(ConnectionState.AUTHENTICATING)
            
            init_message = self.protocol.create_init_message(wav_name, audio_fs, wav_format)
            await self._websocket.send(init_message)
            self._messages_sent += 1
            
            self._set_state(ConnectionState.READY)
            logger.debug("Initialization message sent")
            
        except Exception as e:
            logger.error(f"Failed to send initialization message: {e}")
            raise WebSocketError(f"Initialization failed: {e}")
    
    async def _connection_monitor(self) -> None:
        """Monitor connection health with periodic pings."""
        # Wait a bit before starting monitoring to let initial connection stabilize
        await asyncio.sleep(5)
        
        while self._state in [ConnectionState.READY, ConnectionState.CONNECTED, ConnectionState.DEGRADED]:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self._websocket and hasattr(self._websocket, 'state') and self._websocket.state.name == 'OPEN':
                    # Send ping to test connection
                    ping_start = time.time()
                    pong_waiter = await self._websocket.ping()
                    
                    try:
                        await asyncio.wait_for(pong_waiter, timeout=10)
                        ping_time = time.time() - ping_start
                        
                        # Update connection quality based on ping time
                        if ping_time < 0.1:  # Very good
                            self._update_connection_quality(True)
                        elif ping_time < 0.5:  # Good
                            self._update_connection_quality(True)
                        else:  # Poor but working
                            self._update_connection_quality(False)
                        
                        self._last_ping_time = time.time()
                        logger.debug(f"Ping successful: {ping_time:.3f}s")
                        
                    except asyncio.TimeoutError:
                        self._update_connection_quality(False)
                        logger.warning("Ping timeout - connection may be unstable")
                        
                        if self._ping_failures >= self._max_ping_failures:
                            self._record_error("ping_failures", f"Max ping failures reached: {self._ping_failures}")
                            await self._handle_connection_failure()
                
            except Exception as e:
                self._record_error("monitor_error", f"Connection monitor error: {e}", e)
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _handle_connection_failure(self) -> None:
        """Handle connection failure with appropriate recovery action."""
        logger.warning("Connection failure detected, attempting recovery")
        
        # Close current connection
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None
        
        self._set_state(ConnectionState.DISCONNECTED, "Connection failure detected")
        
        # Attempt reconnection if enabled
        if self._max_reconnect_attempts > 0 and self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_task = asyncio.create_task(self._reconnect())
        else:
            self._set_state(ConnectionState.ERROR, "Max reconnection attempts exceeded")
    
    async def _receive_loop(self) -> None:
        """Main message receiving loop with enhanced error handling."""
        logger.debug("Starting receive loop")
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            logger.debug("Waiting for messages from WebSocket...")
            # Use while loop with recv() like the original client
            while self._websocket and self._state in [ConnectionState.CONNECTED, ConnectionState.READY, ConnectionState.AUTHENTICATING]:
                try:
                    # Simple recv() like original client
                    message = await self._websocket.recv()
                    logger.debug(f"Received raw message: {message[:100] if isinstance(message, (str, bytes)) else message}")
                    
                    await self._handle_message(message)
                    self._messages_received += 1
                    self._update_connection_quality(True)
                    consecutive_errors = 0  # Reset error count on success
                    
                except asyncio.TimeoutError:
                    # Just continue waiting
                    continue
                    
                except websockets.exceptions.ConnectionClosed as e:
                    logger.info("WebSocket connection closed")
                    # 检查是否是正常关闭，如果是则重新抛出以被外层处理
                    if isinstance(e, ConnectionClosedOK):
                        raise  # 让外层的 ConnectionClosedOK 处理器设置状态
                    elif isinstance(e, ConnectionClosedError):  
                        raise  # 让外层的 ConnectionClosedError 处理器设置状态
                    else:
                        # 通用的连接关闭，设置为断开状态
                        self._set_state(ConnectionState.DISCONNECTED)
                    break
                    
                except Exception as e:
                    consecutive_errors += 1
                    self._record_error("message_handling", f"Error in receive loop: {e}", e)
                    logger.warning(f"Message handling error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                    
                    # 特别处理Mock对象错误，立即终止以避免无限循环
                    error_str = str(e)
                    error_type = str(type(e))
                    if ("AsyncMock" in error_str or "Mock" in error_str or 
                        "AsyncMock" in error_type or "Mock" in error_type):
                        logger.error(f"Mock object detected in receive loop - TERMINATING IMMEDIATELY: {e}")
                        self._set_state(ConnectionState.DISCONNECTED, f"Mock object error: {e}")
                        return  # 立即返回，不是break
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive message errors ({consecutive_errors}) - terminating receive loop")
                        break
                    
                    # 在连续错误时添加短暂延迟，避免CPU占用过高
                    await asyncio.sleep(0.01 * consecutive_errors)
                    
        except ConnectionClosedOK:
            logger.info("WebSocket connection closed normally")
            self._set_state(ConnectionState.DISCONNECTED)
            
        except ConnectionClosedError as e:
            error_msg = f"WebSocket connection closed unexpectedly: {e.code} - {e.reason}"
            logger.warning(error_msg)
            self._set_state(ConnectionState.DISCONNECTED, error_msg)
            self._record_error("connection_closed", error_msg, e)
            
            # Reset session initialization when connection closes unexpectedly
            self._session_initialized = False
            logger.debug("Session initialization reset due to connection closure")
            
            # Different reconnection strategies based on close code
            if e.code in [1000, 1001]:  # Normal closure or going away
                # Don't auto-reconnect for normal closure
                return
            elif e.code in [1006, 1011, 1014]:  # Abnormal closure, try to reconnect
                if self._max_reconnect_attempts > 0:
                    self._reconnect_task = asyncio.create_task(self._reconnect())
            
        except WebSocketException as e:
            error_msg = f"WebSocket protocol error: {e}"
            self._record_error("protocol_error", error_msg, e)
            self._set_state(ConnectionState.ERROR, error_msg)
            
            # Protocol errors may be recoverable
            if self._max_reconnect_attempts > 0:
                self._reconnect_task = asyncio.create_task(self._reconnect())
                
        except Exception as e:
            error_msg = f"Unexpected error in receive loop: {e}"
            self._record_error("receive_loop_error", error_msg, e)
            self._set_state(ConnectionState.ERROR, error_msg)
            logger.error(error_msg)
    
    async def _handle_message(self, message: Union[str, bytes]) -> None:
        """Handle incoming message from server."""
        try:
            # 检查消息类型，避免处理无效的mock对象
            if not isinstance(message, (str, bytes)):
                logger.error(f"Invalid message type received: {type(message)}. Expected str or bytes.")
                raise ValueError(f"Invalid message type: {type(message)}")
            
            logger.info(f"Received raw message: {message[:200]}...")
            
            # Parse message using protocol
            message_data = self.protocol.parse_message(message)
            logger.debug(f"Parsed message data: {message_data}")
            
            # Handle different message types
            if self.protocol.is_error_message(message_data):
                error_code, error_message = self.protocol.get_error_info(message_data)
                logger.error(f"Server error [{error_code}]: {error_message}")
                
                if self._error_callback:
                    self._error_callback(error_code, error_message)
            
            else:
                # Try to extract recognition result
                result = self.protocol.extract_recognition_result(message_data)
                
                if result and result.text.strip():  # Only process non-empty results
                    logger.info(f"Calling result callback with: {result}")
                    if self._result_callback:
                        self._result_callback(result)
                    else:
                        logger.warning(f"Recognition result but no callback: {result}")
                elif result:
                    logger.debug(f"Empty recognition result (normal for streaming): {result}")
                else:
                    logger.debug(f"Non-result message: {message_data}")
        
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
    
    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to server in chunks (streaming mode).
        
        Args:
            audio_data: PCM audio data bytes
            
        Raises:
            WebSocketError: If not connected or send fails
        """
        if self._state not in [ConnectionState.CONNECTED, ConnectionState.READY]:
            raise WebSocketError(f"Cannot send audio in state: {self._state.value}")
        
        if not self._websocket:
            raise WebSocketError("WebSocket not connected")
        
        # Send initialization if needed
        if not self._session_initialized:
            self._set_state(ConnectionState.AUTHENTICATING)
            logger.info("Sending microphone mode init message")
            # Use microphone mode to match original client 
            init_message = self.protocol.create_init_message("microphone")
            await self._websocket.send(init_message)
            self._messages_sent += 1
            self._session_initialized = True
            self._set_state(ConnectionState.READY)
            logger.debug("Microphone mode initialization completed")
        
        try:
            # CRITICAL: Simulate real-time streaming exactly like original client (line 122-128)
            # Original client sends each PyAudio chunk immediately with 5ms delay
            logger.info(f"Simulating real-time streaming: {len(audio_data)} bytes")
            
            # Calculate chunk size exactly matching original PyAudio client (funasr_wss_client.py line 75-76)
            # chunk_size = 60 * args.chunk_size[1] / args.chunk_interval
            # CHUNK = int(RATE / 1000 * chunk_size)
            chunk_size_ms = 60 * self.config.audio.chunk_size[1] / self.config.audio.chunk_interval
            chunk_frames = int(16000 / 1000 * chunk_size_ms)  # 16000 Hz sample rate
            pyaudio_chunk_size = chunk_frames * 2  # 2 bytes per frame (16-bit PCM)
            logger.debug(f"Dynamic chunk calculation: {chunk_size_ms}ms -> {chunk_frames} frames -> {pyaudio_chunk_size} bytes")
            chunk_count = (len(audio_data) + pyaudio_chunk_size - 1) // pyaudio_chunk_size
            
            logger.info(f"Streaming audio in real-time chunks: {chunk_count} chunks of {pyaudio_chunk_size} bytes")
            
            # Stream each chunk immediately (exactly matching original line 122-128)
            for i in range(chunk_count):
                start_idx = i * pyaudio_chunk_size
                end_idx = min(start_idx + pyaudio_chunk_size, len(audio_data))
                chunk = audio_data[start_idx:end_idx]
                
                # Send raw audio chunk immediately (matches: await websocket.send(message))
                await self._websocket.send(chunk)
                self._messages_sent += 1
                logger.debug(f"Streamed chunk {i+1}/{chunk_count} ({len(chunk)} bytes)")
                
                # CRITICAL: 5ms delay exactly matching original client (line 127)
                # await asyncio.sleep(0.005)
                await asyncio.sleep(0.005)
            
            # Send end signal after streaming complete (matches original end-of-stream logic)
            end_message = json.dumps({"is_speaking": False}, ensure_ascii=False)
            await self._websocket.send(end_message)
            self._messages_sent += 1
            logger.info(f"Streaming complete: sent {chunk_count} chunks, {len(audio_data)} bytes total")
            
            # Session will be reset for next audio transmission (matches original client pattern)
            # Each audio send gets fresh initialization like original client's per-connection model
            
            # For streaming mode, minimal wait since we're simulating real-time
            # Original client doesn't have explicit wait after streaming, just continues receiving
            logger.debug("Streaming complete, waiting for recognition results...")
            
            if self.config.recognition.mode == "offline":
                # Offline mode needs time to process the complete audio
                await asyncio.sleep(2.0)
            else:
                # 2pass and online modes process incrementally during streaming
                # Just a brief wait for final processing
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to send audio data: {e}")
            raise WebSocketError(f"Audio send failed: {e}")
    
    async def send_audio_file(self, audio_data: bytes, wav_name: str = "demo", audio_fs: int = 16000, wav_format: str = "pcm") -> None:
        """
        Send audio file data to server (file mode) with proper initialization.
        
        This method handles the complete file mode workflow:
        1. Send file mode initialization 
        2. Send audio in chunks matching funasr_wss_client.py exactly
        
        Args:
            audio_data: PCM audio data bytes
            wav_name: Name for this audio file 
            audio_fs: Audio sample rate
            wav_format: Audio format (pcm, wav, etc.)
            
        Raises:
            WebSocketError: If connection or send fails
        """
        if self._state != ConnectionState.CONNECTED:
            raise WebSocketError(f"Cannot send audio in state: {self._state.value}")
        
        if not self._websocket:
            raise WebSocketError("WebSocket not connected")
        
        try:
            # Send file mode initialization message (matches original client exactly)
            self._set_state(ConnectionState.AUTHENTICATING)
            logger.info(f"Sending file mode init message: {wav_name}, {audio_fs}Hz, {wav_format}")
            file_init_message = self.protocol.create_init_message(wav_name, audio_fs, wav_format)
            await self._websocket.send(file_init_message)
            self._messages_sent += 1
            self._set_state(ConnectionState.READY)
            logger.debug("File mode initialization completed")
            
            # Calculate chunk parameters exactly matching funasr_wss_client.py line 191-192
            stride = int(60 * self.config.audio.chunk_size[1] / self.config.audio.chunk_interval / 1000 * audio_fs * 2)
            chunk_num = (len(audio_data) - 1) // stride + 1
            
            logger.info(f"Sending file audio in chunks: total_bytes={len(audio_data)}, stride={stride}, chunk_num={chunk_num}")
            
            # Send audio in chunks exactly matching funasr_wss_client.py
            for i in range(chunk_num):
                beg = i * stride
                chunk = audio_data[beg:beg + stride]
                
                # Send raw audio chunk
                await self._websocket.send(chunk)
                self._messages_sent += 1
                
                # Send end signal after last chunk (matches original client exactly)
                if i == chunk_num - 1:
                    end_message = json.dumps({"is_speaking": False}, ensure_ascii=False)
                    await self._websocket.send(end_message)
                    self._messages_sent += 1
                    logger.info("Sent end signal after last audio chunk")
                
                # Sleep between chunks (exactly matches original client timing - line 228-234)
                # Important: Original client sleeps even after the last chunk!
                sleep_duration = (
                    0.001
                    if self.config.recognition.mode == "offline"
                    else 60 * self.config.audio.chunk_size[1] / self.config.audio.chunk_interval / 1000
                )
                
                await asyncio.sleep(sleep_duration)
                logger.debug(f"Sent audio chunk {i+1}/{chunk_num} ({len(chunk)} bytes)")
            
            logger.info(f"Successfully sent all audio chunks ({chunk_num} chunks, {len(audio_data)} bytes total)")
            
            # Wait additional time after sending audio (matches original client line 236-237)
            if self.config.recognition.mode != "offline":
                await asyncio.sleep(2.0)  # Exactly matches original client timing
            else:
                await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to send audio file: {e}")
            raise WebSocketError(f"Audio file send failed: {e}")
    
    async def initialize_streaming_session(self) -> None:
        """Initialize streaming session (like original client)."""
        if self._state not in [ConnectionState.CONNECTED, ConnectionState.READY]:
            raise WebSocketError(f"Cannot initialize streaming in state: {self._state.value}")
        
        if not self._websocket:
            raise WebSocketError("WebSocket not connected")
        
        try:
            self._set_state(ConnectionState.AUTHENTICATING)
            logger.info("Initializing streaming session")
            
            # Send microphone mode initialization
            init_message = self.protocol.create_init_message("microphone")
            await self._websocket.send(init_message)
            self._messages_sent += 1
            self._session_initialized = True
            
            self._set_state(ConnectionState.READY)
            logger.info("Streaming session initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize streaming session: {e}")
            raise WebSocketError(f"Streaming initialization failed: {e}")
    
    async def send_audio_chunk(self, audio_chunk: bytes) -> None:
        """Send single audio chunk for real-time streaming (like original client)."""
        if self._state != ConnectionState.READY:
            logger.warning(f"Cannot send audio chunk in state: {self._state.value}")
            return
        
        if not self._websocket:
            logger.warning("WebSocket not connected")
            return
        
        try:
            # Send raw audio chunk immediately (matches original client)
            await self._websocket.send(audio_chunk)
            self._messages_sent += 1
            logger.debug(f"Streamed audio chunk: {len(audio_chunk)} bytes")
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}")

    async def send_end_signal(self) -> None:
        """Send end-of-stream signal to server."""
        if self._state != ConnectionState.READY:
            logger.warning(f"Cannot send end signal in state: {self._state.value}")
            return
        
        try:
            end_message = self.protocol.create_end_message()
            await self._websocket.send(end_message)
            self._messages_sent += 1
            
            logger.info("End signal sent")
            
        except Exception as e:
            logger.error(f"Failed to send end signal: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from server and cleanup resources."""
        logger.info("Disconnecting from FunASR server")
        
        # Cancel monitoring task first
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        # Give receive task a chance to process remaining messages
        if self._receive_task and not self._receive_task.done():
            try:
                # Wait briefly for any pending messages
                await asyncio.wait_for(self._receive_task, timeout=1.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # Now cancel if still running
                if not self._receive_task.done():
                    self._receive_task.cancel()
                    try:
                        await self._receive_task
                    except asyncio.CancelledError:
                        pass
        
        # Close WebSocket connection
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self._websocket = None
        
        self._set_state(ConnectionState.DISCONNECTED)
        self._connection_start_time = None
        # Reset session initialization on manual disconnect
        self._session_initialized = False
        
        logger.info("Disconnected from FunASR server")
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect with enhanced exponential backoff and jitter."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            error_msg = f"Max reconnect attempts ({self._max_reconnect_attempts}) exceeded"
            logger.error(error_msg)
            self._set_state(ConnectionState.ERROR, error_msg)
            return
        
        self._reconnect_attempts += 1
        
        # Exponential backoff with jitter to avoid thundering herd
        import random
        base_backoff = self._reconnect_interval * (2 ** (self._reconnect_attempts - 1))
        jitter = random.uniform(0.1, 0.5) * base_backoff
        backoff_time = min(base_backoff + jitter, 300)  # Max 5 minutes
        
        logger.info(f"Reconnecting in {backoff_time:.1f}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
        self._set_state(ConnectionState.RECONNECTING)
        
        await asyncio.sleep(backoff_time)
        
        # Check if we should still reconnect (user might have called disconnect)
        if self._state != ConnectionState.RECONNECTING:
            logger.debug("Reconnection cancelled - state changed during backoff")
            return
        
        try:
            # Clean up any existing connection state
            await self._cleanup_connection_state()
            
            # Attempt connection
            await self.connect()
            logger.info(f"Reconnection successful after {self._reconnect_attempts} attempts")
            
        except WebSocketError as e:
            error_msg = f"Reconnection attempt {self._reconnect_attempts} failed: {e}"
            logger.error(error_msg)
            self._record_error("reconnection_failed", error_msg, e)
            
            # Check if we should continue trying based on error type
            should_retry = self._should_retry_reconnection(e)
            
            if should_retry and self._reconnect_attempts < self._max_reconnect_attempts:
                # Schedule next reconnection attempt
                self._reconnect_task = asyncio.create_task(self._reconnect())
            else:
                self._set_state(ConnectionState.ERROR, f"Reconnection failed: {error_msg}")
                
        except Exception as e:
            error_msg = f"Unexpected error during reconnection: {e}"
            logger.error(error_msg)
            self._record_error("reconnection_unexpected", error_msg, e)
            self._set_state(ConnectionState.ERROR, error_msg)
    
    def _should_retry_reconnection(self, error: WebSocketError) -> bool:
        """Determine if reconnection should be retried based on error type."""
        error_msg = str(error).lower()
        
        # Don't retry for these error types
        non_retryable_errors = [
            "invalid websocket connection",
            "server rejected connection",
            "authentication failed",
            "unauthorized"
        ]
        
        for non_retryable in non_retryable_errors:
            if non_retryable in error_msg:
                logger.info(f"Not retrying reconnection due to non-retryable error: {error}")
                return False
        
        return True
    
    async def _cleanup_connection_state(self) -> None:
        """Clean up connection state before reconnection."""
        # Cancel existing tasks
        for task in [self._receive_task, self._ping_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close existing WebSocket
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            finally:
                self._websocket = None
        
        # Reset state
        self._receive_task = None
        self._ping_task = None
        self._ping_failures = 0
    
    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    def is_connected(self) -> bool:
        """Check if client is connected and ready."""
        return self._state in [ConnectionState.CONNECTED, ConnectionState.READY]
    
    def is_ready(self) -> bool:
        """Check if client is ready for streaming audio."""
        return self._state == ConnectionState.READY
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get comprehensive connection statistics."""
        uptime = 0.0
        if self._connection_start_time:
            uptime = time.time() - self._connection_start_time
        
        last_ping = 0.0
        if self._last_ping_time > 0:
            last_ping = time.time() - self._last_ping_time
        
        return {
            "state": self._state.value,
            "connected": self.is_connected(),
            "uptime": uptime,
            "reconnect_attempts": self._reconnect_attempts,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "server_url": self._get_websocket_url(),
            "ssl_enabled": self.config.server.use_ssl,
            "connection_quality": self._connection_quality,
            "ping_failures": self._ping_failures,
            "last_ping_ago": last_ping,
            "error_count": len(self._error_history),
            "last_connection_time": self._last_connection_time
        }
    
    def get_error_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent error history.
        
        Args:
            limit: Maximum number of recent errors to return
            
        Returns:
            List of error records
        """
        return self._error_history[-limit:] if self._error_history else []
    
    def get_connection_health(self) -> Dict[str, Any]:
        """
        Get connection health assessment.
        
        Returns:
            Health status and recommendations
        """
        health = {
            "status": "unknown",
            "quality_score": self._connection_quality,
            "issues": [],
            "recommendations": []
        }
        
        # Assess overall health
        if self._state == ConnectionState.ERROR:
            health["status"] = "error"
            health["issues"].append("Connection is in error state")
            health["recommendations"].append("Check server availability and network connectivity")
            
        elif self._state == ConnectionState.DISCONNECTED:
            health["status"] = "disconnected"
            health["issues"].append("Not connected to server")
            health["recommendations"].append("Call connect() to establish connection")
            
        elif self._state in [ConnectionState.CONNECTING, ConnectionState.RECONNECTING]:
            health["status"] = "connecting"
            
        elif self._connection_quality < 0.3:
            health["status"] = "poor"
            health["issues"].append("Poor connection quality")
            health["recommendations"].append("Check network stability")
            
        elif self._connection_quality < 0.7:
            health["status"] = "fair"
            health["issues"].append("Moderate connection quality")
            
        else:
            health["status"] = "good"
        
        # Check for specific issues
        if self._ping_failures > 0:
            health["issues"].append(f"Recent ping failures: {self._ping_failures}")
            
        if self._reconnect_attempts > 0:
            health["issues"].append(f"Recent reconnection attempts: {self._reconnect_attempts}")
            
        recent_errors = len([e for e in self._error_history if time.time() - e["timestamp"] < 300])  # 5 minutes
        if recent_errors > 3:
            health["issues"].append(f"High error rate: {recent_errors} errors in 5 minutes")
            health["recommendations"].append("Check server logs and network stability")
        
        return health
    
    def reset_connection_stats(self) -> None:
        """Reset connection statistics (useful for testing)."""
        self._messages_sent = 0
        self._messages_received = 0
        self._reconnect_attempts = 0
        self._ping_failures = 0
        self._connection_quality = 1.0
        self._error_history.clear()
        logger.info("Connection statistics reset")
    
    def validate_connection_config(self) -> List[str]:
        """
        Validate connection configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate server config
        if not self.config.server.host:
            errors.append("Server host is required")
        
        if not (1 <= self.config.server.port <= 65535):
            errors.append(f"Invalid server port: {self.config.server.port}")
        
        if self.config.server.timeout <= 0:
            errors.append("Server timeout must be positive")
        
        if self.config.server.reconnect_attempts < 0:
            errors.append("Reconnect attempts must be non-negative")
        
        # Validate protocol config
        protocol_errors = self.protocol.validate_config()
        errors.extend(protocol_errors)
        
        return errors
    
    async def test_connection(self) -> bool:
        """
        Test connection to server without full initialization.
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            url = self._get_websocket_url()
            
            # Quick connection test
            async with websockets.connect(
                url,
                ssl=self._ssl_context,
                ping_interval=None,  # Disable ping for test
                close_timeout=5
            ) as websocket:
                # Just test if we can connect
                await websocket.ping()
                return True
                
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()