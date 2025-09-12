"""
Main controller for NexTalk application.

Coordinates all modules and manages the application lifecycle.
"""

import logging
import asyncio
import threading
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Set
import time
from dataclasses import dataclass, field
from datetime import datetime
import traceback

from ..config.manager import ConfigManager
from ..config.models import NexTalkConfig
from ..audio.capture import AudioCaptureManager, AudioChunk as AudioData
from ..network.ws_client import FunASRWebSocketClient as WebSocketClient
from ..network.protocol import RecognitionResult
from ..input.hotkey import HotkeyManager
from ..output.text_injector import TextInjector
from ..ui.tray import SystemTrayManager, TrayStatus
from .session import RecognitionSession, SessionState


logger = logging.getLogger(__name__)


class ControllerState(Enum):
    """Main controller states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"
    RECOVERING = "recovering"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


class ControllerEvent(Enum):
    """Controller events."""
    INITIALIZE = "initialize"
    START = "start"
    STOP = "stop"
    ACTIVATE_RECOGNITION = "activate_recognition"
    DEACTIVATE_RECOGNITION = "deactivate_recognition"
    ERROR_OCCURRED = "error_occurred"
    RECOVER = "recover"
    SHUTDOWN = "shutdown"
    MODULE_READY = "module_ready"
    MODULE_FAILED = "module_failed"
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_LOST = "connection_lost"


@dataclass
class StateTransition:
    """Represents a state transition."""
    from_state: ControllerState
    to_state: ControllerState
    event: ControllerEvent
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None


class StateManager:
    """Manages controller state transitions and validation."""
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        ControllerState.UNINITIALIZED: {
            ControllerEvent.INITIALIZE: ControllerState.INITIALIZING
        },
        ControllerState.INITIALIZING: {
            ControllerEvent.MODULE_READY: ControllerState.READY,
            ControllerEvent.MODULE_FAILED: ControllerState.ERROR,
            ControllerEvent.ERROR_OCCURRED: ControllerState.ERROR
        },
        ControllerState.READY: {
            ControllerEvent.START: ControllerState.READY,
            ControllerEvent.ACTIVATE_RECOGNITION: ControllerState.ACTIVE,
            ControllerEvent.ERROR_OCCURRED: ControllerState.ERROR,
            ControllerEvent.SHUTDOWN: ControllerState.SHUTTING_DOWN
        },
        ControllerState.ACTIVE: {
            ControllerEvent.DEACTIVATE_RECOGNITION: ControllerState.READY,
            ControllerEvent.ERROR_OCCURRED: ControllerState.ERROR,
            ControllerEvent.CONNECTION_LOST: ControllerState.RECOVERING,
            ControllerEvent.SHUTDOWN: ControllerState.SHUTTING_DOWN
        },
        ControllerState.ERROR: {
            ControllerEvent.RECOVER: ControllerState.RECOVERING,
            ControllerEvent.SHUTDOWN: ControllerState.SHUTTING_DOWN
        },
        ControllerState.RECOVERING: {
            ControllerEvent.MODULE_READY: ControllerState.READY,
            ControllerEvent.ERROR_OCCURRED: ControllerState.ERROR,
            ControllerEvent.SHUTDOWN: ControllerState.SHUTTING_DOWN
        },
        ControllerState.SHUTTING_DOWN: {
            ControllerEvent.SHUTDOWN: ControllerState.SHUTDOWN
        },
        ControllerState.SHUTDOWN: {}
    }
    
    def __init__(self):
        """Initialize state manager."""
        self.current_state = ControllerState.UNINITIALIZED
        self.transition_history: List[StateTransition] = []
        self.state_listeners: Dict[ControllerState, List[Callable]] = {}
        self.event_listeners: Dict[ControllerEvent, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def can_transition(self, event: ControllerEvent) -> bool:
        """
        Check if transition is valid for given event.
        
        Args:
            event: Event to trigger
            
        Returns:
            True if transition is valid
        """
        transitions = self.VALID_TRANSITIONS.get(self.current_state, {})
        return event in transitions
    
    def transition(self, event: ControllerEvent, data: Optional[Dict[str, Any]] = None) -> Optional[ControllerState]:
        """
        Execute state transition.
        
        Args:
            event: Event triggering transition
            data: Optional event data
            
        Returns:
            New state if transition successful, None otherwise
        """
        with self._lock:
            if not self.can_transition(event):
                logger.warning(f"Invalid transition: {self.current_state} -> {event}")
                return None
            
            from_state = self.current_state
            to_state = self.VALID_TRANSITIONS[from_state][event]
            
            # Record transition
            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                event=event,
                data=data
            )
            self.transition_history.append(transition)
            
            # Update state
            self.current_state = to_state
            
            # Notify listeners
            self._notify_state_listeners(from_state, to_state, event, data)
            self._notify_event_listeners(event, from_state, to_state, data)
            
            try:
                logger.info(f"State transition: {from_state.value} -> {to_state.value} (event: {event.value})")
            except ValueError:
                # Logger may be closed during shutdown
                pass
            return to_state
    
    def register_state_listener(self, state: ControllerState, callback: Callable) -> None:
        """Register listener for state entry."""
        if state not in self.state_listeners:
            self.state_listeners[state] = []
        self.state_listeners[state].append(callback)
    
    def register_event_listener(self, event: ControllerEvent, callback: Callable) -> None:
        """Register listener for event."""
        if event not in self.event_listeners:
            self.event_listeners[event] = []
        self.event_listeners[event].append(callback)
    
    def _notify_state_listeners(self, from_state: ControllerState, to_state: ControllerState, 
                                event: ControllerEvent, data: Optional[Dict[str, Any]]) -> None:
        """Notify state listeners."""
        for callback in self.state_listeners.get(to_state, []):
            try:
                callback(from_state, to_state, event, data)
            except Exception as e:
                try:
                    logger.error(f"Error in state listener: {e}")
                except ValueError:
                    # Logger may be closed during shutdown
                    pass
    
    def _notify_event_listeners(self, event: ControllerEvent, from_state: ControllerState,
                               to_state: ControllerState, data: Optional[Dict[str, Any]]) -> None:
        """Notify event listeners."""
        for callback in self.event_listeners.get(event, []):
            try:
                callback(event, from_state, to_state, data)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    def get_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get transition history."""
        if limit:
            return self.transition_history[-limit:]
        return self.transition_history.copy()
    
    def get_state(self) -> ControllerState:
        """Get current state."""
        return self.current_state


