"""
macOS IME adapter implementation.

Uses macOS Input Method Kit and Carbon/Cocoa APIs for IME integration.
"""

import asyncio
import logging
import time
import subprocess
from typing import Optional, Dict, Any, List
from datetime import datetime
import sys

# macOS-specific imports
if sys.platform == "darwin":
    try:
        import objc
        from Foundation import NSBundle, NSString, NSArray
        from AppKit import NSApplication, NSWorkspace, NSRunningApplication
        from Carbon import TextInput
        MACOS_APIS_AVAILABLE = True
    except ImportError:
        try:
            # Fallback to subprocess-based approach if PyObjC not available
            import subprocess
            MACOS_APIS_AVAILABLE = False
        except ImportError:
            MACOS_APIS_AVAILABLE = False
else:
    MACOS_APIS_AVAILABLE = False

from .ime_base import (
    IMEAdapter, IMEStateMonitor, IMEResult, IMEStatus, IMEInfo,
    CompositionState, IMEFramework, IMEStateEvent, FocusEvent,
    IMEInitializationError, IMEPermissionError, IMETimeoutError,
    IMEStateError
)


logger = logging.getLogger(__name__)


class MacOSIMEAdapter(IMEAdapter):
    """macOS IME adapter using Input Method Kit."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize macOS IME adapter.
        
        Args:
            config: IME configuration parameters
        """
        super().__init__(config)
        self._current_input_source = None
        self._composition_state = CompositionState.INACTIVE
        self._app = None
        self._workspace = None
        
        # Configuration
        self.use_accessibility_api = config.get('use_accessibility_api', True)
        self.composition_timeout = config.get('composition_timeout', 1.0)
        self.debug_mode = config.get('debug_mode', False)
        self.fallback_to_applescript = config.get('fallback_to_applescript', True)
        
        if sys.platform != "darwin":
            raise IMEInitializationError("macOS IME adapter can only be used on macOS")
    
    async def initialize(self) -> bool:
        """
        Initialize the macOS IME adapter.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Check for required permissions
            if not await self._check_accessibility_permissions():
                self.logger.warning("Accessibility permissions not granted")
                if not self.fallback_to_applescript:
                    return False
            
            if MACOS_APIS_AVAILABLE:
                # Initialize NSApplication if needed
                try:
                    self._app = NSApplication.sharedApplication()
                    self._workspace = NSWorkspace.sharedWorkspace()
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Cocoa APIs: {e}")
            
            # Detect current input source
            input_source_info = await self.detect_active_ime()
            if input_source_info:
                self._current_input_source = input_source_info.name
                self.logger.info(f"Detected input source: {self._current_input_source}")
            
            self._set_initialized(True)
            self.logger.info("macOS IME adapter initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize macOS IME adapter: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up macOS IME adapter resources."""
        try:
            # Clean up any allocated resources
            self._app = None
            self._workspace = None
            self._set_initialized(False)
            self.logger.info("macOS IME adapter cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def inject_text(self, text: str) -> IMEResult:
        """
        Inject text through the macOS IME framework.
        
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
            
            if self.debug_mode:
                self.logger.debug(f"Injecting text to {focus_info.get('app_name', 'unknown')}: {text}")
            
            # Try different injection methods in order of preference
            success = False
            method_used = ""
            
            # Method 1: Carbon Text Input APIs (if available)
            if MACOS_APIS_AVAILABLE and self.use_accessibility_api:
                success = await self._inject_via_carbon_text_input(text)
                method_used = "carbon_text_input"
            
            # Method 2: AppleScript automation
            if not success and self.fallback_to_applescript:
                success = await self._inject_via_applescript(text)
                method_used = "applescript"
            
            # Method 3: Accessibility API
            if not success and self.use_accessibility_api:
                success = await self._inject_via_accessibility_api(text)
                method_used = "accessibility_api"
            
            injection_time = time.time() - start_time
            
            return IMEResult(
                success=success,
                text_injected=text if success else "",
                ime_used=f"{self._current_input_source or 'system'}_{method_used}",
                injection_time=injection_time,
                error=None if success else "All injection methods failed"
            )
            
        except Exception as e:
            injection_time = time.time() - start_time
            self.logger.error(f"Text injection failed: {e}")
            return IMEResult(
                success=False,
                text_injected="",
                ime_used=self._current_input_source or "unknown",
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
            # Method 1: Use Carbon Text Input Manager
            if MACOS_APIS_AVAILABLE:
                input_source_info = await self._get_current_input_source_carbon()
                if input_source_info:
                    return input_source_info
            
            # Method 2: Use command line tools
            input_source_info = await self._get_current_input_source_cli()
            return input_source_info
                
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
            # Check if we have accessibility permissions
            if self.use_accessibility_api and not await self._check_accessibility_permissions():
                return self.fallback_to_applescript
            
            # Check if there's a focused application that can accept text
            focus_info = await self._get_focus_info()
            return focus_info.get('app_name') != 'unknown'
        except Exception:
            return False
    
    async def _check_accessibility_permissions(self) -> bool:
        """Check if accessibility permissions are granted."""
        try:
            # Use AppleScript to check accessibility permissions
            script = '''
            tell application "System Events"
                try
                    get name of first process
                    return true
                on error
                    return false
                end try
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            
            return result.returncode == 0 and result.stdout.strip().lower() == 'true'
        except Exception as e:
            self.logger.debug(f"Failed to check accessibility permissions: {e}")
            return False
    
    async def _inject_via_carbon_text_input(self, text: str) -> bool:
        """Inject text via Carbon Text Input APIs."""
        try:
            if not MACOS_APIS_AVAILABLE:
                return False
            
            # This is a simplified implementation
            # In practice, Carbon Text Input requires more complex setup
            # for proper IME integration
            
            # For now, fall back to other methods
            return False
            
        except Exception as e:
            self.logger.error(f"Carbon text input injection failed: {e}")
            return False
    
    async def _inject_via_applescript(self, text: str) -> bool:
        """Inject text via AppleScript."""
        try:
            # Escape text for AppleScript
            escaped_text = text.replace('"', '\\"').replace('\\', '\\\\')
            
            # AppleScript to type text
            script = f'''
            tell application "System Events"
                keystroke "{escaped_text}"
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=10
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"AppleScript injection failed: {e}")
            return False
    
    async def _inject_via_accessibility_api(self, text: str) -> bool:
        """Inject text via macOS Accessibility API."""
        try:
            if not MACOS_APIS_AVAILABLE:
                return False
            
            # This would require more complex implementation using
            # AXUIElementRef and related accessibility APIs
            # For now, return False to use other methods
            return False
            
        except Exception as e:
            self.logger.error(f"Accessibility API injection failed: {e}")
            return False
    
    async def _get_focus_info(self) -> Dict[str, Any]:
        """Get information about currently focused application."""
        try:
            if MACOS_APIS_AVAILABLE and self._workspace:
                # Use Cocoa APIs
                active_app = self._workspace.frontmostApplication()
                if active_app:
                    return {
                        'app_name': str(active_app.localizedName() or 'unknown'),
                        'bundle_id': str(active_app.bundleIdentifier() or 'unknown'),
                        'process_id': int(active_app.processIdentifier())
                    }
            
            # Fall back to command line approach
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get name of first application process whose frontmost is true'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                app_name = result.stdout.strip()
                return {
                    'app_name': app_name,
                    'bundle_id': 'unknown',
                    'process_id': 0
                }
            
            return {
                'app_name': 'unknown',
                'bundle_id': 'unknown',
                'process_id': 0
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to get focus info: {e}")
            return {
                'app_name': 'unknown',
                'bundle_id': 'unknown',
                'process_id': 0
            }
    
    async def _get_current_input_source_carbon(self) -> Optional[IMEInfo]:
        """Get current input source using Carbon APIs."""
        try:
            if not MACOS_APIS_AVAILABLE:
                return None
            
            # This would require proper Carbon Text Input Manager integration
            # For now, return None to use CLI approach
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get input source via Carbon: {e}")
            return None
    
    async def _get_current_input_source_cli(self) -> Optional[IMEInfo]:
        """Get current input source using command line tools."""
        try:
            # Get current input source
            result = subprocess.run(
                ['/usr/bin/defaults', 'read', 'com.apple.HIToolbox', 'AppleCurrentKeyboardLayoutInputSourceID'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode != 0:
                # Try alternative method
                result = subprocess.run(
                    ['osascript', '-e', 'tell application "System Events" to tell process "SystemUIServer" to get value of attribute "AXDescription" of menu bar item 1 of menu bar 1'],
                    capture_output=True, text=True, timeout=2
                )
            
            if result.returncode == 0:
                input_source_id = result.stdout.strip()
                
                # Parse input source information
                is_ime = self._is_ime_input_source(input_source_id)
                language = self._get_language_from_input_source(input_source_id)
                
                return IMEInfo(
                    name=self._get_friendly_name_from_input_source(input_source_id),
                    framework=IMEFramework.UNKNOWN,  # macOS uses native input methods
                    language=language,
                    is_active=is_ime,
                    version=None
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get input source via CLI: {e}")
            return None
    
    async def _get_composition_state(self) -> CompositionState:
        """Get current IME composition state."""
        try:
            # This would require integration with Text Input Manager
            # to get actual composition state
            # For now, return INACTIVE
            return CompositionState.INACTIVE
        except:
            return CompositionState.INACTIVE
    
    def _is_ime_input_source(self, input_source_id: str) -> bool:
        """Check if input source is an IME."""
        ime_indicators = [
            'chinese', 'japanese', 'korean', 'pinyin', 'zhuyin',
            'hiragana', 'katakana', 'romaji', 'hangul', 'hanja'
        ]
        
        input_source_lower = input_source_id.lower()
        return any(indicator in input_source_lower for indicator in ime_indicators)
    
    def _get_language_from_input_source(self, input_source_id: str) -> str:
        """Get language code from input source ID."""
        input_source_lower = input_source_id.lower()
        
        if 'chinese' in input_source_lower or 'pinyin' in input_source_lower or 'zhuyin' in input_source_lower:
            if 'traditional' in input_source_lower or 'hant' in input_source_lower:
                return 'zh-TW'
            else:
                return 'zh-CN'
        elif 'japanese' in input_source_lower or 'hiragana' in input_source_lower or 'katakana' in input_source_lower:
            return 'ja'
        elif 'korean' in input_source_lower or 'hangul' in input_source_lower:
            return 'ko'
        else:
            return 'en'
    
    def _get_friendly_name_from_input_source(self, input_source_id: str) -> str:
        """Get friendly name from input source ID."""
        # Extract friendly name from input source ID
        if '.' in input_source_id:
            parts = input_source_id.split('.')
            return parts[-1].replace('_', ' ').title()
        else:
            return input_source_id.replace('_', ' ').title()
    
    def _get_system_language(self) -> str:
        """Get system default language."""
        try:
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleLanguages'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.returncode == 0:
                # Parse the array output and get first language
                output = result.stdout.strip()
                if '(' in output and ')' in output:
                    languages_part = output.split('(')[1].split(')')[0]
                    first_lang = languages_part.split(',')[0].strip().strip('"')
                    return first_lang.replace('-', '_') if first_lang else 'en'
            
            return 'en'
        except:
            return 'en'


class MacOSIMEStateMonitor(IMEStateMonitor):
    """macOS IME state monitor."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize macOS IME state monitor."""
        super().__init__(config)
        self._adapter = MacOSIMEAdapter(config)
        self._monitor_interval = config.get('state_monitor_interval', 0.1)
    
    async def start_monitoring(self) -> None:
        """Start monitoring IME state changes."""
        if not await self._adapter.initialize():
            raise IMEInitializationError("Failed to initialize IME adapter for monitoring")
        
        self._set_monitoring(True)
        self.logger.info("Started macOS IME state monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring IME state changes."""
        self._set_monitoring(False)
        await self._adapter.cleanup()
        self.logger.info("Stopped macOS IME state monitoring")
    
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
        """Monitor application focus changes."""
        if not self.is_monitoring:
            return
        
        last_focus = None
        
        while self.is_monitoring:
            try:
                current_focus = await self._adapter._get_focus_info()
                
                if (last_focus and 
                    (last_focus.get('app_name') != current_focus.get('app_name') or
                     last_focus.get('bundle_id') != current_focus.get('bundle_id'))):
                    
                    yield FocusEvent(
                        window_title=current_focus.get('app_name', ''),  # macOS doesn't easily provide window titles
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