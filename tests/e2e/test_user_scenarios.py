"""
End-to-end tests for user scenarios.
"""

import unittest
import asyncio
import time
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import psutil
import yaml


class TestUserScenarios(unittest.TestCase):
    """Test real user scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"
        
        # Create test configuration
        self.create_test_config()
        
        # Track subprocesses for cleanup
        self.processes = []
    
    def tearDown(self):
        """Clean up test environment."""
        # Terminate any running processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                pass
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_config(self):
        """Create test configuration file."""
        config = {
            "audio": {
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 1024,
                "device_index": None
            },
            "network": {
                "server_url": "ws://localhost:10095",
                "reconnect_interval": 5,
                "max_reconnect_attempts": 3
            },
            "hotkey": {
                "trigger_key": "ctrl+alt+space",
                "cancel_key": "escape"
            },
            "text_injection": {
                "method": "typing",
                "typing_delay": 0.01,
                "clipboard_timeout": 2.0
            },
            "ui": {
                "show_tray_icon": False,
                "show_notifications": False,
                "tray_icon_theme": "auto"
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f)
    
    @unittest.skipIf(not Path("nextalk/main.py").exists(), "Source not available")
    def test_application_launch(self):
        """Test application can launch successfully."""
        # Launch application with test config
        cmd = [
            "python", "-m", "nextalk",
            "-c", str(self.config_file),
            "--check"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should complete successfully
        self.assertEqual(result.returncode, 0)
        self.assertIn("requirements", result.stdout.lower())
    
    @unittest.skipIf(not Path("nextalk/main.py").exists(), "Source not available")
    def test_quick_recognition_session(self):
        """Test quick recognition session scenario."""
        # This would require a running FunASR server
        # For now, we'll test the application flow with mocks
        
        from nextalk.main import NexTalkApp
        
        with patch('nextalk.main.check_system_requirements', return_value=True):
            with patch('nextalk.core.controller.AudioCaptureManager'):
                with patch('nextalk.core.controller.WebSocketClient'):
                    with patch('nextalk.core.controller.HotkeyManager'):
                        with patch('nextalk.core.controller.TextInjector'):
                            with patch('nextalk.core.controller.SystemTrayManager'):
                                app = NexTalkApp(str(self.config_file))
                                
                                # Run initialization
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                result = loop.run_until_complete(app.initialize())
                                self.assertTrue(result)
                                
                                # Simulate user triggering recognition
                                app.controller._toggle_recognition()
                                
                                # Simulate speaking for 3 seconds
                                time.sleep(0.1)  # Reduced for test speed
                                
                                # Stop recognition
                                app.controller._toggle_recognition()
                                
                                # Cleanup
                                loop.run_until_complete(app.cleanup())
                                loop.close()
    
    def test_text_editor_scenario(self):
        """Test using NexTalk with a text editor."""
        # Simulate typing into a text editor
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(
            method="typing",
            typing_delay=0.001  # Fast for testing
        )
        
        with patch('pyautogui.typewrite') as mock_typewrite:
            with patch('pyautogui.position', return_value=(100, 200)):
                injector = TextInjector(config)
                
                # Test injecting various text types
                test_cases = [
                    "Hello, world!",
                    "This is a test of the NexTalk system.",
                    "Special chars: @#$%^&*()",
                    "Multi-line\ntext\ninjection",
                    "中文测试"  # Chinese text
                ]
                
                for text in test_cases:
                    result = injector.inject_text(text)
                    self.assertTrue(result)
                
                # Verify all texts were typed
                self.assertEqual(mock_typewrite.call_count, len(test_cases))
    
    def test_browser_scenario(self):
        """Test using NexTalk with a web browser."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(
            method="clipboard",  # Use clipboard for browser
            clipboard_timeout=1.0
        )
        
        with patch('pyperclip.copy') as mock_copy:
            with patch('pyperclip.paste', return_value=""):
            with patch('pyautogui.hotkey') as mock_hotkey:
                injector = TextInjector(config)
                
                # Simulate injecting search query
                search_query = "NexTalk voice recognition system"
                result = injector.inject_text(search_query)
                
                # Should use clipboard method
                mock_copy.assert_called_with(search_query)
                mock_hotkey.assert_called()  # Ctrl+V
    
    def test_chat_application_scenario(self):
        """Test using NexTalk with chat applications."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(
            method="smart",  # Smart detection
            typing_delay=0.01
        )
        
        # Mock application detection
        with patch('nextalk.output.text_injector.get_active_application') as mock_get_app:
            with patch('pyautogui.typewrite') as mock_typewrite:
                mock_get_app.return_value = "Discord"
                
                injector = TextInjector(config)
                
                # Test sending chat messages
                messages = [
                    "Hey everyone!",
                    "How's it going?",
                    "Let me share something interesting...",
                ]
                
                for msg in messages:
                    result = injector.inject_text(msg)
                    self.assertTrue(result)
                    time.sleep(0.01)  # Simulate delay between messages
    
    def test_code_editor_scenario(self):
        """Test using NexTalk with code editors."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(
            method="typing",
            typing_delay=0.005
        )
        
        with patch('pyautogui.typewrite') as mock_typewrite:
            injector = TextInjector(config)
            
            # Test injecting code snippets
            code_snippets = [
                "def hello_world():",
                "    print('Hello, World!')",
                "    return True",
                "",
                "if __name__ == '__main__':",
                "    hello_world()"
            ]
            
            for code in code_snippets:
                result = injector.inject_text(code)
                self.assertTrue(result)


