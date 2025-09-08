"""
Windows IME adapter implementation.

Uses Windows Text Services Framework (TSF) and Win32 APIs for IME integration.
"""

import asyncio
import logging
import time
import ctypes
import ctypes.wintypes
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys

# Windows-specific imports
if sys.platform == "win32":
    try:
        import win32api
        import win32con
        import win32gui
        import win32process
        import win32clipboard
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False

from .ime_base import (
    IMEAdapter, IMEStateMonitor, IMEResult, IMEStatus, IMEInfo,
    CompositionState, IMEFramework, IMEStateEvent, FocusEvent,
    IMEInitializationError, IMEPermissionError, IMETimeoutError,
    IMEStateError
)
from ..utils.system import is_admin


logger = logging.getLogger(__name__)


# Windows API constants
HWND_MESSAGE = -3
WM_IME_CHAR = 0x0286
WM_CHAR = 0x0102
WM_IME_COMPOSITION = 0x010F
WM_IME_COMPOSITIONFULL = 0x0284
WM_IME_CONTROL = 0x0283
WM_IME_ENDCOMPOSITION = 0x010E
WM_IME_NOTIFY = 0x0282
WM_IME_SETCONTEXT = 0x0281
WM_IME_STARTCOMPOSITION = 0x010D

# IME constants
GCS_COMPREADSTR = 0x0001
GCS_COMPREADATTR = 0x0002
GCS_COMPREADCLAUSE = 0x0004
GCS_COMPSTR = 0x0008
GCS_COMPATTR = 0x0010
GCS_COMPCLAUSE = 0x0020
GCS_CURSORPOS = 0x0080
GCS_DELTASTART = 0x0100
GCS_RESULTREADSTR = 0x0200
GCS_RESULTREADCLAUSE = 0x0400
GCS_RESULTSTR = 0x0800
GCS_RESULTCLAUSE = 0x1000


