"""
Unit tests for hotkey manager module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import time
import threading

from nextalk.input.hotkey import (
    HotkeyManager,
    HotkeyRegistration,
    HotkeyConflictError
)
from nextalk.input.listener import HotkeyEvent, KeyEventType
from nextalk.config.models import HotkeyConfig


class TestHotkeyManager(unittest.TestCase):
    """Test cases for HotkeyManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        hotkey_config = HotkeyConfig(
            trigger_key="ctrl+alt+space",
            stop_key="ctrl+alt+space",
            conflict_detection=True,
            enable_sound_feedback=False
        )
        self.config = hotkey_config.to_recording_config()
        self.manager = HotkeyManager(self.config)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.manager.is_running():
            self.manager.stop()
    
    def test_initialization(self):
        """Test manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertEqual(self.manager.config, self.config)
        self.assertFalse(self.manager.is_running())
        self.assertEqual(len(self.manager._registrations), 0)
    
    @patch('nextalk.input.hotkey.KeyListener')
    def test_start_stop(self, mock_listener_class):
        """Test starting and stopping the manager."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        # Create new manager with mocked listener
        manager = HotkeyManager(self.config)
        manager._listener = mock_listener
        
        # Start manager
        manager.start()
        self.assertTrue(manager.is_running())
        mock_listener.start.assert_called_once()
        
        # Try starting again (should warn but not error)
        manager.start()
        self.assertTrue(manager.is_running())
        
        # Stop manager
        manager.stop()
        self.assertFalse(manager.is_running())
        mock_listener.stop.assert_called_once()
        
        # Stop again (should be idempotent)
        manager.stop()
        self.assertFalse(manager.is_running())
    
    def test_register_hotkey(self):
        """Test hotkey registration."""
        callback = Mock()
        hotkey = "ctrl+shift+f1"
        description = "Test hotkey"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register hotkey
        self.manager.register(hotkey, callback, description)
        
        # Check registration stored
        normalized = self.manager._normalize_hotkey(hotkey)
        self.assertIn(normalized, self.manager._registrations)
        
        registration = self.manager._registrations[normalized]
        self.assertEqual(registration.hotkey, normalized)
        self.assertEqual(registration.callback, callback)
        self.assertEqual(registration.description, description)
        self.assertTrue(registration.enabled)
        
        # Check listener was called
        self.manager._listener.register_hotkey.assert_called_once()
    
    def test_register_conflict_detection(self):
        """Test hotkey conflict detection."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register first hotkey
        self.manager.register("ctrl+alt+a", callback1, "First hotkey")
        
        # Try registering conflicting hotkey
        with self.assertRaises(HotkeyConflictError):
            self.manager.register("ctrl+alt+a", callback2, "Conflicting hotkey")
        
        # Register without conflict check should work
        self.manager.register("ctrl+alt+a", callback2, "Override", check_conflicts=False)
    
    def test_unregister_hotkey(self):
        """Test hotkey unregistration."""
        callback = Mock()
        hotkey = "ctrl+alt+b"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        self.manager._listener.unregister_hotkey = Mock()
        
        # Register hotkey
        self.manager.register(hotkey, callback)
        normalized = self.manager._normalize_hotkey(hotkey)
        self.assertIn(normalized, self.manager._registrations)
        
        # Unregister hotkey
        self.manager.unregister(hotkey)
        self.assertNotIn(normalized, self.manager._registrations)
        self.manager._listener.unregister_hotkey.assert_called_with(normalized)
    
    def test_set_enabled(self):
        """Test enabling/disabling hotkeys."""
        callback = Mock()
        hotkey = "ctrl+alt+c"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register hotkey
        self.manager.register(hotkey, callback)
        normalized = self.manager._normalize_hotkey(hotkey)
        
        # Check initially enabled
        self.assertTrue(self.manager._registrations[normalized].enabled)
        
        # Disable hotkey
        self.manager.set_enabled(hotkey, False)
        self.assertFalse(self.manager._registrations[normalized].enabled)
        
        # Enable hotkey
        self.manager.set_enabled(hotkey, True)
        self.assertTrue(self.manager._registrations[normalized].enabled)
    
    def test_is_registered(self):
        """Test checking if hotkey is registered."""
        callback = Mock()
        hotkey = "ctrl+alt+d"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Check not registered
        self.assertFalse(self.manager.is_registered(hotkey))
        
        # Register and check
        self.manager.register(hotkey, callback)
        self.assertTrue(self.manager.is_registered(hotkey))
        
        # Check with different case (should still work)
        self.assertTrue(self.manager.is_registered("CTRL+ALT+D"))
    
    def test_normalize_hotkey(self):
        """Test hotkey normalization."""
        test_cases = [
            ("ctrl+alt+space", "alt+ctrl+space"),
            ("CTRL+ALT+SPACE", "alt+ctrl+space"),
            ("shift+ctrl+a", "ctrl+shift+a"),
            ("meta+c", "cmd+c"),  # meta normalized to cmd
            ("space", "space"),
            ("ctrl+shift+alt+f1", "alt+ctrl+shift+f1"),
        ]
        
        for input_key, expected in test_cases:
            result = self.manager._normalize_hotkey(input_key)
            self.assertEqual(result, expected)
    
    def test_validate_hotkey(self):
        """Test hotkey validation."""
        # Valid hotkeys
        valid_hotkeys = [
            "ctrl+alt+space",
            "shift+f1",
            "ctrl+shift+alt+a",
            "cmd+c",
            "space",
        ]
        
        for hotkey in valid_hotkeys:
            errors = self.manager.validate_hotkey(hotkey)
            self.assertEqual(len(errors), 0, f"Hotkey '{hotkey}' should be valid")
        
        # Invalid hotkeys
        invalid_hotkeys = [
            ("", ["Hotkey cannot be empty"]),
            ("ctrl+alt", ["Hotkey must include at least one non-modifier key"]),
            ("ctrl+ctrl+a", ["Duplicate modifier keys"]),
            ("ctrl+invalid_key", ["Invalid key: invalid_key"]),
        ]
        
        for hotkey, expected_errors in invalid_hotkeys:
            errors = self.manager.validate_hotkey(hotkey)
            self.assertTrue(len(errors) > 0, f"Hotkey '{hotkey}' should be invalid")
            for expected_error in expected_errors:
                self.assertTrue(
                    any(expected_error in error for error in errors),
                    f"Expected error '{expected_error}' not found in {errors}"
                )
    
    @patch('time.time')
    def test_trigger_hotkey(self, mock_time):
        """Test hotkey triggering."""
        mock_time.return_value = 1.0
        
        callback = Mock()
        hotkey = "ctrl+alt+e"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register hotkey
        self.manager.register(hotkey, callback, "Test trigger")
        normalized = self.manager._normalize_hotkey(hotkey)
        
        # Trigger hotkey
        self.manager._trigger_hotkey(normalized)
        
        # Check callback was called
        callback.assert_called_once()
        
        # Check registration updated
        registration = self.manager._registrations[normalized]
        self.assertEqual(registration.trigger_count, 1)
        self.assertEqual(registration.last_triggered, 1.0)
    
    @patch('time.time')
    def test_trigger_cooldown(self, mock_time):
        """Test hotkey trigger cooldown."""
        # First trigger at t=0
        mock_time.return_value = 0.0
        
        callback = Mock()
        hotkey = "ctrl+alt+f"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register hotkey
        self.manager.register(hotkey, callback)
        normalized = self.manager._normalize_hotkey(hotkey)
        
        # First trigger should work
        self.manager._trigger_hotkey(normalized)
        self.assertEqual(callback.call_count, 1)
        
        # Second trigger too soon (within 200ms cooldown)
        mock_time.return_value = 0.1  # 100ms later
        self.manager._trigger_hotkey(normalized)
        self.assertEqual(callback.call_count, 1)  # Still 1, not triggered
        
        # Third trigger after cooldown
        mock_time.return_value = 0.3  # 300ms later
        self.manager._trigger_hotkey(normalized)
        self.assertEqual(callback.call_count, 2)  # Now triggered
    
    def test_trigger_disabled_hotkey(self):
        """Test triggering a disabled hotkey."""
        callback = Mock()
        hotkey = "ctrl+alt+g"
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register and disable hotkey
        self.manager.register(hotkey, callback)
        self.manager.set_enabled(hotkey, False)
        
        normalized = self.manager._normalize_hotkey(hotkey)
        
        # Try to trigger disabled hotkey
        self.manager._trigger_hotkey(normalized)
        
        # Callback should not be called
        callback.assert_not_called()
    
    def test_get_registrations(self):
        """Test getting all registrations."""
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register multiple hotkeys
        self.manager.register("ctrl+a", Mock(), "Hotkey A")
        self.manager.register("ctrl+b", Mock(), "Hotkey B")
        self.manager.register("ctrl+c", Mock(), "Hotkey C")
        
        registrations = self.manager.get_registrations()
        self.assertEqual(len(registrations), 3)
        
        descriptions = [r.description for r in registrations]
        self.assertIn("Hotkey A", descriptions)
        self.assertIn("Hotkey B", descriptions)
        self.assertIn("Hotkey C", descriptions)
    
    @patch('time.time')
    def test_get_statistics(self, mock_time):
        """Test getting hotkey statistics."""
        mock_time.return_value = 1.0
        
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register hotkeys
        self.manager.register("ctrl+a", Mock(), "Hotkey A")
        self.manager.register("ctrl+b", Mock(), "Hotkey B")
        
        # Trigger one hotkey
        self.manager._trigger_hotkey("ctrl+a")
        
        stats = self.manager.get_statistics()
        
        self.assertIn("ctrl+a", stats)
        self.assertIn("ctrl+b", stats)
        
        self.assertEqual(stats["ctrl+a"]["trigger_count"], 1)
        self.assertEqual(stats["ctrl+a"]["last_triggered"], 1.0)
        self.assertEqual(stats["ctrl+b"]["trigger_count"], 0)
        self.assertIsNone(stats["ctrl+b"]["last_triggered"])
    
    def test_check_conflicts(self):
        """Test conflict checking logic."""
        # Mock the listener
        self.manager._listener.register_hotkey = Mock()
        
        # Register a hotkey
        self.manager.register("ctrl+alt+x", Mock(), "Existing hotkey")
        
        # Check exact conflict
        conflicts = self.manager._check_conflicts("alt+ctrl+x")  # Different order, same combo
        self.assertEqual(len(conflicts), 1)
        
        # Check no conflict
        conflicts = self.manager._check_conflicts("ctrl+alt+y")
        self.assertEqual(len(conflicts), 0)
    
    def test_on_hotkey_event(self):
        """Test hotkey event handler."""
        event = HotkeyEvent(
            hotkey="ctrl+alt+space",
            event_type=KeyEventType.PRESS,
            timestamp=1234567890.0,
            modifiers={"ctrl", "alt"},
            key="space"
        )
        
        # Should not raise any exceptions
        self.manager._on_hotkey_event(event)
    
    @patch('nextalk.input.hotkey.logger')
    def test_play_feedback_sound(self, mock_logger):
        """Test feedback sound placeholder."""
        self.manager._play_feedback_sound()
        mock_logger.debug.assert_called_with("Playing feedback sound (not implemented)")


class TestHotkeyRegistration(unittest.TestCase):
    """Test cases for HotkeyRegistration dataclass."""
    
    def test_registration_creation(self):
        """Test creating a HotkeyRegistration."""
        callback = Mock()
        
        registration = HotkeyRegistration(
            hotkey="ctrl+alt+space",
            callback=callback,
            description="Test hotkey"
        )
        
        self.assertEqual(registration.hotkey, "ctrl+alt+space")
        self.assertEqual(registration.callback, callback)
        self.assertEqual(registration.description, "Test hotkey")
        self.assertTrue(registration.enabled)
        self.assertIsNone(registration.last_triggered)
        self.assertEqual(registration.trigger_count, 0)
    
    def test_registration_defaults(self):
        """Test default values in HotkeyRegistration."""
        callback = Mock()
        
        registration = HotkeyRegistration(
            hotkey="ctrl+a",
            callback=callback,
            description="Test"
        )
        
        self.assertTrue(registration.enabled)
        self.assertIsNone(registration.last_triggered)
        self.assertEqual(registration.trigger_count, 0)


class TestHotkeyConflictError(unittest.TestCase):
    """Test cases for HotkeyConflictError exception."""
    
    def test_conflict_error(self):
        """Test HotkeyConflictError exception."""
        error = HotkeyConflictError("Test conflict")
        self.assertEqual(str(error), "Test conflict")
        self.assertIsInstance(error, Exception)


if __name__ == '__main__':
    unittest.main()