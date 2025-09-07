"""
Integration tests for voice recognition flow.
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from pathlib import Path
import tempfile

from nextalk.core.controller import MainController, ControllerState
from nextalk.core.session import SessionState
from nextalk.config.models import NexTalkConfig
from nextalk.ui.tray import TrayStatus


class TestVoiceRecognitionFlow(unittest.TestCase):
    """Test complete voice recognition flow."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"
        
        # Write test config
        config_content = """
audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 1024
  device_index: null

network:
  server_url: "ws://localhost:10095"
  reconnect_interval: 5
  max_reconnect_attempts: 3

hotkey:
  trigger_key: "ctrl+alt+space"
  cancel_key: "escape"

text_injection:
  method: "typing"
  typing_delay: 0.01

ui:
  show_tray_icon: false
  show_notifications: false
"""
        self.config_file.write_text(config_content)
        
        # Patch dependencies
        self.patches = []
        
        # Patch audio
        audio_patch = patch('nextalk.core.controller.AudioCaptureManager')
        self.mock_audio_cls = audio_patch.start()
        self.patches.append(audio_patch)
        
        # Patch WebSocket
        ws_patch = patch('nextalk.core.controller.WebSocketClient')
        self.mock_ws_cls = ws_patch.start()
        self.patches.append(ws_patch)
        
        # Patch hotkey
        hotkey_patch = patch('nextalk.core.controller.HotkeyManager')
        self.mock_hotkey_cls = hotkey_patch.start()
        self.patches.append(hotkey_patch)
        
        # Patch text injector
        injector_patch = patch('nextalk.core.controller.TextInjector')
        self.mock_injector_cls = injector_patch.start()
        self.patches.append(injector_patch)
        
        # Patch tray
        tray_patch = patch('nextalk.core.controller.SystemTrayManager')
        self.mock_tray_cls = tray_patch.start()
        self.patches.append(tray_patch)
    
    def tearDown(self):
        """Clean up test environment."""
        for patch in self.patches:
            patch.stop()
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_complete_recognition_flow(self):
        """Test complete voice recognition flow."""
        # Create controller
        controller = MainController(str(self.config_file))
        
        # Initialize
        result = await controller.initialize()
        self.assertTrue(result)
        self.assertEqual(controller.state_manager.get_state(), ControllerState.READY)
        
        # Setup mock instances
        mock_audio = controller.audio_manager
        mock_ws = controller.ws_client
        mock_injector = controller.text_injector
        mock_tray = controller.tray_manager
        
        # Configure mock behaviors
        mock_ws.is_connected.return_value = True
        mock_injector.inject_text.return_value = True
        
        # Simulate hotkey trigger
        controller._handle_hotkey_trigger()
        
        # Verify recognition started
        self.assertEqual(controller.state_manager.get_state(), ControllerState.ACTIVE)
        mock_audio.start_capture.assert_called_once()
        
        # Simulate audio data
        audio_callback = mock_audio.start_capture.call_args[0][0]
        audio_callback(b"audio_chunk_1")
        audio_callback(b"audio_chunk_2")
        
        # Verify audio added to session
        self.assertIsNotNone(controller.current_session)
        self.assertTrue(controller.current_session.is_active())
        
        # Simulate recognition result
        controller._handle_ws_message({
            "type": "recognition_result",
            "text": "Hello world"
        })
        
        # Simulate stop recognition
        controller._stop_recognition()
        
        # Verify text injection
        controller._handle_session_state(SessionState.INJECTING)
        mock_injector.inject_text.assert_called_with("Hello world")
        
        # Verify state returned to ready
        self.assertEqual(controller.state_manager.get_state(), ControllerState.READY)
    
    async def test_recognition_with_error(self):
        """Test recognition flow with error handling."""
        controller = MainController(str(self.config_file))
        
        # Initialize
        await controller.initialize()
        
        # Setup error scenario
        mock_ws = controller.ws_client
        mock_ws.is_connected.return_value = False
        
        # Start recognition
        controller._start_recognition()
        
        # Simulate WebSocket error
        controller._handle_ws_error("Connection lost")
        
        # Verify error handling
        self.assertIsNotNone(controller.current_session)
        self.assertEqual(controller.current_session.error_message, "网络错误: Connection lost")
        
        # Verify recovery attempt
        self.assertEqual(controller.state_manager.get_state(), ControllerState.ERROR)
    
    async def test_cancel_recognition(self):
        """Test canceling recognition."""
        controller = MainController(str(self.config_file))
        
        # Initialize
        await controller.initialize()
        
        # Start recognition
        controller._start_recognition()
        self.assertIsNotNone(controller.current_session)
        
        # Cancel session
        controller.current_session.cancel()
        
        # Verify cancellation
        self.assertEqual(controller.current_session.state, SessionState.CANCELLED)
        
        # Stop recognition
        controller._stop_recognition()
        
        # Verify cleanup
        controller.audio_manager.stop_capture.assert_called_once()
    
    async def test_multiple_sessions(self):
        """Test multiple recognition sessions."""
        controller = MainController(str(self.config_file))
        
        # Initialize
        await controller.initialize()
        
        mock_injector = controller.text_injector
        mock_injector.inject_text.return_value = True
        
        # Run multiple sessions
        texts = ["First text", "Second text", "Third text"]
        
        for text in texts:
            # Start recognition
            controller._start_recognition()
            
            # Add audio
            audio_callback = controller.audio_manager.start_capture.call_args[0][0]
            audio_callback(b"audio_data")
            
            # Process recognition
            controller._handle_ws_message({
                "type": "recognition_result",
                "text": text
            })
            
            # Stop and inject
            controller._stop_recognition()
            controller._handle_session_state(SessionState.INJECTING)
            controller.current_session.complete_injection(True)
            
            # Wait a bit
            await asyncio.sleep(0.1)
        
        # Verify statistics
        self.assertEqual(controller.stats["sessions_total"], 3)
        self.assertEqual(controller.stats["sessions_successful"], 3)
        self.assertEqual(len(controller.session_history), 3)


