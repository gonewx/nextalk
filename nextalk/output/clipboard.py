"""
Clipboard management for NexTalk.

Provides clipboard operations for text injection fallback.
"""

import logging
import time
from typing import Optional
import pyperclip


logger = logging.getLogger(__name__)


class ClipboardManager:
    """
    Manages clipboard operations for text injection.
    
    Provides a fallback mechanism when direct text injection fails.
    """
    
    def __init__(self):
        """Initialize the clipboard manager."""
        self._original_content: Optional[str] = None
        self._preserve_original = True
    
    def copy_text(self, text: str) -> bool:
        """
        Copy text to clipboard.
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pyperclip.copy(text)
            logger.debug(f"Copied {len(text)} characters to clipboard")
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False
    
    def paste_text(self) -> Optional[str]:
        """
        Get text from clipboard.
        
        Returns:
            Text from clipboard, or None if failed
        """
        try:
            text = pyperclip.paste()
            return text
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}")
            return None
    
    def preserve_clipboard(self) -> None:
        """Save the current clipboard content for later restoration."""
        if self._preserve_original:
            try:
                self._original_content = pyperclip.paste()
                logger.debug("Preserved original clipboard content")
            except Exception as e:
                logger.warning(f"Could not preserve clipboard content: {e}")
                self._original_content = None
    
    def restore_clipboard(self) -> None:
        """Restore the previously saved clipboard content."""
        if self._preserve_original and self._original_content is not None:
            try:
                pyperclip.copy(self._original_content)
                logger.debug("Restored original clipboard content")
                self._original_content = None
            except Exception as e:
                logger.warning(f"Could not restore clipboard content: {e}")
    
    def clear_clipboard(self) -> None:
        """Clear the clipboard content."""
        try:
            pyperclip.copy("")
            logger.debug("Cleared clipboard")
        except Exception as e:
            logger.warning(f"Could not clear clipboard: {e}")
    
    def wait_for_clipboard_ready(self, timeout: float = 1.0) -> bool:
        """
        Wait for clipboard to be ready for operations.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if clipboard is ready, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to access clipboard
                _ = pyperclip.paste()
                return True
            except Exception:
                time.sleep(0.05)  # Wait 50ms before retry
        
        return False
    
    def inject_via_clipboard(self, text: str, paste_delay: float = 0.1) -> bool:
        """
        Inject text using clipboard and paste operation.
        
        Args:
            text: Text to inject
            paste_delay: Delay before pasting (seconds)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular dependency
            import pyautogui
            
            # Preserve original clipboard content
            self.preserve_clipboard()
            
            # Copy text to clipboard
            if not self.copy_text(text):
                return False
            
            # Small delay to ensure clipboard is ready
            time.sleep(paste_delay)
            
            # Paste using keyboard shortcut
            # Use platform-specific paste shortcut
            import platform
            if platform.system() == "Darwin":  # macOS
                pyautogui.hotkey("cmd", "v")
            else:  # Windows/Linux
                pyautogui.hotkey("ctrl", "v")
            
            logger.info(f"Injected {len(text)} characters via clipboard")
            
            # Restore original clipboard content after a delay
            # This is done in a non-blocking way
            import threading
            restore_thread = threading.Thread(
                target=lambda: (time.sleep(1.0), self.restore_clipboard())
            )
            restore_thread.daemon = True
            restore_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to inject via clipboard: {e}")
            # Try to restore clipboard on error
            self.restore_clipboard()
            return False
    
    def set_preserve_original(self, preserve: bool) -> None:
        """
        Set whether to preserve original clipboard content.
        
        Args:
            preserve: Whether to preserve original content
        """
        self._preserve_original = preserve
        logger.debug(f"Clipboard preservation set to: {preserve}")