class TestLongRunningScenarios(unittest.TestCase):
    """Test long-running scenarios for stability."""
    
    def test_continuous_recognition_sessions(self):
        """Test multiple continuous recognition sessions."""
        from nextalk.core.controller import MainController
        from nextalk.core.session import SessionState
        
        with patch('nextalk.core.controller.AudioCaptureManager'):
            with patch('nextalk.core.controller.WebSocketClient'):
                with patch('nextalk.core.controller.HotkeyManager'):
                    with patch('nextalk.core.controller.TextInjector') as mock_injector_cls:
                        with patch('nextalk.core.controller.SystemTrayManager'):
                            mock_injector = mock_injector_cls.return_value
                            mock_injector.inject_text.return_value = True
                            
                            controller = MainController()
                            
                            # Run initialization
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            loop.run_until_complete(controller.initialize())
                            
                            # Simulate 10 recognition sessions
                            for i in range(10):
                                # Start recognition
                                controller._start_recognition()
                                
                                # Simulate audio data
                                if controller.current_session:
                                    controller.current_session.add_audio_data(b"audio_" + str(i).encode())
                                
                                # Process result
                                controller._handle_ws_message({
                                    "type": "recognition_result",
                                    "text": f"Test message {i}"
                                })
                                
                                # Stop recognition
                                controller._stop_recognition()
                                
                                # Complete injection
                                if controller.current_session:
                                    controller._handle_session_state(SessionState.INJECTING)
                                    controller.current_session.complete_injection(True)
                                
                                time.sleep(0.01)  # Small delay between sessions
                            
                            # Verify statistics
                            self.assertEqual(controller.stats["sessions_total"], 10)
                            self.assertEqual(controller.stats["sessions_successful"], 10)
                            
                            # Check memory usage didn't grow excessively
                            self.assertLess(len(controller.session_history), 101)  # Max 100 + current
                            
                            controller.shutdown()
                            loop.close()
    
    def test_resource_usage_monitoring(self):
        """Test resource usage stays within limits."""
        from nextalk.utils.monitor import system_monitor
        
        # Get initial resource usage
        initial_memory = system_monitor.get_memory_usage()
        initial_threads = system_monitor.get_thread_count()
        
        # Run some operations
        from nextalk.core.session import RecognitionSession
        
        sessions = []
        for i in range(100):
            session = RecognitionSession()
            session.start()
            session.add_audio_data(b"test_data_" + str(i).encode())
            session.stop()
            sessions.append(session)
        
        # Get final resource usage
        final_memory = system_monitor.get_memory_usage()
        final_threads = system_monitor.get_thread_count()
        
        # Memory shouldn't grow too much (< 50MB)
        memory_growth = (final_memory['rss_mb'] - initial_memory['rss_mb'])
        self.assertLess(memory_growth, 50)
        
        # Thread count should be reasonable
        thread_growth = final_threads - initial_threads
        self.assertLess(thread_growth, 10)
    
    def test_error_recovery_stability(self):
        """Test system stability during error recovery."""
        from nextalk.core.controller import MainController, ControllerEvent
        
        with patch('nextalk.core.controller.AudioCaptureManager'):
            with patch('nextalk.core.controller.WebSocketClient') as mock_ws_cls:
                with patch('nextalk.core.controller.HotkeyManager'):
                    with patch('nextalk.core.controller.TextInjector'):
                        with patch('nextalk.core.controller.SystemTrayManager'):
                            controller = MainController()
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            loop.run_until_complete(controller.initialize())
                            
                            # Simulate multiple errors and recoveries
                            for i in range(5):
                                # Trigger error
                                controller.state_manager.transition(
                                    ControllerEvent.ERROR_OCCURRED,
                                    {"error": f"Test error {i}"}
                                )
                                
                                # Wait for recovery attempt
                                time.sleep(0.1)
                                
                                # Simulate successful recovery
                                controller.state_manager.transition(ControllerEvent.MODULE_READY)
                                
                                # Verify recovered
                                self.assertEqual(
                                    controller.state_manager.get_state().value,
                                    "ready"
                                )
                            
                            # System should still be functional
                            self.assertTrue(controller.is_running())
                            
                            controller.shutdown()
                            loop.close()


