"""
Text injection module for NexTalk.

Provides automatic text injection to target applications.
"""

import logging
import time
import platform
import subprocess
from enum import Enum
from typing import Optional, List, Tuple, Dict
import pyautogui
import pyperclip
import re

from ..config.models import TextInjectionConfig
from .clipboard import ClipboardManager


logger = logging.getLogger(__name__)


class InjectionMethod(Enum):
    """Text injection methods."""
    TYPING = "typing"  # Simulate keyboard typing
    CLIPBOARD = "clipboard"  # Use clipboard and paste
    HYBRID = "hybrid"  # Try typing first, fallback to clipboard


class TextInjector:
    """
    Manages text injection to target applications.
    
    Provides multiple injection methods with fallback mechanisms.
    """
    
    def __init__(self, config: Optional[TextInjectionConfig] = None):
        """
        Initialize the text injector.
        
        Args:
            config: Text injection configuration
        """
        self.config = config or TextInjectionConfig()
        self.clipboard = ClipboardManager()
        
        # Configure pyautogui
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.01  # Small pause between actions
        
        # Platform detection
        self.platform = platform.system()
        self.is_windows = self.platform == "Windows"
        self.is_macos = self.platform == "Darwin"
        self.is_linux = self.platform == "Linux"
        
        # Application detection cache
        self._app_cache: dict[str, bool] = {}
        
        # Known application compatibility profiles
        self._app_profiles = self._load_app_profiles()
        
        # Special character handling
        self._special_chars_map = self._init_special_chars_map()
    
    def inject_text(
        self,
        text: str,
        method: Optional[InjectionMethod] = None,
        app_name: Optional[str] = None
    ) -> bool:
        """
        Inject text to the current cursor position.
        
        Args:
            text: Text to inject
            method: Injection method to use (None for auto-detect)
            app_name: Name of target application (for compatibility check)
            
        Returns:
            True if successful, False otherwise
        """
        if not text:
            logger.warning("Empty text, nothing to inject")
            return True
        
        # Get active window info if not provided
        if not app_name:
            _, app_name = self.get_active_window_info()
        
        # Detect application type
        app_type = self._detect_app_type(app_name)
        logger.debug(f"Detected app type: {app_type} for {app_name}")
        
        # Pre-process text if configured
        if self.config.format_text:
            text = self._format_text(text)
        
        if self.config.strip_whitespace:
            text = text.strip()
        
        # Handle IME compatibility
        text = self._handle_ime_compatibility(text)
        
        # Check application compatibility
        if app_name and not self._is_app_compatible(app_name):
            logger.info(f"App {app_name} is incompatible, using clipboard")
            method = InjectionMethod.CLIPBOARD
        
        # Auto-detect method if not specified
        if method is None:
            method = self._detect_best_method(app_name)
        
        # Apply injection delay
        if self.config.inject_delay > 0:
            time.sleep(self.config.inject_delay)
        
        # Try app-specific injection first
        if app_name and app_type:
            success = self._handle_app_specific_injection(text, app_name, app_type)
            if success:
                logger.info(f"Successfully injected using app-specific method for {app_type}")
                return True
        
        # Escape special characters if needed
        if method == InjectionMethod.TYPING:
            text = self._escape_special_chars(text, app_type)
        
        # Inject based on method
        success = False
        if method == InjectionMethod.TYPING:
            success = self._inject_by_typing(text)
        elif method == InjectionMethod.CLIPBOARD:
            success = self._inject_by_clipboard(text)
        elif method == InjectionMethod.HYBRID:
            success = self._inject_by_typing(text)
            if not success and self.config.fallback_to_clipboard:
                logger.info("Typing failed, falling back to clipboard")
                success = self._inject_by_clipboard(text)
        
        if success:
            # Position cursor as configured
            self._position_cursor(text)
            
            # Optionally verify injection
            # self._verify_injection(text)  # Commented out to avoid side effects
        
        return success
    
    def _inject_by_typing(self, text: str) -> bool:
        """
        Inject text by simulating keyboard typing.
        
        Args:
            text: Text to type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check current input method state
            if self._is_ime_active():
                logger.warning("IME detected, typing may not work correctly")
            
            # Type the text
            pyautogui.typewrite(text, interval=0.001)  # Very fast typing
            
            logger.info(f"Typed {len(text)} characters")
            return True
            
        except Exception as e:
            logger.error(f"Failed to inject by typing: {e}")
            return False
    
    def _inject_by_clipboard(self, text: str) -> bool:
        """
        Inject text using clipboard and paste.
        
        Args:
            text: Text to inject
            
        Returns:
            True if successful, False otherwise
        """
        return self.clipboard.inject_via_clipboard(text, self.config.inject_delay)
    
    def _detect_best_method(self, app_name: Optional[str] = None) -> InjectionMethod:
        """
        Detect the best injection method for current context.
        
        Args:
            app_name: Name of target application
            
        Returns:
            Recommended injection method
        """
        # If auto_inject is disabled, use clipboard
        if not self.config.auto_inject:
            return InjectionMethod.CLIPBOARD
        
        # Check if app is in compatible list
        if app_name and self.config.compatible_apps:
            if app_name in self.config.compatible_apps:
                logger.debug(f"App {app_name} is in compatible list, using typing")
                return InjectionMethod.TYPING
        
        # Check if app is in incompatible list
        if app_name and self.config.incompatible_apps:
            if app_name in self.config.incompatible_apps:
                logger.debug(f"App {app_name} is in incompatible list, using clipboard")
                return InjectionMethod.CLIPBOARD
        
        # Default to hybrid for flexibility
        return InjectionMethod.HYBRID
    
    def _is_app_compatible(self, app_name: str) -> bool:
        """
        Check if an application is compatible with direct typing.
        
        Args:
            app_name: Name of the application
            
        Returns:
            True if compatible, False otherwise
        """
        # Check cache first
        if app_name in self._app_cache:
            return self._app_cache[app_name]
        
        # Check incompatible list
        if app_name in self.config.incompatible_apps:
            self._app_cache[app_name] = False
            return False
        
        # Check compatible list
        if self.config.compatible_apps:
            compatible = app_name in self.config.compatible_apps
            self._app_cache[app_name] = compatible
            return compatible
        
        # Default to compatible
        self._app_cache[app_name] = True
        return True
    
    def _format_text(self, text: str) -> str:
        """
        Format text for injection.
        
        Args:
            text: Original text
            
        Returns:
            Formatted text
        """
        # Basic formatting - can be extended
        # Fix common punctuation issues
        text = text.replace("  ", " ")  # Remove double spaces
        
        # Ensure proper spacing after punctuation
        punctuation = [".", "!", "?", ",", ";", ":"]
        for p in punctuation:
            text = text.replace(p + " ", p + " ")  # Normalize spaces
            text = text.replace(p + p, p)  # Remove duplicates
        
        return text
    
    def _position_cursor(self, text: str) -> None:
        """
        Position cursor after injection based on configuration.
        
        Args:
            text: Injected text
        """
        try:
            positioning = self.config.cursor_positioning
            
            if positioning == "start":
                # Move to start of text
                if self.is_macos:
                    pyautogui.hotkey("cmd", "left")
                else:
                    pyautogui.hotkey("home")
                    
            elif positioning == "select":
                # Select all injected text
                if self.is_macos:
                    pyautogui.hotkey("cmd", "a")
                else:
                    pyautogui.hotkey("ctrl", "a")
                    
            # "end" is default - cursor already at end after injection
            
        except Exception as e:
            logger.warning(f"Could not position cursor: {e}")
    
    def _is_ime_active(self) -> bool:
        """
        Check if an Input Method Editor (IME) is active.
        
        Returns:
            True if IME is active, False otherwise
        """
        # This is platform-specific and difficult to detect reliably
        # For now, return False (assume no IME)
        # Can be extended with platform-specific detection
        return False
    
    def get_active_window_info(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get information about the active window.
        
        Returns:
            Tuple of (window_title, app_name) or (None, None) if failed
        """
        try:
            if self.is_windows:
                return self._get_windows_window_info()
            elif self.is_macos:
                return self._get_macos_window_info()
            elif self.is_linux:
                return self._get_linux_window_info()
        except Exception as e:
            logger.warning(f"Could not get window info: {e}")
        
        return None, None
    
    def _get_windows_window_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get active window info on Windows."""
        try:
            import win32gui
            import win32process
            
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            
            try:
                import psutil
                process = psutil.Process(pid)
                app_name = process.name()
                return window_title, app_name
            except ImportError:
                logger.debug("psutil not available, returning window title only")
                return window_title, None
                
        except ImportError:
            logger.warning("Windows libraries not available")
        except Exception as e:
            logger.warning(f"Failed to get Windows window info: {e}")
        
        return None, None
    
    def _get_macos_window_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get active window info on macOS."""
        try:
            # This requires additional macOS-specific libraries
            # For now, return None
            # Can be implemented with pyobjc or applescript
            return None, None
        except Exception as e:
            logger.warning(f"Failed to get macOS window info: {e}")
            return None, None
    
    def _get_linux_window_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get active window info on Linux."""
        try:
            import subprocess
            
            # Try using xdotool (common on X11)
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            if result.returncode == 0:
                window_title = result.stdout.strip()
                
                # Try to get process name
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                if result.returncode == 0:
                    pid = int(result.stdout.strip())
                    try:
                        import psutil
                        process = psutil.Process(pid)
                        app_name = process.name()
                        return window_title, app_name
                    except ImportError:
                        logger.debug("psutil not available, returning window title only")
                        return window_title, None
                    except Exception as e:
                        logger.debug(f"Failed to get process name: {e}")
                        return window_title, None
                
                return window_title, None
                
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.debug("xdotool not available")
        except Exception as e:
            logger.warning(f"Failed to get Linux window info: {e}")
        
        return None, None
    
    def test_injection(self) -> bool:
        """
        Test text injection with a simple string.
        
        Returns:
            True if test successful, False otherwise
        """
        test_text = "NexTalk injection test"
        
        logger.info("Testing text injection...")
        success = self.inject_text(test_text, method=InjectionMethod.HYBRID)
        
        if success:
            logger.info("Text injection test successful")
        else:
            logger.error("Text injection test failed")
        
        return success
    
    def clear_statistics(self) -> None:
        """Clear cached application compatibility statistics."""
        self._app_cache.clear()
        logger.debug("Cleared application compatibility cache")
    
    def _load_app_profiles(self) -> Dict[str, dict]:
        """
        Load known application compatibility profiles.
        
        Returns:
            Dictionary of application profiles
        """
        profiles = {
            # Terminal/Console applications
            "terminal": {
                "apps": ["Terminal", "iTerm", "Console", "cmd.exe", "powershell.exe", 
                         "gnome-terminal", "konsole", "xterm"],
                "method": InjectionMethod.CLIPBOARD,
                "special_handling": "terminal"
            },
            # IDE/Code editors
            "ide": {
                "apps": ["Code", "VSCode", "IntelliJ", "PyCharm", "WebStorm", "Sublime",
                         "Atom", "vim", "nvim", "emacs"],
                "method": InjectionMethod.TYPING,
                "special_handling": "ide"
            },
            # Web browsers
            "browser": {
                "apps": ["Chrome", "Firefox", "Safari", "Edge", "Opera", "Brave"],
                "method": InjectionMethod.TYPING,
                "special_handling": "browser"
            },
            # Office applications
            "office": {
                "apps": ["Word", "Excel", "PowerPoint", "LibreOffice", "OpenOffice"],
                "method": InjectionMethod.TYPING,
                "special_handling": "office"
            },
            # Chat applications
            "chat": {
                "apps": ["Slack", "Discord", "Teams", "Telegram", "WhatsApp", "WeChat"],
                "method": InjectionMethod.TYPING,
                "special_handling": "chat"
            }
        }
        return profiles
    
    def _init_special_chars_map(self) -> Dict[str, str]:
        """
        Initialize special character mapping for different platforms.
        
        Returns:
            Dictionary mapping special characters to their escaped versions
        """
        if self.is_windows:
            return {
                "<": "{<}",
                ">": "{>}",
                "^": "{^}",
                "%": "{%}",
                "&": "{&}",
                "|": "{|}",
                "{": "{{}",
                "}": "{}}"
            }
        else:
            # Unix-like systems usually don't need escaping for typing
            return {}
    
    def _escape_special_chars(self, text: str, app_type: Optional[str] = None) -> str:
        """
        Escape special characters based on platform and application.
        
        Args:
            text: Text to escape
            app_type: Type of application (terminal, ide, etc.)
            
        Returns:
            Escaped text
        """
        if app_type == "terminal":
            # Terminal-specific escaping
            if self.is_windows:
                # Windows command prompt escaping
                text = text.replace("^", "^^")
                text = text.replace("&", "^&")
                text = text.replace("<", "^<")
                text = text.replace(">", "^>")
                text = text.replace("|", "^|")
            else:
                # Unix shell escaping
                text = text.replace("\\", "\\\\")
                text = text.replace("\"", "\\\"")
                text = text.replace("'", "\\'")
                text = text.replace("$", "\\$")
                text = text.replace("`", "\\`")
        else:
            # General escaping for typing
            for char, escaped in self._special_chars_map.items():
                text = text.replace(char, escaped)
        
        return text
    
    def _detect_app_type(self, app_name: Optional[str]) -> Optional[str]:
        """
        Detect the type of application based on its name.
        
        Args:
            app_name: Name of the application
            
        Returns:
            Application type (terminal, ide, browser, etc.) or None
        """
        if not app_name:
            return None
        
        app_lower = app_name.lower()
        
        for app_type, profile in self._app_profiles.items():
            for known_app in profile["apps"]:
                if known_app.lower() in app_lower:
                    return app_type
        
        return None
    
    def _handle_ime_compatibility(self, text: str) -> str:
        """
        Handle Input Method Editor (IME) compatibility.
        
        Args:
            text: Text to process
            
        Returns:
            Processed text suitable for IME input
        """
        # For Chinese/Japanese/Korean IME
        # Switch to English input mode if possible
        if self._contains_cjk(text):
            logger.debug("CJK characters detected, may need IME handling")
            # Some IMEs need special handling
            # This is highly platform and IME specific
            pass
        
        return text
    
    def _contains_cjk(self, text: str) -> bool:
        """
        Check if text contains CJK (Chinese, Japanese, Korean) characters.
        
        Args:
            text: Text to check
            
        Returns:
            True if contains CJK characters
        """
        cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+')
        return bool(cjk_pattern.search(text))
    
    def _ensure_focus(self) -> None:
        """Ensure the target window has focus before injection."""
        try:
            # Small click to ensure focus
            # Get current mouse position
            current_x, current_y = pyautogui.position()
            
            # Click at current position to ensure focus
            pyautogui.click(current_x, current_y)
            
            # Small delay to let the window gain focus
            time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Could not ensure window focus: {e}")
    
    def _handle_app_specific_injection(
        self,
        text: str,
        app_name: str,
        app_type: Optional[str]
    ) -> bool:
        """
        Handle application-specific injection logic.
        
        Args:
            text: Text to inject
            app_name: Name of the application
            app_type: Type of application
            
        Returns:
            True if handled, False to use default method
        """
        if app_type == "terminal":
            # Terminal applications often need special handling
            logger.debug(f"Using terminal-specific injection for {app_name}")
            
            # Ensure focus
            self._ensure_focus()
            
            # Escape special characters
            text = self._escape_special_chars(text, "terminal")
            
            # Use clipboard method for terminals
            return self.clipboard.inject_via_clipboard(text, 0.1)
            
        elif app_type == "ide":
            # IDEs usually work well with typing
            logger.debug(f"Using IDE-specific injection for {app_name}")
            
            # Some IDEs have auto-complete that might interfere
            # Send Escape first to close any popups
            pyautogui.press("escape")
            time.sleep(0.05)
            
            # Then type normally
            return False  # Use default method
            
        elif app_type == "browser":
            # Browsers might have focus issues with form fields
            logger.debug(f"Using browser-specific injection for {app_name}")
            
            # Ensure the input field has focus
            self._ensure_focus()
            
            # Clear any selection first
            pyautogui.hotkey("ctrl", "a") if not self.is_macos else pyautogui.hotkey("cmd", "a")
            time.sleep(0.02)
            
            # Then type
            return False  # Use default method
            
        elif app_type == "chat":
            # Chat apps might have rich text editors
            logger.debug(f"Using chat-specific injection for {app_name}")
            
            # Some chat apps need plain text mode
            # Try to switch to plain text (app-specific)
            return False  # Use default method
            
        return False  # Use default method
    
    def _verify_injection(self, original_text: str, timeout: float = 0.5) -> bool:
        """
        Verify that text was successfully injected.
        
        Args:
            original_text: The text that should have been injected
            timeout: Time to wait for verification
            
        Returns:
            True if injection verified, False otherwise
        """
        try:
            # Select all text
            time.sleep(0.1)
            if self.is_macos:
                pyautogui.hotkey("cmd", "a")
            else:
                pyautogui.hotkey("ctrl", "a")
            
            # Copy to clipboard
            time.sleep(0.05)
            if self.is_macos:
                pyautogui.hotkey("cmd", "c")
            else:
                pyautogui.hotkey("ctrl", "c")
            
            # Get clipboard content
            time.sleep(0.05)
            clipboard_text = pyperclip.paste()
            
            # Check if the injected text is in clipboard
            # (it might have additional text from before)
            if original_text in clipboard_text:
                logger.debug("Injection verified successfully")
                return True
            else:
                logger.warning("Injection verification failed")
                return False
                
        except Exception as e:
            logger.warning(f"Could not verify injection: {e}")
            return False
    
    def get_compatibility_report(self) -> Dict[str, any]:
        """
        Get a compatibility report for debugging.
        
        Returns:
            Dictionary with compatibility information
        """
        report = {
            "platform": self.platform,
            "app_cache": self._app_cache,
            "known_profiles": list(self._app_profiles.keys()),
            "compatible_apps": self.config.compatible_apps,
            "incompatible_apps": self.config.incompatible_apps,
            "injection_stats": {
                "cached_apps": len(self._app_cache),
                "compatible": sum(1 for v in self._app_cache.values() if v),
                "incompatible": sum(1 for v in self._app_cache.values() if not v)
            }
        }
        return report