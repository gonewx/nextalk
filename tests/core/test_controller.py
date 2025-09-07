"""
Unit tests for main controller.
"""

import unittest
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
import asyncio
import threading
import time
from typing import Dict, Any

from nextalk.core.controller import (
    MainController,
    ControllerState,
    ControllerEvent,
    StateManager,
    StateTransition
)
from nextalk.core.session import SessionState
from nextalk.config.models import NexTalkConfig
from nextalk.ui.tray import TrayStatus


class TestStateManager(unittest.TestCase):
    """Test StateManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = StateManager()
    
    def test_init(self):
        """Test state manager initialization."""
        self.assertEqual(self.state_manager.current_state, ControllerState.UNINITIALIZED)
        self.assertEqual(len(self.state_manager.transition_history), 0)
        self.assertIsInstance(self.state_manager.state_listeners, dict)
        self.assertIsInstance(self.state_manager.event_listeners, dict)
    
    def test_can_transition_valid(self):
        """Test valid transition check."""
        # From UNINITIALIZED to INITIALIZING
        self.assertTrue(self.state_manager.can_transition(ControllerEvent.INITIALIZE))
        
        # Transition to INITIALIZING
        self.state_manager.current_state = ControllerState.INITIALIZING
        self.assertTrue(self.state_manager.can_transition(ControllerEvent.MODULE_READY))
        self.assertTrue(self.state_manager.can_transition(ControllerEvent.MODULE_FAILED))
    
    def test_can_transition_invalid(self):
        """Test invalid transition check."""
        # Cannot activate recognition from UNINITIALIZED
        self.assertFalse(self.state_manager.can_transition(ControllerEvent.ACTIVATE_RECOGNITION))
        
        # Cannot recover from READY state
        self.state_manager.current_state = ControllerState.READY
        self.assertFalse(self.state_manager.can_transition(ControllerEvent.RECOVER))
    
    def test_transition_valid(self):
        """Test valid state transition."""
        new_state = self.state_manager.transition(ControllerEvent.INITIALIZE)
        
        self.assertEqual(new_state, ControllerState.INITIALIZING)
        self.assertEqual(self.state_manager.current_state, ControllerState.INITIALIZING)
        self.assertEqual(len(self.state_manager.transition_history), 1)
        
        # Check transition record
        transition = self.state_manager.transition_history[0]
        self.assertEqual(transition.from_state, ControllerState.UNINITIALIZED)
        self.assertEqual(transition.to_state, ControllerState.INITIALIZING)
        self.assertEqual(transition.event, ControllerEvent.INITIALIZE)
    
    def test_transition_invalid(self):
        """Test invalid state transition."""
        result = self.state_manager.transition(ControllerEvent.ACTIVATE_RECOGNITION)
        
        self.assertIsNone(result)
        self.assertEqual(self.state_manager.current_state, ControllerState.UNINITIALIZED)
        self.assertEqual(len(self.state_manager.transition_history), 0)
    
    def test_transition_with_data(self):
        """Test transition with event data."""
        data = {"module": "test", "status": "ready"}
        
        self.state_manager.transition(ControllerEvent.INITIALIZE)
        new_state = self.state_manager.transition(ControllerEvent.MODULE_READY, data)
        
        self.assertEqual(new_state, ControllerState.READY)
        
        # Check data in transition history
        transition = self.state_manager.transition_history[-1]
        self.assertEqual(transition.data, data)
    
    def test_register_state_listener(self):
        """Test registering state listener."""
        listener = Mock()
        
        self.state_manager.register_state_listener(ControllerState.READY, listener)
        
        self.assertIn(ControllerState.READY, self.state_manager.state_listeners)
        self.assertIn(listener, self.state_manager.state_listeners[ControllerState.READY])
    
    def test_register_event_listener(self):
        """Test registering event listener."""
        listener = Mock()
        
        self.state_manager.register_event_listener(ControllerEvent.ERROR_OCCURRED, listener)
        
        self.assertIn(ControllerEvent.ERROR_OCCURRED, self.state_manager.event_listeners)
        self.assertIn(listener, self.state_manager.event_listeners[ControllerEvent.ERROR_OCCURRED])
    
    def test_state_listener_notification(self):
        """Test state listener notification."""
        listener = Mock()
        self.state_manager.register_state_listener(ControllerState.INITIALIZING, listener)
        
        # Trigger transition
        self.state_manager.transition(ControllerEvent.INITIALIZE)
        
        # Check listener was called
        listener.assert_called_once()
        args = listener.call_args[0]
        self.assertEqual(args[0], ControllerState.UNINITIALIZED)  # from_state
        self.assertEqual(args[1], ControllerState.INITIALIZING)  # to_state
        self.assertEqual(args[2], ControllerEvent.INITIALIZE)  # event
    
    def test_event_listener_notification(self):
        """Test event listener notification."""
        listener = Mock()
        self.state_manager.register_event_listener(ControllerEvent.INITIALIZE, listener)
        
        # Trigger transition
        self.state_manager.transition(ControllerEvent.INITIALIZE)
        
        # Check listener was called
        listener.assert_called_once()
        args = listener.call_args[0]
        self.assertEqual(args[0], ControllerEvent.INITIALIZE)  # event
        self.assertEqual(args[1], ControllerState.UNINITIALIZED)  # from_state
        self.assertEqual(args[2], ControllerState.INITIALIZING)  # to_state
    
    def test_listener_error_handling(self):
        """Test listener error doesn't break transition."""
        bad_listener = Mock(side_effect=Exception("Listener error"))
        good_listener = Mock()
        
        self.state_manager.register_state_listener(ControllerState.INITIALIZING, bad_listener)
        self.state_manager.register_state_listener(ControllerState.INITIALIZING, good_listener)
        
        # Transition should succeed despite listener error
        new_state = self.state_manager.transition(ControllerEvent.INITIALIZE)
        
        self.assertEqual(new_state, ControllerState.INITIALIZING)
        bad_listener.assert_called_once()
        good_listener.assert_called_once()
    
    def test_get_history(self):
        """Test getting transition history."""
        # Make some transitions
        self.state_manager.transition(ControllerEvent.INITIALIZE)
        self.state_manager.transition(ControllerEvent.MODULE_READY)
        
        history = self.state_manager.get_history()
        self.assertEqual(len(history), 2)
        
        # Test with limit
        limited_history = self.state_manager.get_history(limit=1)
        self.assertEqual(len(limited_history), 1)
        self.assertEqual(limited_history[0].event, ControllerEvent.MODULE_READY)
    
    def test_get_state(self):
        """Test getting current state."""
        self.assertEqual(self.state_manager.get_state(), ControllerState.UNINITIALIZED)
        
        self.state_manager.transition(ControllerEvent.INITIALIZE)
        self.assertEqual(self.state_manager.get_state(), ControllerState.INITIALIZING)
    
    def test_complex_state_flow(self):
        """Test complex state transition flow."""
        # Initialize -> Ready -> Active -> Ready -> Shutdown
        transitions = [
            (ControllerEvent.INITIALIZE, ControllerState.INITIALIZING),
            (ControllerEvent.MODULE_READY, ControllerState.READY),
            (ControllerEvent.ACTIVATE_RECOGNITION, ControllerState.ACTIVE),
            (ControllerEvent.DEACTIVATE_RECOGNITION, ControllerState.READY),
            (ControllerEvent.SHUTDOWN, ControllerState.SHUTTING_DOWN),
            (ControllerEvent.SHUTDOWN, ControllerState.SHUTDOWN)
        ]
        
        for event, expected_state in transitions:
            new_state = self.state_manager.transition(event)
            self.assertEqual(new_state, expected_state)
            self.assertEqual(self.state_manager.current_state, expected_state)
        
        # Check full history
        history = self.state_manager.get_history()
        self.assertEqual(len(history), len(transitions))