class MainController:
    """
    Main controller that coordinates all NexTalk modules.
    
    Manages the application lifecycle and module interactions.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the main controller.
        
        Args:
            config_path: Path to configuration file
        """
        # State management
        self.state_manager = StateManager()
        self._setup_state_listeners()
        
        # Configuration
        self.config_manager = ConfigManager(config_path)
        self.config: Optional[NexTalkConfig] = None
        
        # Modules
        self.audio_manager: Optional[AudioCaptureManager] = None
        self.ws_client: Optional[WebSocketClient] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.text_injector: Optional[TextInjector] = None
        self.tray_manager: Optional[Any] = None  # Can be SystemTrayManager or GTK4TrayManager
        
        # Session management
        self.current_session: Optional[RecognitionSession] = None
        self.session_history: List[RecognitionSession] = []
        
        # Hotkey debouncing - increased to prevent rapid toggle during long press
        self._last_hotkey_time = 0.0
        self._hotkey_debounce_time = 2.0  # 2000ms debounce to prevent rapid toggling
        
        # Threading and async
        self._main_thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        
        # Statistics
        self.stats = {
            "sessions_total": 0,
            "sessions_successful": 0,
            "sessions_failed": 0,
            "total_audio_time": 0.0,
            "total_text_length": 0,
            "start_time": 0.0
        }
        
        # Error recovery
        self._recovery_attempts = 0
        self._max_recovery_attempts = 3
        self._recovery_task: Optional[asyncio.Task] = None
        
        # Continuous mode state
        self._continuous_mode_paused = False
        
        # Toggle mode state: track if user manually stopped recording
        self._user_stopped_recording = False
        
        logger.info("MainController initialized")
    
    def _setup_state_listeners(self) -> None:
        """Setup state transition listeners."""
        # Register state entry listeners
        self.state_manager.register_state_listener(
            ControllerState.ERROR,
            self._on_error_state
        )
        self.state_manager.register_state_listener(
            ControllerState.RECOVERING,
            self._on_recovering_state
        )
        self.state_manager.register_state_listener(
            ControllerState.READY,
            self._on_ready_state
        )
        
        # Register event listeners
        self.state_manager.register_event_listener(
            ControllerEvent.CONNECTION_LOST,
            self._on_connection_lost
        )
        self.state_manager.register_event_listener(
            ControllerEvent.ERROR_OCCURRED,
            self._on_error_occurred
        )
    
    async def initialize(self) -> bool:
        """
        Initialize all modules.
        
        Returns:
            True if initialization successful
        """
        try:
            self.state_manager.transition(ControllerEvent.INITIALIZE)
            
            # Load configuration
            logger.info("Loading configuration...")
            self.config = self.config_manager.load_config()
            
            # Validate configuration
            errors = self.config.validate()
            if errors:
                logger.error(f"Configuration errors: {errors}")
                return False
            
            # Initialize modules
            logger.info("Initializing modules...")
            
            # Audio capture
            self.audio_manager = AudioCaptureManager(self.config.audio)
            
            # WebSocket client
            self.ws_client = WebSocketClient(self.config)
            self.ws_client.on_message = self._handle_ws_message
            self.ws_client.on_error = self._handle_ws_error
            self.ws_client.set_result_callback(self._handle_recognition_result)
            
            # Hotkey manager  
            self.hotkey_manager = HotkeyManager(self.config.recording)
            
            # Choose recording mode based on configuration
            if self.config.recording.mode == "hold":
                self.hotkey_manager.register_press_release(
                    self.config.recording.hotkey,
                    on_press=self._handle_hotkey_press,
                    on_release=self._handle_hotkey_release,
                    description="Press to Start / Release to Stop Recording"
                )
                logger.info("Using hold recording mode")
            else:
                # Default to toggle mode  
                self.hotkey_manager.register(
                    self.config.recording.hotkey,
                    self._handle_hotkey_trigger,
                    "Start/Stop Recognition"
                )
                logger.info(f"Using {self.config.recording.mode} recording mode")
            
            # Text injector - 使用Portal/xdotool现代注入系统
            try:
                self.text_injector = TextInjector(self.config.text_injection)
                # Modern TextInjector需要异步初始化，在_run_async中完成
                logger.info("TextInjector创建成功，将在异步环境中初始化现代文本注入器")
            except Exception as e:
                logger.error(f"TextInjector创建失败: {e}")
                raise
            
            # System tray
            if self.config.ui.show_tray_icon:
                self._initialize_tray_manager()
                if self.tray_manager:
                    self.tray_manager.set_on_quit(self.shutdown)
                    self.tray_manager.set_on_toggle(self._toggle_recognition)
                    self.tray_manager.set_on_settings(self._open_settings)
            
            self.state_manager.transition(ControllerEvent.MODULE_READY)
            logger.info("All modules initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.state_manager.transition(ControllerEvent.MODULE_FAILED, {"error": str(e)})
            return False
    
    def start(self) -> None:
        """Start the main controller."""
        if self.state_manager.get_state() != ControllerState.READY:
            logger.error(f"Cannot start in state: {self.state_manager.get_state()}")
            return
        
        self._running = True
        self.stats["start_time"] = time.time()
        
        # Start modules
        logger.info("Starting modules...")
        
        # Start hotkey listener
        self.hotkey_manager.start()
        
        # Start system tray
        if self.tray_manager:
            self.tray_manager.start()
        
        # Connect to WebSocket server
        self._main_thread = threading.Thread(target=self._run_async, daemon=True)
        self._main_thread.start()
        
        # Auto start recognition based on recording mode
        if self.config.recording.mode in ["once", "continuous"]:
            # Wait a moment for WebSocket connection
            threading.Timer(2.0, self._auto_start_recognition).start()
        
        logger.info("MainController started")
    
    def _run_async(self) -> None:
        """Run async event loop in thread."""
        try:
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            
            # Initialize modern text injector asynchronously
            self._event_loop.run_until_complete(self._initialize_text_injector())
            
            # Connect to WebSocket
            self._event_loop.run_until_complete(self._connect_websocket())
            
            # Run event loop
            while self._running:
                self._event_loop.run_until_complete(asyncio.sleep(0.1))
                
        except Exception as e:
            logger.error(f"Async loop error: {e}")
        finally:
            # Cleanup text injector
            if self.text_injector:
                self._event_loop.run_until_complete(self.text_injector.cleanup())
            self._event_loop.close()
    
    async def _initialize_text_injector(self) -> None:
        """Initialize modern text injector asynchronously."""
        try:
            if self.text_injector:
                injector_initialized = await self.text_injector.initialize()
                if injector_initialized:
                    logger.info("Modern text injector initialized successfully")
                else:
                    logger.warning("Modern text injector initialization failed")
                    if self.tray_manager:
                        self.tray_manager.show_notification(
                            "文本注入警告",
                            "Portal/xdotool文本注入初始化失败，语音输入可能不可用"
                        )
        except Exception as e:
            logger.error(f"Text injector initialization error: {e}")
            if self.tray_manager:
                self.tray_manager.show_notification(
                    "文本注入错误",
                    f"现代文本注入器初始化异常: {str(e)[:50]}"
                )
    
    async def _inject_text_async(self, text: str) -> None:
        """
        Inject text asynchronously using modern injection methods.
        
        Args:
            text: Text to inject
        """
        try:
            logger.info(f"DEBUG: _inject_text_async被调用, 文本: '{text}'")
            if self.text_injector and self.current_session:
                injection_start = time.time()
                
                # Get injection status before injection
                health_status = await self.text_injector.get_health_status()
                method_used = health_status.get('active_method', 'unknown')
                injector_ready = health_status.get('ready', False)
                logger.info(f"DEBUG: 注入器状态 - method_used: {method_used}, injector_ready: {injector_ready}")
                
                # Update session with injector status  
                self.current_session.update_injection_status(injector_ready, method_used)
                
                # Perform injection
                logger.info(f"DEBUG: 开始执行文本注入...")
                success = await self.text_injector.inject_text(text)
                injection_time = time.time() - injection_start
                logger.info(f"DEBUG: 文本注入完成, 成功: {success}, 耗时: {injection_time:.3f}s")
                
                # Complete injection with method details
                self.current_session.complete_injection(success, method_used, injection_time)
                
                if success:
                    logger.info(f"Successfully injected text via {method_used}: {text[:50]}...")
                    # Update statistics
                    self.stats["total_text_length"] += len(text)
                else:
                    logger.error(f"Failed to inject text via {method_used}: {text[:50]}...")
                    
        except Exception as e:
            logger.error(f"Text injection error: {e}")
            if self.current_session:
                self.current_session.complete_injection(False, "error", 0.0)
    
    async def _connect_websocket(self) -> None:
        """Connect to WebSocket server."""
        try:
            await self.ws_client.connect()
            logger.info("Connected to WebSocket server")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            if self.tray_manager:
                self.tray_manager.show_notification(
                    "连接失败",
                    "无法连接到语音识别服务器"
                )
    
    def _auto_start_recognition(self) -> None:
        """Auto start recognition for auto_start and continuous modes."""
        if not self.ws_client or not self.ws_client.is_connected():
            logger.warning("WebSocket not connected, delaying auto start")
            # Retry after a delay
            threading.Timer(2.0, self._auto_start_recognition).start()
            return
        
        recording_mode = self.config.recording.mode
        if recording_mode in ["once", "continuous"]:
            logger.info(f"Auto starting recognition in {recording_mode} mode")
            self._start_recognition()
            
            if self.tray_manager:
                mode_text = "启动时录音一次" if recording_mode == "once" else "持续采集模式"
                self.tray_manager.show_notification(
                    "自动音频采集",
                    f"{mode_text} - 音频采集已开始"
                )
    
    def shutdown(self) -> None:
        """Shutdown the controller and all modules."""
        if self.state_manager.get_state() == ControllerState.SHUTDOWN:
            return
        
        logger.info("Shutting down MainController...")
        self.state_manager.transition(ControllerEvent.SHUTDOWN)
        
        self._running = False
        
        # Stop current session if active
        if self.current_session and self.current_session.is_active():
            try:
                self.current_session.cancel()
            except Exception as e:
                logger.error(f"Error cancelling session: {e}")
        
        # Stop modules with error handling
        if self.audio_manager:
            try:
                self.audio_manager.stop_recording()
            except Exception as e:
                logger.error(f"Error stopping audio manager: {e}")
        
        if self.ws_client and self._event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.ws_client.disconnect(),
                    self._event_loop
                )
            except Exception as e:
                logger.error(f"Error disconnecting WebSocket: {e}")
        
        if self.hotkey_manager:
            try:
                self.hotkey_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping hotkey manager: {e}")
        
        if self.tray_manager:
            try:
                self.tray_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping tray manager: {e}")
        
        # Clean up text injector
        if self.text_injector and hasattr(self.text_injector, 'cleanup'):
            try:
                self.text_injector.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up text injector: {e}")
        
        # Wait for threads with timeout
        if self._main_thread and self._main_thread.is_alive():
            logger.debug("Waiting for main thread to finish...")
            self._main_thread.join(timeout=2.0)
            if self._main_thread.is_alive():
                logger.warning("Main thread did not finish cleanly")
        
        self.state_manager.transition(ControllerEvent.SHUTDOWN)
        logger.info("MainController shutdown complete")
    
    def _handle_hotkey_press(self) -> None:
        """Handle hotkey press event - start recording."""        
        # Only start if not already active
        if not (self.current_session and self.current_session.is_active()):
            logger.info("Hotkey pressed - starting recording")
            self._start_recognition_direct()
        else:
            logger.debug("Hotkey pressed but recording already active, ignoring")
    
    def _handle_hotkey_release(self) -> None:
        """Handle hotkey release event - stop recording."""        
        # Only stop if currently active
        if self.current_session and self.current_session.is_active():
            logger.debug("Hotkey released - stopping recording")
            self._stop_recognition()
        else:
            logger.debug("Hotkey released but recording not active, ignoring")
    
    def _handle_hotkey_trigger(self) -> None:
        """Handle hotkey trigger event with debouncing (legacy toggle mode)."""
        import time
        current_time = time.time()
        
        # Debounce: ignore if triggered too quickly
        time_since_last = current_time - self._last_hotkey_time
        if time_since_last < self._hotkey_debounce_time:
            logger.info(f"Hotkey ignored (debounce): {time_since_last:.3f}s since last trigger (min: {self._hotkey_debounce_time}s)")
            return
        
        self._last_hotkey_time = current_time
        logger.info(f"Hotkey triggered (last trigger: {time_since_last:.3f}s ago)")
        self._toggle_recognition()
    
    def _toggle_recognition(self) -> None:
        """Toggle voice recognition on/off."""
        recording_mode = self.config.recording.mode
        
        # Check if we're actually recording (not just session active)
        is_recording = self.audio_manager and self.audio_manager.is_recording()
        controller_active = self.state_manager.get_state() == ControllerState.ACTIVE
        
        # For toggle mode, use both recording state and controller state
        should_stop = False
        if recording_mode == "toggle":
            should_stop = is_recording or controller_active
        else:
            # For other modes, use session state
            should_stop = self.current_session and self.current_session.is_active()
        
        if should_stop:
            logger.info(f"Stopping recognition (mode: {recording_mode}, recording: {is_recording}, controller: {controller_active})")
            # In continuous mode, mark as paused by user
            if recording_mode == "continuous":
                self._continuous_mode_paused = True
                if self.tray_manager:
                    self.tray_manager.show_notification(
                        "持续采集已暂停",
                        "再次按热键恢复采集"
                    )
            self._stop_recognition()
        else:
            # Clear any old session data before starting new one
            if self.current_session:
                self.current_session.clear_audio_buffer()
            logger.info(f"Starting recognition (mode: {recording_mode}, recording: {is_recording}, controller: {controller_active})")
            # In continuous mode, resume from pause
            if recording_mode == "continuous" and self._continuous_mode_paused:
                self._continuous_mode_paused = False
                if self.tray_manager:
                    self.tray_manager.show_notification(
                        "持续采集已恢复",
                        "音频采集继续运行"
                    )
            self._start_recognition()
    
    def _start_recognition_direct(self) -> None:
        """Start a new recognition session directly (for press-and-hold mode)."""
        if self.state_manager.get_state() != ControllerState.READY:
            logger.warning(f"Cannot start recognition in state: {self.state_manager.get_state()}")
            return
        
        if self.current_session and self.current_session.is_active():
            logger.warning("Recognition already active")
            return
        
        logger.info("Starting recognition session (direct)")
        
        # Clear user stop flag when starting new recording
        self._user_stopped_recording = False
        
        # Create new session
        self.current_session = RecognitionSession()
        self.current_session.set_on_state_change(self._handle_session_state)
        self.current_session.set_on_text_recognized(self._handle_text_recognized)
        self.current_session.set_on_error(self._handle_session_error)
        self.current_session.set_on_complete(self._handle_session_complete)
        
        # Start session
        self.current_session.start()
        
        # Initialize WebSocket streaming session asynchronously (non-blocking)
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws_client.initialize_streaming_session(),
                self._event_loop
            )
            logger.info("WebSocket streaming session initialization started")
        except Exception as e:
            logger.warning(f"Failed to start streaming session initialization: {e}")
            logger.info("Will retry initialization when first audio data arrives")
        
        # Start PyAudio recording with real-time streaming immediately
        self.audio_manager.set_data_callback(self._stream_audio_chunk)
        self.audio_manager.start_recording()
        
        # Update UI
        self.state_manager.transition(ControllerEvent.ACTIVATE_RECOGNITION)
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.ACTIVE)
            self.tray_manager.show_notification("语音识别", "开始识别...")
    
    def _start_recognition(self) -> None:
        """Start a new recognition session."""
        if self.state_manager.get_state() != ControllerState.READY:
            logger.warning(f"Cannot start recognition in state: {self.state_manager.get_state()}")
            return
        
        if self.current_session and self.current_session.is_active():
            logger.warning("Recognition already active")
            return
        
        logger.info("Starting recognition session")
        
        # Clear user stop flag when starting new recording
        self._user_stopped_recording = False
        
        # Create new session
        self.current_session = RecognitionSession()
        self.current_session.set_on_state_change(self._handle_session_state)
        self.current_session.set_on_text_recognized(self._handle_text_recognized)
        self.current_session.set_on_error(self._handle_session_error)
        self.current_session.set_on_complete(self._handle_session_complete)
        
        # Start session
        self.current_session.start()
        
        # Initialize WebSocket streaming session asynchronously (non-blocking)
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws_client.initialize_streaming_session(),
                self._event_loop
            )
            logger.info("WebSocket streaming session initialization started")
        except Exception as e:
            logger.warning(f"Failed to start streaming session initialization: {e}")
            logger.info("Will retry initialization when first audio data arrives")
        
        # Start PyAudio recording with real-time streaming immediately
        self.audio_manager.set_data_callback(self._stream_audio_chunk)
        self.audio_manager.start_recording()
        
        # Update UI
        self.state_manager.transition(ControllerEvent.ACTIVATE_RECOGNITION)
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.ACTIVE)
            self.tray_manager.show_notification("语音识别", "开始识别...")
    
    def _stop_recognition(self) -> None:
        """Stop the current recognition session."""
        # Check if we have recording or active session to stop
        has_recording = self.audio_manager and self.audio_manager.is_recording()
        has_active_session = self.current_session and self.current_session.is_active()
        
        if not has_recording and not has_active_session:
            logger.warning("No active recording or session to stop")
            return
        
        logger.info("Stopping recognition session")
        
        # Stop PyAudio recording and get accumulated data
        if has_recording:
            audio_data = self.audio_manager.stop_recording()
        
        # Stop session if it exists and is active
        if has_active_session:
            self.current_session.stop()
        
        # In toggle mode, immediately clear session when user stops recording
        if self.config.recording.mode == "toggle":
            logger.info("Toggle mode: User stopped recording, clearing session immediately")
            # Mark that user manually stopped recording
            self._user_stopped_recording = True
            
            # Store the current session in history and clear it
            if self.current_session:
                self.session_history.append(self.current_session)
                if len(self.session_history) > 100:
                    self.session_history.pop(0)
                self.current_session = None
                logger.info("Toggle mode: Session cleared, ready for next recording")
        
        # Send end signal to WebSocket (for streaming mode)
        if self.ws_client and self.ws_client.is_connected():
            logger.info("Sending end signal to WebSocket")
            asyncio.run_coroutine_threadsafe(
                self.ws_client.send_end_signal(),
                self._event_loop
            )
        else:
            logger.warning("WebSocket not connected, cannot send end signal")
        
        # Update UI - only transition if we're in ACTIVE state
        current_state = self.state_manager.get_state()
        if current_state == ControllerState.ACTIVE:
            self.state_manager.transition(ControllerEvent.DEACTIVATE_RECOGNITION)
        elif current_state == ControllerState.READY:
            logger.debug("Already in READY state, no state transition needed")
        else:
            logger.warning(f"Unexpected state during stop recognition: {current_state}")
        
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.IDLE)
    
    def _handle_audio_data(self, audio_data: AudioData) -> None:
        """
        Handle captured audio data from PyAudio.
        
        Args:
            audio_data: AudioChunk object containing raw PCM data
        """
        if self.current_session and self.current_session.is_active():
            # AudioChunk.data is already raw PCM bytes from PyAudio (paInt16 format)
            # This matches exactly what funasr_wss_client.py sends
            self.current_session.add_audio_data(audio_data.data)
    
    def _stream_audio_chunk(self, audio_data: AudioData) -> None:
        """
        Stream audio chunk to WebSocket immediately (real-time like original client).
        
        Args:
            audio_data: AudioChunk object containing raw PCM data
        """
        # In hold mode, if no current session, create a new one automatically
        if (not self.current_session or not self.current_session.is_active()) and \
           self.config.recording.mode == "hold" and \
           self.state_manager.get_state() == ControllerState.ACTIVE:
            logger.info("Hold mode: Auto-creating new session for continued recording")
            self.current_session = RecognitionSession()
            self.current_session.set_on_state_change(self._handle_session_state)
            self.current_session.set_on_text_recognized(self._handle_text_recognized)
            self.current_session.set_on_error(self._handle_session_error)
            self.current_session.set_on_complete(self._handle_session_complete)
            self.current_session.start()
        
        if self.current_session and self.current_session.is_active():
            # Add to session for record keeping
            self.current_session.add_audio_data(audio_data.data)
            
            # Stream immediately to WebSocket (real-time like original client)
            if self.ws_client and self.ws_client.is_connected():
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.ws_client.send_audio_chunk(audio_data.data),
                        self._event_loop
                    )
                    logger.debug(f"Streamed audio chunk: {len(audio_data.data)} bytes")
                except Exception as e:
                    logger.error(f"Failed to stream audio chunk: {e}")
            else:
                logger.warning("WebSocket not connected, cannot stream audio chunk")
    
    def _handle_recognition_result(self, result: RecognitionResult) -> None:
        """
        Handle recognition result from WebSocket client.
        
        Args:
            result: Recognition result from FunASR server
        """
        logger.info(f"Recognition result received: '{result.text}' (confidence: {result.confidence}, final: {result.is_final}, mode: {result.mode})")
        
        # If no current session, ignore the result (user may have stopped recording)
        if not self.current_session:
            logger.info("No current session, ignoring recognition result")
            return
        
        if result.text.strip():
            # For 2pass mode, prioritize 2pass-offline results (complete results)
            # For other modes, use is_final flag
            should_process = False
            
            if result.mode == "2pass-offline":
                # 2pass-offline contains the complete, best result
                # Process it even if is_final is False (which can happen after stop)
                logger.info(f"Processing 2pass-offline result: '{result.text}'")
                should_process = True
                
                # In toggle mode, log the result processing
                if self.config.recording.mode == "toggle":
                    logger.info(f"Received 2pass-offline result in toggle mode: '{result.text}'")
            elif result.mode in ["offline", "online"] and result.is_final:
                # Standard offline/online modes use is_final flag
                should_process = True
                logger.info(f"Processing {result.mode} final result: '{result.text}'")
            elif result.mode == "2pass-online" and result.is_final:
                # 2pass-online partial results - only use if no offline result comes
                # Store as backup but don't process immediately
                logger.debug(f"Received 2pass-online partial result: '{result.text}'")
            
            if should_process:
                self.current_session.process_recognition(result.text.strip())
    
    def _handle_ws_message(self, message: dict) -> None:
        """
        Handle WebSocket message from server.
        
        Args:
            message: Message dictionary
        """
        msg_type = message.get("type")
        
        if msg_type == "recognition_result":
            text = message.get("text", "")
            if self.current_session:
                self.current_session.process_recognition(text)
        
        elif msg_type == "error":
            error = message.get("error", "Unknown error")
            if self.current_session:
                self.current_session.report_error(error)
    
    def _handle_ws_error(self, error: str) -> None:
        """
        Handle WebSocket error.
        
        Args:
            error: Error message
        """
        logger.error(f"WebSocket error: {error}")
        if self.current_session:
            self.current_session.report_error(f"网络错误: {error}")
    
    def _handle_session_state(self, state: SessionState) -> None:
        """
        Handle session state change.
        
        Args:
            state: New session state
        """
        logger.debug(f"Session state changed to: {state.value}")
        
        if state == SessionState.INJECTING and self.current_session:
            logger.info(f"DEBUG: 准备注入文本，状态检查通过")
            # Inject recognized text asynchronously
            text = self.current_session.recognized_text
            logger.info(f"DEBUG: 获取到文本: '{text}', text_injector存在: {self.text_injector is not None}")
            if text and self.text_injector:
                logger.info(f"DEBUG: 开始创建异步注入任务")
                # Schedule async text injection
                asyncio.create_task(self._inject_text_async(text))
            else:
                logger.warning(f"DEBUG: 注入条件不满足 - text: '{text}', text_injector: {self.text_injector is not None}")
    
    def _handle_text_recognized(self, text: str) -> None:
        """
        Handle recognized text.
        
        Args:
            text: Recognized text
        """
        logger.info(f"Text recognized: {text}")
        
        # NOTE: Text injection is now handled in _handle_session_state 
        # to avoid duplicate injection. This method only shows notifications.
        
        if self.tray_manager:
            self.tray_manager.show_notification(
                "识别完成",
                f"识别结果: {text[:100]}..."
            )
    
    def _handle_session_error(self, error: str) -> None:
        """
        Handle session error.
        
        Args:
            error: Error message
        """
        logger.error(f"Session error: {error}")
        
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.ERROR)
            self.tray_manager.show_notification("识别错误", error)
        
        # Trigger error event
        self.state_manager.transition(ControllerEvent.ERROR_OCCURRED, {"error": error})
        if self.tray_manager:
            # Reset tray icon after delay
            threading.Timer(
                3.0,
                lambda: self.tray_manager.update_status(TrayStatus.IDLE)
            ).start()
    
    def _handle_session_complete(self, metrics: Any) -> None:
        """
        Handle session completion.
        
        Args:
            metrics: Session metrics
        """
        # Update statistics
        self.stats["sessions_total"] += 1
        if metrics.injected_successfully:
            self.stats["sessions_successful"] += 1
        else:
            self.stats["sessions_failed"] += 1
        
        self.stats["total_audio_time"] += metrics.audio_duration
        self.stats["total_text_length"] += len(metrics.recognized_text)
        
        # Add to history
        if self.current_session:
            self.session_history.append(self.current_session)
            # Keep only last 100 sessions
            if len(self.session_history) > 100:
                self.session_history.pop(0)
        
        logger.info(f"Session complete: {metrics.session_id}")
        
        # In toggle mode, if recording is still active, create new session for continued recording
        if self.config.recording.mode == "toggle":
            # Only continue recording if user hasn't stopped recording and controller is still active
            if not self._user_stopped_recording and self.state_manager.get_state() == ControllerState.ACTIVE:
                logger.info("Toggle mode: Text injected, creating new session and continuing recording")
                # Create a new session for continued recording in toggle mode
                if self.current_session:
                    # Store the completed session in history
                    self.session_history.append(self.current_session)
                    if len(self.session_history) > 100:
                        self.session_history.pop(0)
                
                # Create new session for continued recording
                self.current_session = RecognitionSession()
                self.current_session.set_on_state_change(self._handle_session_state)
                self.current_session.set_on_text_recognized(self._handle_text_recognized)
                self.current_session.set_on_error(self._handle_session_error)
                self.current_session.set_on_complete(self._handle_session_complete)
                self.current_session.start()
                
                # Keep controller state as ACTIVE in toggle mode to maintain recording
                logger.info("Toggle mode: New session created, maintaining ACTIVE state for continued recording")
                return
            else:
                logger.info("Toggle mode: User stopped recording or controller not active, not creating new session")
        
        # In hold mode, text is injected and we create a fresh session for next recognition
        # but keep recording active until user releases the key
        if self.config.recording.mode == "hold":
            logger.info("Hold mode: Text injected, creating fresh session but keeping recording active until key release")
            # Store completed session in history
            if self.current_session:
                self.session_history.append(self.current_session)
                if len(self.session_history) > 100:
                    self.session_history.pop(0)
            
            # Create fresh session for next recognition, but don't auto-start it yet
            # It will be started when audio comes in (if recording is still active)
            self.current_session = None
            
            # Keep controller state as ACTIVE to maintain recording
            logger.info("Hold mode: Session cleared, recording continues until key release")
            return
        
        # Transition state back to READY after natural session completion
        current_state = self.state_manager.get_state()
        if current_state == ControllerState.ACTIVE:
            self.state_manager.transition(ControllerEvent.DEACTIVATE_RECOGNITION)
            logger.debug("State transitioned from ACTIVE to READY after session completion")
        
        # Auto restart for continuous mode
        recording_mode = self.config.recording.mode
        current_state = self.state_manager.get_state()
        
        logger.debug(f"Auto-restart check: mode={recording_mode}, running={self._running}, state={current_state.value}, paused={self._continuous_mode_paused}")
        
        if (recording_mode == "continuous" and 
            self._running and 
            current_state == ControllerState.READY and
            not self._continuous_mode_paused):
            logger.info("Continuous mode: auto restarting recognition")
            # Small delay before restarting to avoid rapid cycling
            threading.Timer(1.0, self._start_recognition).start()
        elif recording_mode == "continuous":
            # Log why auto-restart didn't happen
            reasons = []
            if not self._running:
                reasons.append("not running")
            if current_state != ControllerState.READY:
                reasons.append(f"state is {current_state.value}")
            if self._continuous_mode_paused:
                reasons.append("mode paused")
            logger.debug(f"Continuous mode auto-restart skipped: {', '.join(reasons)}")
    
    def _open_settings(self) -> None:
        """Open settings window."""
        logger.info("Opening settings (not implemented)")
        if self.tray_manager:
            self.tray_manager.show_notification(
                "设置",
                "设置界面尚未实现"
            )
    
    def _on_error_state(self, from_state: ControllerState, to_state: ControllerState,
                        event: ControllerEvent, data: Optional[Dict[str, Any]]) -> None:
        """Handle entry to error state."""
        logger.error(f"Entered error state from {from_state.value}")
        
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.ERROR)
            error_msg = data.get("error", "Unknown error") if data else "Unknown error"
            self.tray_manager.show_notification("系统错误", error_msg)
        
        # Schedule recovery attempt
        if self._recovery_attempts < self._max_recovery_attempts:
            threading.Timer(5.0, self._attempt_recovery).start()
    
    def _on_recovering_state(self, from_state: ControllerState, to_state: ControllerState,
                            event: ControllerEvent, data: Optional[Dict[str, Any]]) -> None:
        """Handle entry to recovering state."""
        try:
            logger.info(f"Attempting recovery (attempt {self._recovery_attempts + 1}/{self._max_recovery_attempts})")
        except ValueError:
            # Logger may be closed during shutdown, skip logging
            pass
        
        if self.tray_manager:
            self.tray_manager.show_notification("系统恢复", "正在尝试恢复连接...")
        
        # Start async recovery
        if self._event_loop:
            self._recovery_task = asyncio.run_coroutine_threadsafe(
                self._async_recovery(),
                self._event_loop
            )
    
    def _on_ready_state(self, from_state: ControllerState, to_state: ControllerState,
                       event: ControllerEvent, data: Optional[Dict[str, Any]]) -> None:
        """Handle entry to ready state."""
        logger.info("System ready")
        
        # Reset recovery attempts on successful recovery
        if from_state == ControllerState.RECOVERING:
            self._recovery_attempts = 0
            if self.tray_manager:
                self.tray_manager.show_notification("系统恢复", "已成功恢复")
        
        if self.tray_manager:
            self.tray_manager.update_status(TrayStatus.IDLE)
    
    def _on_connection_lost(self, event: ControllerEvent, from_state: ControllerState,
                           to_state: ControllerState, data: Optional[Dict[str, Any]]) -> None:
        """Handle connection lost event."""
        logger.warning("Connection lost to server")
        
        if self.tray_manager:
            self.tray_manager.show_notification("连接断开", "与服务器的连接已断开")
    
    def _on_error_occurred(self, event: ControllerEvent, from_state: ControllerState,
                          to_state: ControllerState, data: Optional[Dict[str, Any]]) -> None:
        """Handle error occurred event."""
        error_msg = data.get("error", "Unknown error") if data else "Unknown error"
        logger.error(f"Error occurred: {error_msg}")
    
    def _initialize_tray_manager(self) -> None:
        """Initialize the system tray manager."""
        try:
            self.tray_manager = SystemTrayManager(self.config.ui)
            logger.info("System tray manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize system tray manager: {e}")
            self.tray_manager = None
    
    def _attempt_recovery(self) -> None:
        """Attempt to recover from error state."""
        if self.state_manager.get_state() != ControllerState.ERROR:
            return
        
        self._recovery_attempts += 1
        self.state_manager.transition(ControllerEvent.RECOVER)
    
    async def _async_recovery(self) -> None:
        """Async recovery process."""
        try:
            # Try to reconnect WebSocket
            if self.ws_client:
                await self.ws_client.disconnect()
                await asyncio.sleep(1)
                await self.ws_client.connect()
            
            # Recovery successful
            self.state_manager.transition(ControllerEvent.MODULE_READY)
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.state_manager.transition(ControllerEvent.ERROR_OCCURRED, {"error": str(e)})
    
    async def toggle_recording(self) -> None:
        """
        Toggle recording state (async version for signal handling).
        
        This method provides an async interface to the toggle functionality
        for use with signal handlers and external control.
        """
        try:
            current_state = self.state_manager.get_state()
            if current_state in [ControllerState.READY, ControllerState.ACTIVE]:
                logger.info("External toggle request received")
                self._toggle_recognition()
            else:
                logger.warning(f"Cannot toggle recording in current state: {current_state}")
        except Exception as e:
            logger.error(f"Error in toggle_recording: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get application statistics.
        
        Returns:
            Statistics dictionary
        """
        uptime = time.time() - self.stats["start_time"] if self.stats["start_time"] > 0 else 0
        
        return {
            **self.stats,
            "uptime": uptime,
            "state": self.state_manager.get_state().value,
            "active_session": self.current_session.session_id if self.current_session else None,
            "session_history_count": len(self.session_history)
        }
    
    def is_running(self) -> bool:
        """Check if controller is running."""
        current_state = self.state_manager.get_state()
        return self._running and current_state not in [
            ControllerState.UNINITIALIZED,
            ControllerState.SHUTTING_DOWN,
            ControllerState.SHUTDOWN
        ]