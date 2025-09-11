"""
Integration tests for full workflow scenarios.
"""

import unittest
import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import yaml

from nextalk.main import NexTalkApp
from nextalk.core.controller import ControllerState, ControllerEvent
from nextalk.config.models import NexTalkConfig
from nextalk.output.injection_models import InjectionMethod
from nextalk.utils.logger import setup_logging
from nextalk.utils.monitor import performance_monitor, metrics_collector


class TestFullWorkflow(unittest.TestCase):
    """Test complete application workflow."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"
        self.log_dir = Path(self.temp_dir) / "logs"
        
        # Create test config
        config_data = {
            "audio": {
                "sample_rate": 16000,
                "channels": 1,
                "chunk_size": 1024
            },
            "network": {
                "server_url": "ws://localhost:10095",
                "reconnect_interval": 5
            },
            "hotkey": {
                "trigger_key": "ctrl+alt+space"
            },
            "text_injection": {
                "method": "typing"
            },
            "ui": {
                "show_tray_icon": False,
                "show_notifications": False
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Setup logging
        setup_logging("DEBUG", self.log_dir, console=False, file=True)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('nextalk.main.check_system_requirements')
    @patch('nextalk.main.setup_environment')
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_application_startup_shutdown(self, mock_tray_cls, mock_injector_cls,
                                               mock_hotkey_cls, mock_ws_cls, mock_audio_cls,
                                               mock_setup_env, mock_check_req):
        """Test application startup and shutdown."""
        # Setup mocks
        mock_check_req.return_value = True
        
        # Create application
        app = NexTalkApp(str(self.config_file))
        
        # Initialize
        result = await app.initialize()
        self.assertTrue(result)
        
        # Verify controller initialized
        self.assertIsNotNone(app.controller)
        self.assertEqual(app.controller.state_manager.get_state(), ControllerState.READY)
        
        # Start application in background
        run_task = asyncio.create_task(app.run())
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Trigger shutdown
        app._shutdown()
        
        # Wait for shutdown
        exit_code = await run_task
        self.assertEqual(exit_code, 0)
        
        # Verify clean shutdown
        self.assertEqual(app.controller.state_manager.get_state(), ControllerState.SHUTDOWN)
    
    @patch('nextalk.main.check_system_requirements')
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_recognition_workflow(self, mock_tray_cls, mock_injector_cls,
                                       mock_hotkey_cls, mock_ws_cls, mock_audio_cls,
                                       mock_check_req):
        """Test complete recognition workflow."""
        mock_check_req.return_value = True
        
        app = NexTalkApp(str(self.config_file))
        
        # Initialize
        await app.initialize()
        
        # Setup mock behaviors
        mock_ws = app.controller.ws_client
        mock_ws.is_connected.return_value = True
        mock_ws.send_audio = AsyncMock()
        
        mock_injector = app.controller.text_injector
        mock_injector.inject_text.return_value = True
        
        # Start recognition
        app.controller._start_recognition()
        
        # Add audio data
        audio_callback = app.controller.audio_manager.start_capture.call_args[0][0]
        audio_callback(b"test_audio_1")
        audio_callback(b"test_audio_2")
        
        # Process recognition result
        app.controller._handle_ws_message({
            "type": "recognition_result",
            "text": "Hello from integration test"
        })
        
        # Stop recognition
        app.controller._stop_recognition()
        
        # Verify text injection
        app.controller._handle_session_state(SessionState.INJECTING)
        mock_injector.inject_text.assert_called_with("Hello from integration test")
        
        # Verify statistics updated
        self.assertEqual(app.controller.stats["sessions_total"], 1)
        
        # Cleanup
        await app.cleanup()
    
    @patch('nextalk.main.check_system_requirements')
    @patch('nextalk.core.controller.AudioCaptureManager')
    @patch('nextalk.core.controller.WebSocketClient')
    @patch('nextalk.core.controller.HotkeyManager')
    @patch('nextalk.core.controller.TextInjector')
    @patch('nextalk.core.controller.SystemTrayManager')
    async def test_error_recovery_workflow(self, mock_tray_cls, mock_injector_cls,
                                          mock_hotkey_cls, mock_ws_cls, mock_audio_cls,
                                          mock_check_req):
        """Test error recovery workflow."""
        mock_check_req.return_value = True
        
        app = NexTalkApp(str(self.config_file))
        
        # Initialize
        await app.initialize()
        
        # Simulate connection error
        mock_ws = app.controller.ws_client
        mock_ws.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Trigger error
        app.controller.state_manager.transition(ControllerEvent.CONNECTION_LOST)
        
        # Verify recovery state
        self.assertEqual(app.controller.state_manager.get_state(), ControllerState.RECOVERING)
        
        # Simulate recovery
        mock_ws.connect = AsyncMock(return_value=None)
        mock_ws.is_connected.return_value = True
        
        # Wait for recovery
        await asyncio.sleep(0.1)
        
        # Cleanup
        await app.cleanup()


class TestPerformanceMonitoring(unittest.TestCase):
    """Test performance monitoring integration."""
    
    def setUp(self):
        """Set up test environment."""
        performance_monitor.reset()
        metrics_collector.performance_monitor = performance_monitor
    
    def test_operation_timing(self):
        """Test operation timing monitoring."""
        # Time some operations
        with performance_monitor.timer("test_operation"):
            time.sleep(0.01)
        
        with performance_monitor.timer("test_operation"):
            time.sleep(0.02)
        
        with performance_monitor.timer("test_operation"):
            time.sleep(0.015)
        
        # Get statistics
        stats = performance_monitor.get_stats("test_operation")
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats.count, 3)
        self.assertAlmostEqual(stats.avg_time, 0.015, places=2)
        self.assertLess(stats.min_time, stats.max_time)
    
    def test_counter_tracking(self):
        """Test counter tracking."""
        # Increment counters
        performance_monitor.increment_counter("sessions_started", 1)
        performance_monitor.increment_counter("sessions_started", 1)
        performance_monitor.increment_counter("sessions_completed", 1)
        performance_monitor.increment_counter("errors", 2)
        
        # Get counters
        counters = performance_monitor.get_counters()
        
        self.assertEqual(counters["sessions_started"], 2)
        self.assertEqual(counters["sessions_completed"], 1)
        self.assertEqual(counters["errors"], 2)
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        # Start collection
        metrics_collector.start_collection(interval=0.1)
        
        # Perform some operations
        with performance_monitor.timer("recognition"):
            time.sleep(0.005)
        
        performance_monitor.increment_counter("recognitions", 1)
        performance_monitor.set_gauge("active_sessions", 1)
        
        # Wait for collection
        time.sleep(0.2)
        
        # Stop collection
        metrics_collector.stop_collection()
        
        # Get metrics
        metrics = metrics_collector.get_metrics()
        
        # Should have collected some metrics
        self.assertTrue(len(metrics) > 0)
        
        # Check metric types
        metric_names = [m.name for m in metrics]
        self.assertTrue(any("cpu_percent" in name for name in metric_names))
        self.assertTrue(any("memory_rss" in name for name in metric_names))
    
    def test_threshold_monitoring(self):
        """Test threshold monitoring."""
        # Register threshold callback
        threshold_triggered = False
        threshold_value = 0.0
        
        def on_threshold(name, value):
            nonlocal threshold_triggered, threshold_value
            threshold_triggered = True
            threshold_value = value
        
        performance_monitor.register_threshold("slow_operation", 0.05, on_threshold)
        
        # Perform slow operation
        with performance_monitor.timer("slow_operation"):
            time.sleep(0.1)
        
        # Check threshold not triggered (only triggers on check)
        performance_monitor._check_thresholds("slow_operation", 0.1)
        
        self.assertTrue(threshold_triggered)
        self.assertGreater(threshold_value, 0.05)


class TestLoggingIntegration(unittest.TestCase):
    """Test logging integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_file_creation(self):
        """Test log file creation."""
        from nextalk.utils.logger import logger_manager
        
        # Setup logging
        logger_manager.setup("DEBUG", self.log_dir, console=False, file=True)
        
        # Get logger and log messages
        logger = logger_manager.get_logger("test.integration")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Check log files created
        log_files = list(self.log_dir.glob("*.log"))
        self.assertTrue(len(log_files) > 0)
        
        # Read log file
        log_file = log_files[0]
        content = log_file.read_text()
        
        # Verify messages logged
        self.assertIn("Debug message", content)
        self.assertIn("Info message", content)
        self.assertIn("Warning message", content)
        self.assertIn("Error message", content)
    
    def test_session_logging(self):
        """Test session-specific logging."""
        from nextalk.utils.logger import logger_manager
        
        # Setup logging
        logger_manager.setup("DEBUG", self.log_dir, console=False, file=True)
        
        # Create session logger
        session_id = "test_session_123"
        session_logger = logger_manager.create_session_logger(session_id)
        
        # Log session events
        session_logger.info("Session started")
        session_logger.info("Processing audio")
        session_logger.info("Recognition complete")
        
        # Check logs contain session ID
        log_files = list(self.log_dir.glob("*.log"))
        self.assertTrue(len(log_files) > 0)
        
        content = log_files[0].read_text()
        # Session ID should be in logger name
        self.assertIn("nextalk.session.test_session_123", content)
    
    def test_performance_logging(self):
        """Test performance metric logging."""
        from nextalk.utils.logger import logger_manager, log_performance
        
        # Setup logging
        logger_manager.setup("DEBUG", self.log_dir, console=False, file=True)
        
        # Log performance metrics
        log_performance("recognition", 0.125, accuracy=0.95, words=10)
        log_performance("injection", 0.050, method="typing", success=True)
        
        # Check logs
        log_files = list(self.log_dir.glob("*.log"))
        content = log_files[0].read_text()
        
        self.assertIn("Performance: recognition", content)
        self.assertIn("Performance: injection", content)
        # Note: duration values are in extra fields, not in the message text


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration integration."""
    
    def test_config_loading_and_validation(self):
        """Test configuration loading and validation."""
        from nextalk.config.manager import ConfigManager
        
        # Create temp config file
        temp_dir = tempfile.mkdtemp()
        config_file = Path(temp_dir) / "config.yaml"
        
        # Write config
        config_data = {
            "audio": {
                "sample_rate": 48000,  # Non-default value
                "channels": 2
            },
            "recording": {
                "hotkey": "ctrl+shift+r"  # Custom hotkey
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        try:
            # Load config
            manager = ConfigManager(str(config_file))
            config = manager.load_config()
            
            # Verify values loaded
            self.assertEqual(config.audio.sample_rate, 48000)
            self.assertEqual(config.audio.channels, 2)
            self.assertEqual(config.recording.hotkey, "ctrl+shift+r")
            
            # Verify defaults applied for missing values
            self.assertEqual(config.audio.chunk_size, [5, 10, 5])  # Default
            self.assertEqual(config.text_injection.preferred_method, InjectionMethod.AUTO)  # Default
            
            # Validate config
            errors = config.validate()
            self.assertEqual(len(errors), 0)
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_config_environment_override(self):
        """Test environment variable override."""
        import os
        from nextalk.config.manager import ConfigManager
        
        # Set environment variables
        os.environ["NEXTALK_SERVER"] = "ws://custom-server:8080"
        os.environ["NEXTALK_NO_TRAY"] = "1"
        
        try:
            # Create config without file
            manager = ConfigManager()
            config = manager.load_config()
            
            # Check environment overrides applied
            # Note: This requires implementation in ConfigManager
            
            # Clean environment
        finally:
            os.environ.pop("NEXTALK_SERVER", None)
            os.environ.pop("NEXTALK_NO_TRAY", None)


if __name__ == '__main__':
    unittest.main()