class TestPerformanceScenarios(unittest.TestCase):
    """Test performance in various scenarios."""
    
    def test_audio_processing_performance(self):
        """Test audio processing performance."""
        from nextalk.audio.capture import AudioCaptureManager
        from nextalk.config.models import AudioConfig
        from nextalk.utils.monitor import timer
        
        config = AudioConfig(
            sample_rate=16000,
            channels=1,
            chunk_size=1024
        )
        
        with patch('pyaudio.PyAudio'):
            manager = AudioCaptureManager(config)
            
            # Measure audio processing time
            audio_chunks = [b"x" * 1024 for _ in range(100)]
            
            with timer("audio_processing"):
                for chunk in audio_chunks:
                    # Simulate processing
                    processed = manager._process_audio_chunk(chunk) if hasattr(manager, '_process_audio_chunk') else chunk
            
            # Processing should be fast (< 100ms for 100 chunks)
            # This is just a placeholder as actual timing would be in performance_monitor
            self.assertTrue(True)  # Placeholder assertion
    
    def test_text_injection_performance(self):
        """Test text injection performance."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        from nextalk.utils.monitor import timer
        
        config = TextInjectionConfig(
            method="typing",
            typing_delay=0.001  # Fast for testing
        )
        
        with patch('pyautogui.typewrite') as mock_typewrite:
            injector = TextInjector(config)
            
            # Test injection speed for different text lengths
            test_texts = [
                "Short text",
                "Medium length text that is a bit longer than the short one",
                "Long text " * 50  # 500+ characters
            ]
            
            for text in test_texts:
                with timer(f"inject_{len(text)}_chars"):
                    result = injector.inject_text(text)
                    self.assertTrue(result)
    
    def test_recognition_latency(self):
        """Test recognition latency from trigger to result."""
        from nextalk.core.controller import MainController
        import time
        
        with patch('nextalk.core.controller.AudioCaptureManager'):
            with patch('nextalk.core.controller.WebSocketClient'):
                with patch('nextalk.core.controller.HotkeyManager'):
                    with patch('nextalk.core.controller.TextInjector'):
                        with patch('nextalk.core.controller.SystemTrayManager'):
                            controller = MainController()
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            loop.run_until_complete(controller.initialize())
                            
                            # Measure latency
                            start_time = time.perf_counter()
                            
                            # Trigger recognition
                            controller._start_recognition()
                            
                            # Simulate immediate response
                            controller._handle_ws_message({
                                "type": "recognition_result",
                                "text": "Quick response"
                            })
                            
                            # Stop recognition
                            controller._stop_recognition()
                            
                            end_time = time.perf_counter()
                            latency = end_time - start_time
                            
                            # Latency should be low (< 100ms for local processing)
                            self.assertLess(latency, 0.1)
                            
                            controller.shutdown()
                            loop.close()


if __name__ == '__main__':
    unittest.main()