class TestMainController(unittest.TestCase):
    """Test MainController class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_path = "/test/config.yaml"
        
        # Patch all dependencies
        self.patches = []
        
        # Patch config manager
        config_patch = patch('nextalk.core.controller.ConfigManager')
        self.mock_config_manager_cls = config_patch.start()
        self.patches.append(config_patch)
        
        # Patch modules
        audio_patch = patch('nextalk.core.controller.AudioCaptureManager')
        self.mock_audio_cls = audio_patch.start()
        self.patches.append(audio_patch)
        
        ws_patch = patch('nextalk.core.controller.WebSocketClient')
        self.mock_ws_cls = ws_patch.start()
        self.patches.append(ws_patch)
        
        hotkey_patch = patch('nextalk.core.controller.HotkeyManager')
        self.mock_hotkey_cls = hotkey_patch.start()
        self.patches.append(hotkey_patch)
        
        injector_patch = patch('nextalk.core.controller.TextInjector')
        self.mock_injector_cls = injector_patch.start()
        self.patches.append(injector_patch)
        
        tray_patch = patch('nextalk.core.controller.SystemTrayManager')
        self.mock_tray_cls = tray_patch.start()
        self.patches.append(tray_patch)
        
        session_patch = patch('nextalk.core.controller.RecognitionSession')
        self.mock_session_cls = session_patch.start()
        self.patches.append(session_patch)
        
        # Create controller
        self.controller = MainController(self.config_path)
        
        # Setup mock instances
        self.mock_config_manager = self.controller.config_manager
        self.mock_config = Mock(spec=NexTalkConfig)
        self.mock_config.validate.return_value = []
        self.mock_config.ui.show_tray_icon = True
        self.mock_config_manager.load_config.return_value = self.mock_config
    
    def tearDown(self):
        """Clean up patches."""
        for patch in self.patches:
            patch.stop()
    
    def test_init(self):
        """Test controller initialization."""
        self.assertEqual(self.controller.state_manager.get_state(), ControllerState.UNINITIALIZED)
        self.assertIsNone(self.controller.config)
        self.assertIsNone(self.controller.audio_manager)
        self.assertIsNone(self.controller.ws_client)
        self.assertIsNone(self.controller.hotkey_manager)
        self.assertIsNone(self.controller.text_injector)
        self.assertIsNone(self.controller.tray_manager)
        self.assertIsNone(self.controller.current_session)
        self.assertEqual(len(self.controller.session_history), 0)
        self.assertFalse(self.controller._running)
    
    @patch('nextalk.core.controller.asyncio')
    async def test_initialize_success(self, mock_asyncio):
        """Test successful initialization."""
        result = await self.controller.initialize()
        
        self.assertTrue(result)
        self.assertEqual(self.controller.state_manager.get_state(), ControllerState.READY)
        self.assertEqual(self.controller.config, self.mock_config)
        
        # Check modules were created
        self.assertIsNotNone(self.controller.audio_manager)
        self.assertIsNotNone(self.controller.ws_client)
        self.assertIsNotNone(self.controller.hotkey_manager)
        self.assertIsNotNone(self.controller.text_injector)
        self.assertIsNotNone(self.controller.tray_manager)
        
        # Check callbacks were set
        self.controller.tray_manager.set_on_quit.assert_called_once()
        self.controller.tray_manager.set_on_toggle.assert_called_once()
        self.controller.tray_manager.set_on_settings.assert_called_once()
    
    @patch('nextalk.core.controller.asyncio')
    async def test_initialize_config_error(self, mock_asyncio):
        """Test initialization with config error."""
        self.mock_config.validate.return_value = ["Error 1", "Error 2"]
        
        result = await self.controller.initialize()
        
        self.assertFalse(result)
        self.assertEqual(self.controller.state_manager.get_state(), ControllerState.ERROR)
    
    @patch('nextalk.core.controller.asyncio')
    async def test_initialize_module_error(self, mock_asyncio):
        """Test initialization with module error."""
        self.mock_audio_cls.side_effect = Exception("Audio init failed")
        
        result = await self.controller.initialize()
        
        self.assertFalse(result)
        self.assertEqual(self.controller.state_manager.get_state(), ControllerState.ERROR)
    
    @patch('nextalk.core.controller.threading.Thread')
    async def test_start(self, mock_thread_cls):
        """Test starting controller."""
        # Initialize first
        await self.controller.initialize()
        
        mock_thread = Mock()
        mock_thread_cls.return_value = mock_thread
        
        self.controller.start()
        
        self.assertTrue(self.controller._running)
        self.controller.hotkey_manager.start.assert_called_once()
        self.controller.tray_manager.start.assert_called_once()
        mock_thread_cls.assert_called_once()
        mock_thread.start.assert_called_once()
    
    async def test_start_not_ready(self):
        """Test starting when not ready."""
        # Don't initialize
        self.controller.start()
        
        self.assertFalse(self.controller._running)
    
    async def test_shutdown(self):
        """Test shutdown."""
        # Initialize and start first
        await self.controller.initialize()
        self.controller._running = True
        
        self.controller.shutdown()
        
        self.assertFalse(self.controller._running)
        self.assertEqual(self.controller.state_manager.get_state(), ControllerState.SHUTDOWN)
        
        # Check modules were stopped
        self.controller.hotkey_manager.stop.assert_called_once()
        self.controller.tray_manager.stop.assert_called_once()
    
    async def test_shutdown_already_shutdown(self):
        """Test shutdown when already shutdown."""
        self.controller.state_manager.current_state = ControllerState.SHUTDOWN
        
        self.controller.shutdown()
        
        # Should return early, no modules stopped
        self.assertFalse(hasattr(self.controller.hotkey_manager, 'stop'))
    
    async def test_toggle_recognition(self):
        """Test toggling recognition."""
        await self.controller.initialize()
        
        # Mock session
        mock_session = Mock()
        mock_session.is_active.return_value = False
        self.mock_session_cls.return_value = mock_session
        
        # Start recognition
        self.controller._toggle_recognition()
        
        self.assertIsNotNone(self.controller.current_session)
        mock_session.start.assert_called_once()
        self.controller.audio_manager.start_capture.assert_called_once()
        
        # Stop recognition
        mock_session.is_active.return_value = True
        self.controller._toggle_recognition()
        
        self.controller.audio_manager.stop_capture.assert_called_once()
        mock_session.stop.assert_called_once()
    
    async def test_handle_audio_data(self):
        """Test handling audio data."""
        await self.controller.initialize()
        
        mock_session = Mock()
        self.controller.current_session = mock_session
        mock_session.is_active.return_value = True
        
        data = b"audio_data"
        self.controller._handle_audio_data(data)
        
        mock_session.add_audio_data.assert_called_once_with(data)
    
    async def test_handle_ws_message_recognition(self):
        """Test handling recognition WebSocket message."""
        mock_session = Mock()
        self.controller.current_session = mock_session
        
        message = {
            "type": "recognition_result",
            "text": "Hello world"
        }
        
        self.controller._handle_ws_message(message)
        
        mock_session.process_recognition.assert_called_once_with("Hello world")
    
    async def test_handle_ws_message_error(self):
        """Test handling error WebSocket message."""
        mock_session = Mock()
        self.controller.current_session = mock_session
        
        message = {
            "type": "error",
            "error": "Recognition failed"
        }
        
        self.controller._handle_ws_message(message)
        
        mock_session.report_error.assert_called_once_with("Recognition failed")
    
    async def test_handle_session_state_injecting(self):
        """Test handling session state change to injecting."""
        await self.controller.initialize()
        
        mock_session = Mock()
        mock_session.recognized_text = "Test text"
        self.controller.current_session = mock_session
        
        self.controller.text_injector.inject_text.return_value = True
        
        self.controller._handle_session_state(SessionState.INJECTING)
        
        self.controller.text_injector.inject_text.assert_called_once_with("Test text")
        mock_session.complete_injection.assert_called_once_with(True)
    
    async def test_handle_text_recognized(self):
        """Test handling recognized text."""
        await self.controller.initialize()
        
        text = "Recognized text content"
        self.controller._handle_text_recognized(text)
        
        self.controller.tray_manager.show_notification.assert_called_once()
    
    async def test_handle_session_error(self):
        """Test handling session error."""
        await self.controller.initialize()
        
        error = "Session error occurred"
        self.controller._handle_session_error(error)
        
        self.controller.tray_manager.update_status.assert_called_with(TrayStatus.ERROR)
        self.controller.tray_manager.show_notification.assert_called_with("识别错误", error)
    
    async def test_handle_session_complete(self):
        """Test handling session completion."""
        mock_session = Mock()
        mock_session.session_id = "test_session"
        self.controller.current_session = mock_session
        
        metrics = Mock()
        metrics.injected_successfully = True
        metrics.audio_duration = 5.0
        metrics.recognized_text = "Test text"
        metrics.session_id = "test_session"
        
        self.controller._handle_session_complete(metrics)
        
        self.assertEqual(self.controller.stats["sessions_total"], 1)
        self.assertEqual(self.controller.stats["sessions_successful"], 1)
        self.assertEqual(self.controller.stats["total_audio_time"], 5.0)
        self.assertEqual(self.controller.stats["total_text_length"], 9)
        self.assertIn(mock_session, self.controller.session_history)
    
    async def test_error_recovery(self):
        """Test error recovery mechanism."""
        await self.controller.initialize()
        
        # Trigger error state
        self.controller.state_manager.transition(ControllerEvent.ERROR_OCCURRED, {"error": "Test error"})
        
        # Check tray updated
        self.controller.tray_manager.update_status.assert_called_with(TrayStatus.ERROR)
        
        # Test recovery attempt
        with patch('threading.Timer') as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance
            
            # Call error state handler
            self.controller._on_error_state(
                ControllerState.READY,
                ControllerState.ERROR,
                ControllerEvent.ERROR_OCCURRED,
                {"error": "Test error"}
            )
            
            # Check recovery scheduled
            mock_timer.assert_called_once_with(5.0, self.controller._attempt_recovery)
            mock_timer_instance.start.assert_called_once()
    
    async def test_recovery_max_attempts(self):
        """Test recovery stops after max attempts."""
        await self.controller.initialize()
        
        self.controller._recovery_attempts = 3
        self.controller._max_recovery_attempts = 3
        
        with patch('threading.Timer') as mock_timer:
            self.controller._on_error_state(
                ControllerState.READY,
                ControllerState.ERROR,
                ControllerEvent.ERROR_OCCURRED,
                None
            )
            
            # Should not schedule recovery
            mock_timer.assert_not_called()
    
    def test_get_statistics(self):
        """Test getting statistics."""
        self.controller.stats["start_time"] = time.time() - 100
        self.controller.stats["sessions_total"] = 5
        
        stats = self.controller.get_statistics()
        
        self.assertEqual(stats["sessions_total"], 5)
        self.assertEqual(stats["state"], ControllerState.UNINITIALIZED.value)
        self.assertIn("uptime", stats)
        self.assertIsNone(stats["active_session"])
        self.assertEqual(stats["session_history_count"], 0)
    
    def test_is_running(self):
        """Test checking if running."""
        self.assertFalse(self.controller.is_running())
        
        self.controller._running = True
        self.controller.state_manager.current_state = ControllerState.READY
        self.assertTrue(self.controller.is_running())
        
        self.controller.state_manager.current_state = ControllerState.SHUTDOWN
        self.assertFalse(self.controller.is_running())


class TestControllerIntegration(unittest.TestCase):
    """Test controller integration scenarios."""
    
    @patch('nextalk.core.controller.ConfigManager')
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    @patch('nextalk.core.controller.RecognitionSession')
    async def test_full_recognition_flow(self, mock_session_cls, mock_tray_cls,
                                       mock_injector_cls, mock_hotkey_cls,
                                       mock_ws_cls, mock_audio_cls, mock_config_cls):
        """Test complete recognition flow."""
        controller = MainController()
        
        # Setup mocks
        mock_config = Mock()
        mock_config.validate.return_value = []
        mock_config.ui.show_tray_icon = True
        controller.config_manager.load_config.return_value = mock_config
        
        # Initialize
        await controller.initialize()
        
        # Start recognition
        mock_session = Mock()
        mock_session.is_active.side_effect = [False, True, True]
        mock_session.recognized_text = "Test recognition"
        mock_session_cls.return_value = mock_session
        
        controller._start_recognition()
        
        # Simulate audio data
        controller._handle_audio_data(b"audio1")
        controller._handle_audio_data(b"audio2")
        
        # Simulate recognition result
        controller._handle_ws_message({
            "type": "recognition_result",
            "text": "Test recognition"
        })
        
        # Simulate injection
        controller.text_injector.inject_text.return_value = True
        controller._handle_session_state(SessionState.INJECTING)
        
        # Complete session
        metrics = Mock()
        metrics.injected_successfully = True
        metrics.audio_duration = 3.0
        metrics.recognized_text = "Test recognition"
        metrics.session_id = "test_id"
        
        controller._handle_session_complete(metrics)
        
        # Verify flow
        self.assertEqual(controller.stats["sessions_successful"], 1)
        self.assertEqual(len(controller.session_history), 1)
    
    @patch('nextalk.core.controller.ConfigManager')
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_state_transitions(self, mock_tray_cls, mock_injector_cls,
                                    mock_hotkey_cls, mock_ws_cls,
                                    mock_audio_cls, mock_config_cls):
        """Test state transitions through lifecycle."""
        controller = MainController()
        
        # Track state changes
        state_changes = []
        
        def record_state(from_state, to_state, event, data):
            state_changes.append((from_state, to_state, event))
        
        # Register listener for all states
        for state in ControllerState:
            controller.state_manager.register_state_listener(state, record_state)
        
        # Setup mock config
        mock_config = Mock()
        mock_config.validate.return_value = []
        mock_config.ui.show_tray_icon = False
        controller.config_manager.load_config.return_value = mock_config
        
        # Go through lifecycle
        await controller.initialize()
        controller.shutdown()
        
        # Check state transitions
        expected_transitions = [
            (ControllerState.UNINITIALIZED, ControllerState.INITIALIZING, ControllerEvent.INITIALIZE),
            (ControllerState.INITIALIZING, ControllerState.READY, ControllerEvent.MODULE_READY),
            (ControllerState.READY, ControllerState.SHUTTING_DOWN, ControllerEvent.SHUTDOWN),
            (ControllerState.SHUTTING_DOWN, ControllerState.SHUTDOWN, ControllerEvent.SHUTDOWN)
        ]
        
        for expected in expected_transitions:
            self.assertIn(expected, state_changes)


if __name__ == '__main__':
    unittest.main()