class TestSystemIntegration(unittest.TestCase):
    """Test system-wide integration."""
    
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_full_system_lifecycle(self, mock_tray_cls, mock_injector_cls,
                                        mock_hotkey_cls, mock_ws_cls, mock_audio_cls):
        """Test full system lifecycle."""
        controller = MainController()
        
        # Initialize system
        await controller.initialize()
        self.assertEqual(controller.state_manager.get_state(), ControllerState.READY)
        
        # Start controller
        with patch('threading.Thread'):
            controller.start()
            self.assertTrue(controller._running)
        
        # Verify modules started
        controller.hotkey_manager.start.assert_called_once()
        
        # Simulate user interactions
        for i in range(3):
            controller._toggle_recognition()
            await asyncio.sleep(0.1)
            controller._toggle_recognition()
            await asyncio.sleep(0.1)
        
        # Shutdown system
        controller.shutdown()
        
        # Verify clean shutdown
        self.assertFalse(controller._running)
        self.assertEqual(controller.state_manager.get_state(), ControllerState.SHUTDOWN)
        controller.hotkey_manager.stop.assert_called_once()
    
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_error_recovery_flow(self, mock_tray_cls, mock_injector_cls,
                                      mock_hotkey_cls, mock_ws_cls, mock_audio_cls):
        """Test error recovery flow."""
        controller = MainController()
        
        # Initialize
        await controller.initialize()
        
        # Simulate error
        controller.state_manager.transition(ControllerEvent.ERROR_OCCURRED, 
                                           {"error": "Test error"})
        
        self.assertEqual(controller.state_manager.get_state(), ControllerState.ERROR)
        
        # Trigger recovery
        with patch.object(controller, '_async_recovery', new_callable=AsyncMock) as mock_recovery:
            mock_recovery.return_value = None
            controller._attempt_recovery()
            
            # Should transition to recovering
            self.assertEqual(controller.state_manager.get_state(), ControllerState.RECOVERING)
        
        # Simulate successful recovery
        controller.state_manager.transition(ControllerEvent.MODULE_READY)
        self.assertEqual(controller.state_manager.get_state(), ControllerState.READY)
        
        # Verify recovery count reset
        self.assertEqual(controller._recovery_attempts, 0)
    
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_concurrent_operations(self, mock_tray_cls, mock_injector_cls,
                                        mock_hotkey_cls, mock_ws_cls, mock_audio_cls):
        """Test concurrent operations handling."""
        controller = MainController()
        
        # Initialize
        await controller.initialize()
        
        # Try to start multiple recognitions concurrently
        tasks = []
        for _ in range(5):
            task = asyncio.create_task(
                asyncio.to_thread(controller._start_recognition)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # Should only have one active session
        self.assertIsNotNone(controller.current_session)
        
        # Verify only one capture started
        self.assertEqual(controller.audio_manager.start_capture.call_count, 1)


class TestModuleIntegration(unittest.TestCase):
    """Test integration between modules."""
    
    async def test_audio_to_websocket_flow(self):
        """Test audio capture to WebSocket flow."""
        from nextalk.audio.capture import AudioCaptureManager
        from nextalk.network.ws_client import FunASRWebSocketClient
        from nextalk.config.models import AudioConfig, NexTalkConfig
        
        # Create config
        audio_config = AudioConfig()
        config = NexTalkConfig(audio=audio_config)
        
        # Create modules
        with patch('pyaudio.PyAudio'):
            audio_manager = AudioCaptureManager(audio_config)
        
        with patch('websockets.connect'):
            ws_client = FunASRWebSocketClient(config)
        
        # Setup mock connection
        ws_client._ws = AsyncMock()
        ws_client._connected = True
        
        # Capture audio data
        audio_data = []
        def capture_callback(data):
            audio_data.append(data)
        
        with patch.object(audio_manager, '_capture_thread_func'):
            audio_manager.start_capture(capture_callback)
            
            # Simulate audio data
            test_data = b"test_audio_chunk"
            audio_manager._callback(test_data)
        
        # Verify data captured
        self.assertIn(test_data, audio_data)
        
        # Send to WebSocket
        await ws_client.send_audio(test_data)
        
        # Verify sent
        ws_client._ws.send.assert_called()
    
    async def test_hotkey_to_controller_flow(self):
        """Test hotkey trigger to controller flow."""
        from nextalk.input.hotkey import HotkeyManager
        from nextalk.config.models import HotkeyConfig
        
        # Create config
        hotkey_config = HotkeyConfig(
            trigger_key="ctrl+alt+space",
            cancel_key="escape"
        )
        
        # Create hotkey manager
        with patch('pynput.keyboard.GlobalHotKeys'):
            hotkey_manager = HotkeyManager(hotkey_config)
            
            # Register callback
            triggered = False
            def on_trigger():
                nonlocal triggered
                triggered = True
            
            hotkey_manager.register("ctrl+alt+space", on_trigger, "Test")
            
            # Simulate hotkey press
            hotkey_manager._trigger_hotkey("ctrl+alt+space")
            
            # Verify callback triggered
            self.assertTrue(triggered)
    
    async def test_recognition_to_injection_flow(self):
        """Test recognition result to text injection flow."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        # Create config
        injection_config = TextInjectionConfig(
            method="typing",
            typing_delay=0.01
        )
        
        # Create injector
        with patch('pyautogui.typewrite') as mock_typewrite:
            injector = TextInjector(injection_config)
            
            # Inject text
            text = "Test injection"
            result = injector.inject_text(text)
            
            # Verify injection
            self.assertTrue(result)
            mock_typewrite.assert_called_with(text, interval=0.01)
    
    async def test_session_state_flow(self):
        """Test session state transitions."""
        from nextalk.core.session import RecognitionSession
        
        session = RecognitionSession()
        
        # Track state changes
        states = []
        session.set_on_state_change(lambda s: states.append(s))
        
        # Run through states
        session.start()
        self.assertIn(SessionState.RECORDING, states)
        
        session.add_audio_data(b"audio1")
        session.add_audio_data(b"audio2")
        
        session.stop()
        self.assertIn(SessionState.PROCESSING, states)
        
        session.process_recognition("Test text")
        self.assertIn(SessionState.INJECTING, states)
        
        session.complete_injection(True)
        self.assertIn(SessionState.COMPLETED, states)
        
        # Verify final state
        self.assertEqual(session.state, SessionState.COMPLETED)
        self.assertTrue(session.injection_successful)


if __name__ == '__main__':
    # Run async tests
    unittest.main()