"""
Unit tests for clipboard manager module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading

from nextalk.output.clipboard import ClipboardManager


class TestClipboardManager(unittest.TestCase):
    """Test cases for ClipboardManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ClipboardManager()
    
    @patch('nextalk.output.clipboard.pyperclip.copy')
    def test_copy_text(self, mock_copy):
        """Test copying text to clipboard."""
        test_text = "Hello, NexTalk!"
        
        # Test successful copy
        result = self.manager.copy_text(test_text)
        self.assertTrue(result)
        mock_copy.assert_called_once_with(test_text)
        
        # Test copy failure
        mock_copy.side_effect = Exception("Copy failed")
        result = self.manager.copy_text(test_text)
        self.assertFalse(result)
    
    @patch('nextalk.output.clipboard.pyperclip.paste')
    def test_paste_text(self, mock_paste):
        """Test getting text from clipboard."""
        test_text = "Clipboard content"
        mock_paste.return_value = test_text
        
        # Test successful paste
        result = self.manager.paste_text()
        self.assertEqual(result, test_text)
        mock_paste.assert_called_once()
        
        # Test paste failure
        mock_paste.side_effect = Exception("Paste failed")
        result = self.manager.paste_text()
        self.assertIsNone(result)
    
    @patch('nextalk.output.clipboard.pyperclip.paste')
    @patch('nextalk.output.clipboard.pyperclip.copy')
    def test_preserve_restore_clipboard(self, mock_copy, mock_paste):
        """Test preserving and restoring clipboard content."""
        original_content = "Original content"
        mock_paste.return_value = original_content
        
        # Preserve clipboard
        self.manager.preserve_clipboard()
        mock_paste.assert_called_once()
        
        # Restore clipboard
        self.manager.restore_clipboard()
        mock_copy.assert_called_with(original_content)
        
        # Test preserve with error
        mock_paste.reset_mock()
        mock_paste.side_effect = Exception("Cannot access clipboard")
        self.manager.preserve_clipboard()
        
        # Restore should not fail even if preserve failed
        mock_copy.reset_mock()
        self.manager.restore_clipboard()
        mock_copy.assert_not_called()  # Nothing to restore
    
    @patch('nextalk.output.clipboard.pyperclip.copy')
    def test_clear_clipboard(self, mock_copy):
        """Test clearing clipboard."""
        self.manager.clear_clipboard()
        mock_copy.assert_called_once_with("")
        
        # Test clear with error (should not raise)
        mock_copy.side_effect = Exception("Clear failed")
        self.manager.clear_clipboard()  # Should not raise
    
    @patch('nextalk.output.clipboard.pyperclip.paste')
    def test_wait_for_clipboard_ready(self, mock_paste):
        """Test waiting for clipboard to be ready."""
        # Test immediate success
        mock_paste.return_value = "test"
        result = self.manager.wait_for_clipboard_ready(timeout=1.0)
        self.assertTrue(result)
        
        # Test timeout
        mock_paste.side_effect = Exception("Not ready")
        result = self.manager.wait_for_clipboard_ready(timeout=0.1)
        self.assertFalse(result)
    
    @patch('nextalk.output.clipboard.pyautogui.hotkey')
    @patch('nextalk.output.clipboard.pyperclip.copy')
    @patch('nextalk.output.clipboard.pyperclip.paste')
    @patch('nextalk.output.clipboard.platform.system')
    def test_inject_via_clipboard(self, mock_system, mock_paste, mock_copy, mock_hotkey):
        """Test injecting text via clipboard."""
        test_text = "Text to inject"
        original_text = "Original clipboard"
        
        mock_paste.return_value = original_text
        mock_system.return_value = "Linux"  # Test Linux
        
        # Test successful injection
        result = self.manager.inject_via_clipboard(test_text, paste_delay=0.01)
        self.assertTrue(result)
        
        # Check that clipboard was preserved
        mock_paste.assert_called()
        
        # Check that text was copied
        mock_copy.assert_called_with(test_text)
        
        # Check that paste hotkey was pressed
        mock_hotkey.assert_called_with("ctrl", "v")
        
        # Test macOS
        mock_system.return_value = "Darwin"
        mock_hotkey.reset_mock()
        result = self.manager.inject_via_clipboard(test_text, paste_delay=0.01)
        self.assertTrue(result)
        mock_hotkey.assert_called_with("cmd", "v")
        
        # Test failure
        mock_copy.side_effect = Exception("Copy failed")
        result = self.manager.inject_via_clipboard(test_text)
        self.assertFalse(result)
    
    def test_set_preserve_original(self):
        """Test setting preserve original flag."""
        # Default should be True
        self.assertTrue(self.manager._preserve_original)
        
        # Set to False
        self.manager.set_preserve_original(False)
        self.assertFalse(self.manager._preserve_original)
        
        # Set back to True
        self.manager.set_preserve_original(True)
        self.assertTrue(self.manager._preserve_original)
    
    @patch('nextalk.output.clipboard.pyperclip.paste')
    @patch('nextalk.output.clipboard.pyperclip.copy')
    def test_preserve_disabled(self, mock_copy, mock_paste):
        """Test behavior when preserve is disabled."""
        self.manager.set_preserve_original(False)
        
        # Preserve should not access clipboard
        self.manager.preserve_clipboard()
        mock_paste.assert_not_called()
        
        # Restore should not do anything
        self.manager.restore_clipboard()
        mock_copy.assert_not_called()


if __name__ == '__main__':
    unittest.main()