class WindowsIMEAdapter(IMEAdapter):
    """Windows IME adapter using Text Services Framework."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Windows IME adapter.
        
        Args:
            config: IME configuration parameters
        """
        super().__init__(config)
        self._hwnd = None
        self._himc = None
        self._current_ime = None
        self._composition_state = CompositionState.INACTIVE
        
        # Configuration
        self.use_unicode = config.get('use_unicode', True)
        self.composition_timeout = config.get('composition_timeout', 1.0)
        self.debug_mode = config.get('debug_mode', False)
        
        # Windows API libraries
        self.user32 = None
        self.imm32 = None
        self.kernel32 = None
        
        if sys.platform != "win32":
            raise IMEInitializationError("Windows IME adapter can only be used on Windows")
    
    async def initialize(self) -> bool:
        """
        Initialize the Windows IME adapter.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not WIN32_AVAILABLE:
            self.logger.error("pywin32 libraries not available. Install pywin32")
            return False
        
        try:
            # Load Windows API libraries
            self.user32 = ctypes.windll.user32
            self.imm32 = ctypes.windll.imm32
            self.kernel32 = ctypes.windll.kernel32
            
            # Get current thread's window handle or create a message window
            self._hwnd = await self._get_or_create_window()
            if not self._hwnd:
                self.logger.error("Failed to get window handle")
                return False
            
            # Get IME context
            self._himc = self.imm32.ImmGetContext(self._hwnd)
            if not self._himc:
                self.logger.warning("No IME context available, creating default context")
                self._himc = self.imm32.ImmCreateContext()
                if not self._himc:
                    self.logger.error("Failed to create IME context")
                    return False
            
            # Detect current IME
            ime_info = await self.detect_active_ime()
            if ime_info:
                self._current_ime = ime_info.name
                self.logger.info(f"Detected IME: {self._current_ime}")
            
            self._set_initialized(True)
            self.logger.info("Windows IME adapter initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Windows IME adapter: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up Windows IME adapter resources."""
        try:
            if self._himc:
                self.imm32.ImmReleaseContext(self._hwnd, self._himc)
                self._himc = None
            
            if self._hwnd:
                # Don't destroy system windows
                pass
            
            self._set_initialized(False)
            self.logger.info("Windows IME adapter cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def inject_text(self, text: str) -> IMEResult:
        """
        Inject text through the Windows IME framework.
        
        Args:
            text: Text to inject
            
        Returns:
            IMEResult with operation status and details
        """
        if not self.is_initialized:
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="",
                injection_time=0.0,
                error="IME adapter not initialized"
            )
        
        start_time = time.time()
        
        try:
            # Get current focus information
            focus_info = await self._get_focus_info()
            target_hwnd = focus_info.get('hwnd')
            
            if self.debug_mode:
                self.logger.debug(f"Injecting text to {focus_info.get('app_name', 'unknown')}: {text}")
            
            # Try different injection methods in order of preference
            success = False
            method_used = ""
            
            # Method 1: Direct IME composition
            if target_hwnd and await self._is_ime_enabled(target_hwnd):
                success = await self._inject_via_ime_composition(text, target_hwnd)
                method_used = "ime_composition"
            
            # Method 2: SendMessage with WM_CHAR
            if not success and target_hwnd:
                success = await self._inject_via_sendmessage(text, target_hwnd)
                method_used = "sendmessage"
            
            # Method 3: Clipboard fallback (only if configured)
            if not success and self.config.get('allow_clipboard_fallback', False):
                success = await self._inject_via_clipboard(text)
                method_used = "clipboard"
            
            injection_time = time.time() - start_time
            
            return IMEResult(
                success=success,
                text_injected=text if success else "",
                ime_used=f"{self._current_ime or 'system'}_{method_used}",
                injection_time=injection_time,
                error=None if success else "All injection methods failed"
            )
            
        except Exception as e:
            injection_time = time.time() - start_time
            self.logger.error(f"Text injection failed: {e}")
            return IMEResult(
                success=False,
                text_injected="",
                ime_used=self._current_ime or "unknown",
                injection_time=injection_time,
                error=str(e)
            )
    
    async def get_ime_status(self) -> IMEStatus:
        """
        Get current IME status.
        
        Returns:
            Current IME status information
        """
        try:
            focus_info = await self._get_focus_info()
            ime_info = await self.detect_active_ime()
            
            # Check composition state
            composition_state = await self._get_composition_state()
            
            return IMEStatus(
                is_active=ime_info is not None and ime_info.is_active,
                current_ime=ime_info.name if ime_info else "system",
                composition_state=composition_state,
                input_language=ime_info.language if ime_info else self._get_system_language(),
                focus_app=focus_info.get('app_name', 'unknown'),
                last_updated=datetime.now()
            )
        except Exception as e:
            self.logger.error(f"Failed to get IME status: {e}")
            return IMEStatus(
                is_active=False,
                current_ime="error",
                composition_state=CompositionState.INACTIVE,
                input_language="en",
                focus_app="unknown",
                last_updated=datetime.now()
            )
    
    async def detect_active_ime(self) -> Optional[IMEInfo]:
        """
        Detect the currently active IME.
        
        Returns:
            IME information if detected, None otherwise
        """
        try:
            # Get current keyboard layout
            hkl = self.user32.GetKeyboardLayout(0)
            
            # Extract language and sublanguage
            lang_id = hkl & 0xFFFF
            sublang_id = (hkl >> 16) & 0xFFFF
            
            # Get keyboard layout name
            layout_name = self._get_keyboard_layout_name(hkl)
            
            # Check if it's an IME layout
            is_ime = self._is_ime_keyboard_layout(hkl)
            
            if is_ime:
                return IMEInfo(
                    name=layout_name,
                    framework=IMEFramework.UNKNOWN,  # Windows doesn't use external frameworks
                    language=self._get_language_from_id(lang_id),
                    is_active=True,
                    version=None
                )
            else:
                return IMEInfo(
                    name="System Input",
                    framework=IMEFramework.UNKNOWN,
                    language=self._get_language_from_id(lang_id),
                    is_active=False,
                    version=None
                )
                
        except Exception as e:
            self.logger.error(f"Failed to detect active IME: {e}")
            return None
    
    async def is_ime_ready(self) -> bool:
        """
        Check if IME is ready for text injection.
        
        Returns:
            True if IME is ready, False otherwise
        """
        if not self.is_initialized:
            return False
        
        try:
            # Check if we have a valid IME context
            if not self._himc:
                return False
            
            # Check if target window accepts text input
            focus_info = await self._get_focus_info()
            target_hwnd = focus_info.get('hwnd')
            
            if target_hwnd:
                return await self._can_accept_text_input(target_hwnd)
            
            return False
        except Exception:
            return False
    
    async def _get_or_create_window(self) -> Optional[int]:
        """Get current window handle or create a message window."""
        try:
            # First try to get foreground window
            hwnd = self.user32.GetForegroundWindow()
            if hwnd:
                return hwnd
            
            # Fall back to desktop window
            hwnd = self.user32.GetDesktopWindow()
            return hwnd if hwnd else None
            
        except Exception as e:
            self.logger.error(f"Failed to get window handle: {e}")
            return None
    
    async def _inject_via_ime_composition(self, text: str, target_hwnd: int) -> bool:
        """Inject text through IME composition."""
        try:
            # Get IME context for target window
            himc = self.imm32.ImmGetContext(target_hwnd)
            if not himc:
                return False
            
            # Convert text to appropriate encoding
            if self.use_unicode:
                text_bytes = text.encode('utf-16le')
                text_len = len(text_bytes)
            else:
                text_bytes = text.encode('cp932', errors='ignore')  # Japanese encoding fallback
                text_len = len(text_bytes)
            
            # Set composition string
            result = self.imm32.ImmSetCompositionStringW(
                himc, GCS_COMPSTR, text_bytes, text_len, None, 0
            )
            
            # Commit the composition
            if result:
                result = self.imm32.ImmNotifyIME(himc, 2, 0, 0)  # NI_COMPOSITIONSTR, CPS_COMPLETE
            
            # Release context
            self.imm32.ImmReleaseContext(target_hwnd, himc)
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"IME composition injection failed: {e}")
            return False
    
    async def _inject_via_sendmessage(self, text: str, target_hwnd: int) -> bool:
        """Inject text via SendMessage with WM_CHAR."""
        try:
            for char in text:
                char_code = ord(char)
                
                # Send WM_CHAR message
                result = self.user32.SendMessageW(target_hwnd, WM_CHAR, char_code, 0)
                
                # Small delay between characters
                await asyncio.sleep(0.001)
            
            return True
            
        except Exception as e:
            self.logger.error(f"SendMessage injection failed: {e}")
            return False
    
    async def _inject_via_clipboard(self, text: str) -> bool:
        """Inject text via clipboard paste."""
        try:
            # Save current clipboard content
            old_clipboard = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    old_clipboard = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except:
                pass
            
            # Set text to clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            
            # Send Ctrl+V to paste
            focus_hwnd = self.user32.GetForegroundWindow()
            if focus_hwnd:
                # Send Ctrl key down
                self.user32.SendMessageW(focus_hwnd, 0x0100, 0x11, 0)  # WM_KEYDOWN, VK_CONTROL
                # Send V key
                self.user32.SendMessageW(focus_hwnd, WM_CHAR, ord('V'), 0)
                # Send Ctrl key up
                self.user32.SendMessageW(focus_hwnd, 0x0101, 0x11, 0)  # WM_KEYUP, VK_CONTROL
            
            # Restore clipboard
            if old_clipboard:
                await asyncio.sleep(0.1)  # Give time for paste to complete
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_clipboard)
                win32clipboard.CloseClipboard()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Clipboard injection failed: {e}")
            return False
    
    async def _get_focus_info(self) -> Dict[str, Any]:
        """Get information about currently focused window."""
        try:
            hwnd = self.user32.GetForegroundWindow()
            if not hwnd:
                return {'hwnd': None, 'window_title': 'unknown', 'app_name': 'unknown'}
            
            # Get window title
            title_length = self.user32.GetWindowTextLengthW(hwnd)
            if title_length > 0:
                title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                self.user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                window_title = title_buffer.value
            else:
                window_title = "unknown"
            
            # Get process info
            process_id = ctypes.wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            
            try:
                process_handle = self.kernel32.OpenProcess(0x0400, False, process_id.value)  # PROCESS_QUERY_INFORMATION
                if process_handle:
                    module_name = ctypes.create_unicode_buffer(260)
                    self.kernel32.GetModuleBaseNameW(
                        process_handle, None, module_name, 260
                    )
                    app_name = module_name.value
                    self.kernel32.CloseHandle(process_handle)
                else:
                    app_name = "unknown"
            except:
                app_name = "unknown"
            
            return {
                'hwnd': hwnd,
                'window_title': window_title,
                'app_name': app_name,
                'process_id': process_id.value
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to get focus info: {e}")
            return {'hwnd': None, 'window_title': 'unknown', 'app_name': 'unknown'}
    
    async def _is_ime_enabled(self, hwnd: int) -> bool:
        """Check if IME is enabled for the given window."""
        try:
            himc = self.imm32.ImmGetContext(hwnd)
            if not himc:
                return False
            
            # Check if IME is open
            is_open = self.imm32.ImmGetOpenStatus(himc)
            
            # Release context
            self.imm32.ImmReleaseContext(hwnd, himc)
            
            return bool(is_open)
        except:
            return False
    
    async def _can_accept_text_input(self, hwnd: int) -> bool:
        """Check if window can accept text input."""
        try:
            # Check window class for common text input controls
            class_name = ctypes.create_unicode_buffer(256)
            self.user32.GetClassNameW(hwnd, class_name, 256)
            class_str = class_name.value.lower()
            
            text_input_classes = [
                'edit', 'richedit', 'richedit20a', 'richedit20w', 
                'scintilla', 'consolewindowclass', 'notepad'
            ]
            
            return any(cls in class_str for cls in text_input_classes)
        except:
            return True  # Assume yes if we can't determine
    
    async def _get_composition_state(self) -> CompositionState:
        """Get current IME composition state."""
        try:
            if not self._himc:
                return CompositionState.INACTIVE
            
            # Check composition string length
            comp_len = self.imm32.ImmGetCompositionStringW(self._himc, GCS_COMPSTR, None, 0)
            
            if comp_len > 0:
                return CompositionState.COMPOSING
            else:
                return CompositionState.INACTIVE
        except:
            return CompositionState.INACTIVE
    
    def _get_keyboard_layout_name(self, hkl: int) -> str:
        """Get keyboard layout name from handle."""
        try:
            # This is a simplified version - in practice, you'd query the registry
            # or use more detailed Windows APIs
            lang_id = hkl & 0xFFFF
            
            # Common IME layouts
            ime_layouts = {
                0x0804: "Chinese (Simplified)",
                0x0404: "Chinese (Traditional)", 
                0x0411: "Japanese",
                0x0412: "Korean"
            }
            
            return ime_layouts.get(lang_id, f"Layout_{lang_id:04X}")
        except:
            return "Unknown"
    
    def _is_ime_keyboard_layout(self, hkl: int) -> bool:
        """Check if keyboard layout is an IME."""
        try:
            # IME layouts typically have the high bit set in the sublanguage
            sublang = (hkl >> 16) & 0xFFFF
            return (sublang & 0xF000) != 0
        except:
            return False
    
    def _get_language_from_id(self, lang_id: int) -> str:
        """Get language string from language ID."""
        language_map = {
            0x0409: "en",  # English (US)
            0x0804: "zh-CN",  # Chinese (Simplified)
            0x0404: "zh-TW",  # Chinese (Traditional)
            0x0411: "ja",  # Japanese
            0x0412: "ko",  # Korean
        }
        return language_map.get(lang_id, "en")
    
    def _get_system_language(self) -> str:
        """Get system default language."""
        try:
            lang_id = self.kernel32.GetSystemDefaultLangID()
            return self._get_language_from_id(lang_id)
        except:
            return "en"


class WindowsIMEStateMonitor(IMEStateMonitor):
    """Windows IME state monitor."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Windows IME state monitor."""
        super().__init__(config)
        self._adapter = WindowsIMEAdapter(config)
        self._monitor_interval = config.get('state_monitor_interval', 0.1)
    
    async def start_monitoring(self) -> None:
        """Start monitoring IME state changes."""
        if not await self._adapter.initialize():
            raise IMEInitializationError("Failed to initialize IME adapter for monitoring")
        
        self._set_monitoring(True)
        self.logger.info("Started Windows IME state monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring IME state changes."""
        self._set_monitoring(False)
        await self._adapter.cleanup()
        self.logger.info("Stopped Windows IME state monitoring")
    
    async def monitor_ime_state(self):
        """Monitor IME state changes."""
        if not self.is_monitoring:
            return
        
        last_status = None
        
        while self.is_monitoring:
            try:
                current_status = await self._adapter.get_ime_status()
                
                if last_status and self._status_changed(last_status, current_status):
                    yield IMEStateEvent(
                        event_type="status_changed",
                        old_state=last_status,
                        new_state=current_status
                    )
                
                last_status = current_status
                await asyncio.sleep(self._monitor_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring IME state: {e}")
                await asyncio.sleep(self._monitor_interval)
    
    async def monitor_focus_changes(self):
        """Monitor window focus changes."""
        if not self.is_monitoring:
            return
        
        last_focus = None
        
        while self.is_monitoring:
            try:
                current_focus = await self._adapter._get_focus_info()
                
                if (last_focus and 
                    (last_focus.get('app_name') != current_focus.get('app_name') or
                     last_focus.get('window_title') != current_focus.get('window_title'))):
                    
                    yield FocusEvent(
                        window_title=current_focus.get('window_title', ''),
                        app_name=current_focus.get('app_name', ''),
                        process_id=current_focus.get('process_id', 0),
                        timestamp=datetime.now()
                    )
                
                last_focus = current_focus
                await asyncio.sleep(self._monitor_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring focus changes: {e}")
                await asyncio.sleep(self._monitor_interval)
    
    def _status_changed(self, old_status: IMEStatus, new_status: IMEStatus) -> bool:
        """Check if IME status has changed significantly."""
        return (old_status.current_ime != new_status.current_ime or
                old_status.is_active != new_status.is_active or
                old_status.focus_app != new_status.focus_app or
                old_status.composition_state != new_status.composition_state)