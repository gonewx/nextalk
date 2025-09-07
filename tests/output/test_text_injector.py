"""
Unit tests for text injector module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import platform

from nextalk.output.text_injector import (
    TextInjector,
    InjectionMethod
)
from nextalk.config.models import TextInjectionConfig


class TestTextInjector(unittest.TestCase):
    """Test cases for TextInjector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TextInjectionConfig(
            auto_inject=True,
            fallback_to_clipboard=True,
            inject_delay=0.01,
            cursor_positioning="end",
            format_text=True,
            strip_whitespace=True
        )
        self.injector = TextInjector(self.config)
    
    def test_initialization(self):
        """Test injector initialization."""
        self.assertIsNotNone(self.injector)
        self.assertEqual(self.injector.config, self.config)
        self.assertIsNotNone(self.injector.clipboard)
        self.assertEqual(self.injector.platform, platform.system())
    
    @patch('nextalk.output.text_injector.pyautogui.typewrite')
    def test_inject_by_typing(self, mock_typewrite):
        """Test injection by typing."""
        test_text = "Hello, World!"
        
        # Test successful typing
        result = self.injector._inject_by_typing(test_text)
        self.assertTrue(result)
        mock_typewrite.assert_called_once_with(test_text, interval=0.001)
        
        # Test typing failure
        mock_typewrite.side_effect = Exception("Typing failed")
        result = self.injector._inject_by_typing(test_text)
        self.assertFalse(result)
    
    @patch.object(TextInjector, '_inject_by_typing')
    @patch.object(TextInjector, 'get_active_window_info')
    def test_inject_text_typing(self, mock_get_window, mock_typing):
        """Test text injection with typing method."""
        test_text = "  Test text  "
        mock_get_window.return_value = (None, "TestApp")
        mock_typing.return_value = True
        
        result = self.injector.inject_text(
            test_text,
            method=InjectionMethod.TYPING
        )
        
        self.assertTrue(result)
        # Text should be stripped due to config
        mock_typing.assert_called_once()
        called_text = mock_typing.call_args[0][0]
        self.assertEqual(called_text, "Test text")
    
    @patch.object(TextInjector, '_inject_by_clipboard')
    def test_inject_text_clipboard(self, mock_clipboard):
        """Test text injection with clipboard method."""
        test_text = "Test text"
        mock_clipboard.return_value = True
        
        result = self.injector.inject_text(
            test_text,
            method=InjectionMethod.CLIPBOARD
        )
        
        self.assertTrue(result)
        mock_clipboard.assert_called_once()
    
    @patch.object(TextInjector, '_inject_by_typing')
    @patch.object(TextInjector, '_inject_by_clipboard')
    def test_inject_text_hybrid(self, mock_clipboard, mock_typing):
        """Test text injection with hybrid method."""
        test_text = "Test text"
        
        # Test successful typing (no fallback needed)
        mock_typing.return_value = True
        mock_clipboard.return_value = True
        
        result = self.injector.inject_text(
            test_text,
            method=InjectionMethod.HYBRID
        )
        
        self.assertTrue(result)
        mock_typing.assert_called_once()
        mock_clipboard.assert_not_called()
        
        # Test typing failure with fallback
        mock_typing.reset_mock()
        mock_clipboard.reset_mock()
        mock_typing.return_value = False
        
        result = self.injector.inject_text(
            test_text,
            method=InjectionMethod.HYBRID
        )
        
        self.assertTrue(result)
        mock_typing.assert_called_once()
        mock_clipboard.assert_called_once()
    
    def test_inject_empty_text(self):
        """Test injecting empty text."""
        result = self.injector.inject_text("")
        self.assertTrue(result)  # Empty text returns True (nothing to do)
    
    def test_format_text(self):
        """Test text formatting."""
        test_cases = [
            ("Hello  World", "Hello World"),  # Double space
            ("Test..", "Test."),  # Double punctuation
            ("Hi , there", "Hi, there"),  # Space before comma
        ]
        
        for input_text, expected in test_cases:
            result = self.injector._format_text(input_text)
            self.assertEqual(result, expected)
    
    @patch('nextalk.output.text_injector.pyautogui.hotkey')
    def test_position_cursor(self, mock_hotkey):
        """Test cursor positioning after injection."""
        test_text = "Test"
        
        # Test "start" positioning on Linux
        self.injector.is_macos = False
        self.injector.config.cursor_positioning = "start"
        self.injector._position_cursor(test_text)
        mock_hotkey.assert_called_with("home")
        
        # Test "start" positioning on macOS
        mock_hotkey.reset_mock()
        self.injector.is_macos = True
        self.injector._position_cursor(test_text)
        mock_hotkey.assert_called_with("cmd", "left")
        
        # Test "select" positioning
        mock_hotkey.reset_mock()
        self.injector.config.cursor_positioning = "select"
        self.injector._position_cursor(test_text)
        mock_hotkey.assert_called_with("cmd", "a")
        
        # Test "end" positioning (default, no action)
        mock_hotkey.reset_mock()
        self.injector.config.cursor_positioning = "end"
        self.injector._position_cursor(test_text)
        mock_hotkey.assert_not_called()
    
    def test_detect_best_method(self):
        """Test auto-detection of best injection method."""
        # Test with auto_inject disabled
        self.injector.config.auto_inject = False
        method = self.injector._detect_best_method("TestApp")
        self.assertEqual(method, InjectionMethod.CLIPBOARD)
        
        # Test with compatible app
        self.injector.config.auto_inject = True
        self.injector.config.compatible_apps = ["TestApp"]
        method = self.injector._detect_best_method("TestApp")
        self.assertEqual(method, InjectionMethod.TYPING)
        
        # Test with incompatible app
        self.injector.config.compatible_apps = []
        self.injector.config.incompatible_apps = ["BadApp"]
        method = self.injector._detect_best_method("BadApp")
        self.assertEqual(method, InjectionMethod.CLIPBOARD)
        
        # Test default
        method = self.injector._detect_best_method("UnknownApp")
        self.assertEqual(method, InjectionMethod.HYBRID)
    
    def test_is_app_compatible(self):
        """Test application compatibility checking."""
        # Test incompatible app
        self.injector.config.incompatible_apps = ["BadApp"]
        self.assertFalse(self.injector._is_app_compatible("BadApp"))
        
        # Test compatible app
        self.injector.config.compatible_apps = ["GoodApp"]
        self.injector.config.incompatible_apps = []
        self.assertTrue(self.injector._is_app_compatible("GoodApp"))
        
        # Test unknown app with no lists
        self.injector.config.compatible_apps = []
        self.injector.config.incompatible_apps = []
        self.assertTrue(self.injector._is_app_compatible("UnknownApp"))
        
        # Test caching
        self.injector._app_cache.clear()
        self.injector._is_app_compatible("CachedApp")
        self.assertIn("CachedApp", self.injector._app_cache)
    
    def test_load_app_profiles(self):
        """Test loading application profiles."""
        profiles = self.injector._load_app_profiles()
        
        # Check that profiles exist
        self.assertIn("terminal", profiles)
        self.assertIn("ide", profiles)
        self.assertIn("browser", profiles)
        self.assertIn("office", profiles)
        self.assertIn("chat", profiles)
        
        # Check profile structure
        terminal_profile = profiles["terminal"]
        self.assertIn("apps", terminal_profile)
        self.assertIn("method", terminal_profile)
        self.assertIn("special_handling", terminal_profile)
    
    def test_init_special_chars_map(self):
        """Test special character mapping initialization."""
        # Test Windows
        self.injector.is_windows = True
        char_map = self.injector._init_special_chars_map()
        self.assertIn("<", char_map)
        self.assertIn(">", char_map)
        
        # Test non-Windows
        self.injector.is_windows = False
        char_map = self.injector._init_special_chars_map()
        self.assertEqual(char_map, {})
    
    def test_escape_special_chars(self):
        """Test special character escaping."""
        # Test terminal escaping on Windows
        self.injector.is_windows = True
        text = "echo ^test & dir"
        result = self.injector._escape_special_chars(text, "terminal")
        self.assertEqual(result, "echo ^^test ^& dir")
        
        # Test terminal escaping on Unix
        self.injector.is_windows = False
        text = "echo $HOME"
        result = self.injector._escape_special_chars(text, "terminal")
        self.assertEqual(result, "echo \\$HOME")
        
        # Test general escaping
        self.injector.is_windows = True
        self.injector._special_chars_map = {"<": "{<}"}
        text = "a < b"
        result = self.injector._escape_special_chars(text, None)
        self.assertEqual(result, "a {<} b")
    
    def test_detect_app_type(self):
        """Test application type detection."""
        # Test terminal detection
        app_type = self.injector._detect_app_type("Terminal")
        self.assertEqual(app_type, "terminal")
        
        # Test IDE detection
        app_type = self.injector._detect_app_type("VSCode")
        self.assertEqual(app_type, "ide")
        
        # Test browser detection
        app_type = self.injector._detect_app_type("Chrome")
        self.assertEqual(app_type, "browser")
        
        # Test unknown app
        app_type = self.injector._detect_app_type("UnknownApp")
        self.assertIsNone(app_type)
        
        # Test None input
        app_type = self.injector._detect_app_type(None)
        self.assertIsNone(app_type)
    
    def test_contains_cjk(self):
        """Test CJK character detection."""
        # Test Chinese
        self.assertTrue(self.injector._contains_cjk("你好"))
        
        # Test Japanese
        self.assertTrue(self.injector._contains_cjk("こんにちは"))
        
        # Test Korean
        self.assertTrue(self.injector._contains_cjk("안녕하세요"))
        
        # Test English
        self.assertFalse(self.injector._contains_cjk("Hello"))
        
        # Test mixed
        self.assertTrue(self.injector._contains_cjk("Hello 你好"))
    
    @patch('nextalk.output.text_injector.pyautogui.click')
    @patch('nextalk.output.text_injector.pyautogui.position')
    def test_ensure_focus(self, mock_position, mock_click):
        """Test ensuring window focus."""
        mock_position.return_value = (100, 200)
        
        self.injector._ensure_focus()
        
        mock_position.assert_called_once()
        mock_click.assert_called_once_with(100, 200)
    
    @patch.object(TextInjector, '_ensure_focus')
    @patch.object(TextInjector, '_escape_special_chars')
    @patch.object(TextInjector, 'clipboard')
    def test_handle_app_specific_injection_terminal(
        self, mock_clipboard, mock_escape, mock_focus
    ):
        """Test terminal-specific injection handling."""
        test_text = "ls -la"
        mock_escape.return_value = "ls -la"
        mock_clipboard.inject_via_clipboard.return_value = True
        
        result = self.injector._handle_app_specific_injection(
            test_text, "Terminal", "terminal"
        )
        
        self.assertTrue(result)
        mock_focus.assert_called_once()
        mock_escape.assert_called_once_with(test_text, "terminal")
        mock_clipboard.inject_via_clipboard.assert_called_once()
    
    @patch('nextalk.output.text_injector.pyautogui.press')
    def test_handle_app_specific_injection_ide(self, mock_press):
        """Test IDE-specific injection handling."""
        test_text = "print('hello')"
        
        result = self.injector._handle_app_specific_injection(
            test_text, "VSCode", "ide"
        )
        
        self.assertFalse(result)  # Should use default method
        mock_press.assert_called_once_with("escape")
    
    @patch('nextalk.output.text_injector.pyperclip.paste')
    @patch('nextalk.output.text_injector.pyautogui.hotkey')
    def test_verify_injection(self, mock_hotkey, mock_paste):
        """Test injection verification."""
        original_text = "Test text"
        mock_paste.return_value = "Some text before Test text and after"
        
        # Test successful verification
        result = self.injector._verify_injection(original_text, timeout=0.1)
        self.assertTrue(result)
        
        # Test failed verification
        mock_paste.return_value = "Different text"
        result = self.injector._verify_injection(original_text, timeout=0.1)
        self.assertFalse(result)
        
        # Test verification error
        mock_paste.side_effect = Exception("Paste failed")
        result = self.injector._verify_injection(original_text, timeout=0.1)
        self.assertFalse(result)
    
    def test_get_compatibility_report(self):
        """Test compatibility report generation."""
        # Add some data to cache
        self.injector._app_cache["App1"] = True
        self.injector._app_cache["App2"] = False
        
        report = self.injector.get_compatibility_report()
        
        self.assertIn("platform", report)
        self.assertIn("app_cache", report)
        self.assertIn("known_profiles", report)
        self.assertIn("injection_stats", report)
        
        stats = report["injection_stats"]
        self.assertEqual(stats["cached_apps"], 2)
        self.assertEqual(stats["compatible"], 1)
        self.assertEqual(stats["incompatible"], 1)
    
    def test_clear_statistics(self):
        """Test clearing statistics."""
        # Add data to cache
        self.injector._app_cache["App1"] = True
        self.injector._app_cache["App2"] = False
        
        self.injector.clear_statistics()
        
        self.assertEqual(len(self.injector._app_cache), 0)
    
    @patch.object(TextInjector, 'inject_text')
    def test_test_injection(self, mock_inject):
        """Test the test injection method."""
        mock_inject.return_value = True
        
        result = self.injector.test_injection()
        self.assertTrue(result)
        
        mock_inject.assert_called_once_with(
            "NexTalk injection test",
            method=InjectionMethod.HYBRID
        )
        
        # Test failure
        mock_inject.return_value = False
        result = self.injector.test_injection()
        self.assertFalse(result)


class TestInjectionMethod(unittest.TestCase):
    """Test cases for InjectionMethod enum."""
    
    def test_injection_methods(self):
        """Test injection method enum values."""
        self.assertEqual(InjectionMethod.TYPING.value, "typing")
        self.assertEqual(InjectionMethod.CLIPBOARD.value, "clipboard")
        self.assertEqual(InjectionMethod.HYBRID.value, "hybrid")


if __name__ == '__main__':
    unittest.main()