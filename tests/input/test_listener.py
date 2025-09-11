"""
Unit tests for keyboard listener module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time
from pynput.keyboard import Key, KeyCode

from nextalk.input.listener import (
    KeyListener,
    HotkeyEvent,
    KeyEventType
)


class TestKeyListener(unittest.TestCase):
    """Test cases for KeyListener class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.listener = KeyListener()
    
    def tearDown(self):
        """Clean up after tests."""
        if self.listener.is_running():
            self.listener.stop()
    
    def test_initialization(self):
        """Test listener initialization."""
        self.assertIsNotNone(self.listener)
        self.assertFalse(self.listener.is_running())
        self.assertEqual(len(self.listener._registered_hotkeys), 0)
        self.assertEqual(len(self.listener._pressed_keys), 0)
        self.assertEqual(len(self.listener._pressed_modifiers), 0)
    
    @patch('nextalk.input.listener.keyboard.Listener')
    def test_start_stop(self, mock_listener_class):
        """Test starting and stopping the listener."""
        mock_listener = MagicMock()
        mock_listener_class.return_value = mock_listener
        
        # Start listener
        self.listener.start()
        self.assertTrue(self.listener.is_running())
        mock_listener.start.assert_called_once()
        
        # Try starting again (should warn but not error)
        self.listener.start()
        self.assertTrue(self.listener.is_running())
        
        # Stop listener
        self.listener.stop()
        self.assertFalse(self.listener.is_running())
        mock_listener.stop.assert_called_once()
        
        # Stop again (should be idempotent)
        self.listener.stop()
        self.assertFalse(self.listener.is_running())
    
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
            result = self.listener._normalize_hotkey(input_key)
            self.assertEqual(result, expected)
    
    def test_register_unregister_hotkey(self):
        """Test hotkey registration and unregistration."""
        callback = Mock()
        hotkey = "ctrl+alt+space"
        
        # Register hotkey
        self.listener.register_hotkey(hotkey, callback)
        normalized = self.listener._normalize_hotkey(hotkey)
        self.assertIn(normalized, self.listener._registered_hotkeys)
        
        # Unregister hotkey
        self.listener.unregister_hotkey(hotkey)
        self.assertNotIn(normalized, self.listener._registered_hotkeys)
    
    def test_callback_management(self):
        """Test callback addition and removal."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        self.listener.add_callback(callback1)
        self.listener.add_callback(callback2)
        self.assertEqual(len(self.listener._callbacks), 2)
        
        # Remove callback
        self.listener.remove_callback(callback1)
        self.assertEqual(len(self.listener._callbacks), 1)
        self.assertIn(callback2, self.listener._callbacks)
        
        # Remove non-existent callback (should not error)
        self.listener.remove_callback(callback1)
        self.assertEqual(len(self.listener._callbacks), 1)
    
    def test_get_key_name(self):
        """Test key name extraction."""
        test_cases = [
            (Key.ctrl_l, "ctrl"),
            (Key.ctrl_r, "ctrl"),
            (Key.alt_l, "alt"),
            (Key.shift_l, "shift"),
            (Key.space, "space"),
            (Key.enter, "enter"),
            (Key.f1, "f1"),
            (KeyCode(char='a'), "a"),
            (KeyCode(char='A'), "a"),  # Should be lowercase
            (KeyCode(char='1'), "1"),
        ]
        
        for key, expected in test_cases:
            result = self.listener._get_key_name(key)
            self.assertEqual(result, expected)
    
    def test_modifier_state_tracking(self):
        """Test modifier key state tracking."""
        # Set running state for testing
        self.listener._running = True
        
        # Simulate pressing ctrl
        self.listener._on_press(Key.ctrl_l)
        self.assertIn("ctrl", self.listener._pressed_modifiers)
        
        # Simulate pressing alt
        self.listener._on_press(Key.alt_l)
        self.assertIn("alt", self.listener._pressed_modifiers)
        
        # Simulate releasing ctrl
        self.listener._on_release(Key.ctrl_l)
        self.assertNotIn("ctrl", self.listener._pressed_modifiers)
        self.assertIn("alt", self.listener._pressed_modifiers)
        
        # Simulate releasing alt
        self.listener._on_release(Key.alt_l)
        self.assertEqual(len(self.listener._pressed_modifiers), 0)
    
    def test_regular_key_tracking(self):
        """Test regular key state tracking."""
        # Set running state for testing
        self.listener._running = True
        
        # Simulate pressing 'a'
        self.listener._on_press(KeyCode(char='a'))
        self.assertIn("a", self.listener._pressed_keys)
        
        # Simulate pressing 'b'
        self.listener._on_press(KeyCode(char='b'))
        self.assertIn("a", self.listener._pressed_keys)
        self.assertIn("b", self.listener._pressed_keys)
        
        # Simulate releasing 'a'
        self.listener._on_release(KeyCode(char='a'))
        self.assertNotIn("a", self.listener._pressed_keys)
        self.assertIn("b", self.listener._pressed_keys)
    
    def test_build_current_combo(self):
        """Test building current key combination."""
        # Set running state for testing
        self.listener._running = True
        
        # No modifiers, just key
        self.listener._pressed_keys.add("space")
        combo = self.listener._build_current_combo("space")
        self.assertEqual(combo, "space")
        
        # With modifiers
        self.listener._pressed_modifiers.add("ctrl")
        self.listener._pressed_modifiers.add("alt")
        combo = self.listener._build_current_combo("space")
        self.assertEqual(combo, "alt+ctrl+space")
        
        # Modifier-only press should return None
        combo = self.listener._build_current_combo("ctrl")
        self.assertIsNone(combo)
        
        # Key not in pressed keys
        self.listener._pressed_keys.clear()
        self.listener._pressed_modifiers.clear()
        combo = self.listener._build_current_combo("space")
        self.assertEqual(combo, "space")  # No modifiers, just the key
    
    @patch('time.time')
    def test_hotkey_triggered(self, mock_time):
        """Test hotkey triggering."""
        mock_time.return_value = 1234567890.0
        
        callback = Mock()
        event_callback = Mock()
        
        self.listener.register_hotkey("ctrl+alt+space", callback)
        self.listener.add_callback(event_callback)
        
        # Simulate hotkey press
        self.listener._pressed_modifiers.add("ctrl")
        self.listener._pressed_modifiers.add("alt")
        self.listener._pressed_keys.add("space")
        
        self.listener._check_hotkey_triggered("space", KeyEventType.PRESS)
        
        # Verify callbacks were called
        callback.assert_called_once()
        event_callback.assert_called_once()
        
        # Check event structure
        event = event_callback.call_args[0][0]
        self.assertIsInstance(event, HotkeyEvent)
        self.assertEqual(event.hotkey, "alt+ctrl+space")
        self.assertEqual(event.event_type, KeyEventType.PRESS)
        self.assertEqual(event.timestamp, 1234567890.0)
        self.assertEqual(event.modifiers, {"ctrl", "alt"})
        self.assertEqual(event.key, "space")
    
    def test_get_pressed_keys(self):
        """Test getting currently pressed keys."""
        self.listener._pressed_keys.add("a")
        self.listener._pressed_keys.add("b")
        
        keys = self.listener.get_pressed_keys()
        self.assertEqual(keys, {"a", "b"})
        
        # Ensure it returns a copy
        keys.add("c")
        self.assertNotIn("c", self.listener._pressed_keys)
    
    def test_get_pressed_modifiers(self):
        """Test getting currently pressed modifiers."""
        self.listener._pressed_modifiers.add("ctrl")
        self.listener._pressed_modifiers.add("shift")
        
        modifiers = self.listener.get_pressed_modifiers()
        self.assertEqual(modifiers, {"ctrl", "shift"})
        
        # Ensure it returns a copy
        modifiers.add("alt")
        self.assertNotIn("alt", self.listener._pressed_modifiers)


class TestHotkeyEvent(unittest.TestCase):
    """Test cases for HotkeyEvent dataclass."""
    
    def test_hotkey_event_creation(self):
        """Test creating a HotkeyEvent."""
        event = HotkeyEvent(
            hotkey="ctrl+alt+space",
            event_type=KeyEventType.PRESS,
            timestamp=1234567890.0,
            modifiers={"ctrl", "alt"},
            key="space"
        )
        
        self.assertEqual(event.hotkey, "ctrl+alt+space")
        self.assertEqual(event.event_type, KeyEventType.PRESS)
        self.assertEqual(event.timestamp, 1234567890.0)
        self.assertEqual(event.modifiers, {"ctrl", "alt"})
        self.assertEqual(event.key, "space")


class TestKeyEventType(unittest.TestCase):
    """Test cases for KeyEventType enum."""
    
    def test_event_types(self):
        """Test event type enum values."""
        self.assertEqual(KeyEventType.PRESS.value, "press")
        self.assertEqual(KeyEventType.RELEASE.value, "release")


if __name__ == '__main__':
    unittest.main()