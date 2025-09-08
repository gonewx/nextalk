"""
Linux IME adapter implementation.

Supports IBus and Fcitx input method frameworks through DBus interfaces.
"""

import asyncio
import logging
import os
import re
import subprocess
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

from .ime_base import (
    IMEAdapter, IMEStateMonitor, IMEResult, IMEStatus, IMEInfo,
    CompositionState, IMEFramework, IMEStateEvent, FocusEvent,
    IMEInitializationError, IMEPermissionError, IMETimeoutError,
    IMEStateError
)


logger = logging.getLogger(__name__)


class LinuxIMEAdapter(IMEAdapter):
    """Linux IME adapter supporting IBus and Fcitx."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Linux IME adapter.
        
        Args:
            config: IME configuration parameters
        """
        super().__init__(config)
        self._bus = None
        self._ime_proxy = None
        self._current_framework = IMEFramework.UNKNOWN
        self._ime_info = None
        
        # Configuration - force IBus priority for better text injection support
        # Override any config file settings to ensure IBus is tried first
        self.frameworks_to_try = ['ibus', 'fcitx5', 'fcitx']
        self.dbus_timeout = config.get('dbus_timeout', 2.0)
        self.debug_mode = config.get('debug_mode', False)
    
    async def initialize(self) -> bool:
        """
        Initialize the Linux IME adapter.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not DBUS_AVAILABLE:
            self.logger.error("DBus libraries not available. Install python3-dbus and python3-gi")
            return False
        
        try:
            # Initialize DBus main loop
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            
            # Connect to session bus
            self._bus = dbus.SessionBus()
            
            # Detect and connect to available IME framework
            framework_detected = await self._detect_and_connect_ime()
            
            if framework_detected:
                self._set_initialized(True)
                self.logger.info(f"Linux IME adapter initialized with {self._current_framework.value}")
                return True
            else:
                self.logger.error("No compatible IME framework found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Linux IME adapter: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up Linux IME adapter resources."""
        try:
            # Give time for any pending DBus operations to complete
            await asyncio.sleep(0.05)
            
            if self._ime_proxy:
                self._ime_proxy = None
                
            # Don't close the session bus - it's shared and managed by the system
            # Just remove our reference to avoid the GLib-GIO-CRITICAL error
            if self._bus:
                self._bus = None
                
            self._set_initialized(False)
            self.logger.info("Linux IME adapter cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    async def inject_text(self, text: str) -> IMEResult:
        """
        Inject text through the Linux IME framework.
        
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
            
            # Inject text based on detected framework - ONLY use IME APIs
            success = False
            if self._current_framework == IMEFramework.IBUS:
                success = await self._inject_text_ibus_native(text)
            elif self._current_framework == IMEFramework.FCITX:
                # Check if this is actually Fcitx5 based on the proxy interface
                if hasattr(self._ime_proxy, 'State'):  # Fcitx5 has State method
                    success = await self._inject_text_fcitx5_native(text)
                else:
                    success = await self._inject_text_fcitx_native(text)
            else:
                return IMEResult(
                    success=False,
                    text_injected="",
                    ime_used="unknown",
                    injection_time=time.time() - start_time,
                    error="No supported IME framework detected"
                )
            
            injection_time = time.time() - start_time
            
            return IMEResult(
                success=success,
                text_injected=text if success else "",
                ime_used=self._current_framework.value,
                injection_time=injection_time,
                error=None if success else "Text injection failed"
            )
            
        except Exception as e:
            injection_time = time.time() - start_time
            self.logger.error(f"Text injection failed: {e}")
            return IMEResult(
                success=False,
                text_injected="",
                ime_used=self._current_framework.value,
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
            
            return IMEStatus(
                is_active=ime_info is not None and ime_info.is_active,
                current_ime=ime_info.name if ime_info else "unknown",
                composition_state=CompositionState.INACTIVE,  # TODO: Implement composition state detection
                input_language=ime_info.language if ime_info else "en",
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
            if self._current_framework == IMEFramework.IBUS:
                return await self._detect_ibus_ime()
            elif self._current_framework == IMEFramework.FCITX:
                return await self._detect_fcitx_ime()
            else:
                return None
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
            # Check if IME service is running
            ime_info = await self.detect_active_ime()
            return ime_info is not None and ime_info.is_active
        except Exception:
            return False
    
    async def _detect_and_connect_ime(self) -> bool:
        """Detect and connect to available IME framework with intelligent detection."""
        self.logger.info(f"Trying IME frameworks in order: {self.frameworks_to_try}")
        
        # First, check what's actually running
        running_frameworks = await self._detect_running_frameworks()
        self.logger.debug(f"Detected running frameworks: {running_frameworks}")
        
        # Prioritize based on what's actually running
        ordered_frameworks = []
        for framework in running_frameworks:
            if framework in self.frameworks_to_try:
                ordered_frameworks.append(framework)
        
        # Add remaining frameworks from config
        for framework in self.frameworks_to_try:
            if framework not in ordered_frameworks:
                ordered_frameworks.append(framework)
        
        for framework_name in ordered_frameworks:
            self.logger.debug(f"Attempting to connect to {framework_name}...")
            
            if framework_name.lower() == 'fcitx5':
                if await self._try_connect_fcitx5():
                    self._current_framework = IMEFramework.FCITX
                    self.logger.info(f"Successfully connected to Fcitx5")
                    return True
                else:
                    self.logger.warning(f"Failed to connect to Fcitx5")
                    
            elif framework_name.lower() == 'fcitx':
                if await self._try_connect_fcitx():
                    self._current_framework = IMEFramework.FCITX  
                    self.logger.info(f"Successfully connected to Fcitx4")
                    return True
                else:
                    self.logger.warning(f"Failed to connect to Fcitx4")
                    
            elif framework_name.lower() == 'ibus':
                # Check if this is real IBus or IBus compatibility layer
                ibus_type = await self._detect_ibus_type()
                if ibus_type == 'fcitx5_compat':
                    self.logger.info("Detected Fcitx5 IBus compatibility layer, using Fcitx5 methods")
                    if await self._try_connect_fcitx5():
                        self._current_framework = IMEFramework.FCITX
                        return True
                elif ibus_type == 'real_ibus':
                    if await self._try_connect_ibus():
                        self._current_framework = IMEFramework.IBUS
                        self.logger.info(f"Successfully connected to real IBus")
                        return True
                else:
                    self.logger.warning(f"IBus type unknown or unavailable")
                    
        self.logger.error("No compatible IME framework found")
        return False
    
    async def _detect_running_frameworks(self) -> List[str]:
        """Detect which IME frameworks are actually running."""
        running = []
        
        try:
            # Check Fcitx5
            result = subprocess.run(['pgrep', '-f', 'fcitx5'], capture_output=True, timeout=1)
            if result.returncode == 0:
                running.append('fcitx5')
        except:
            pass
            
        try:
            # Check Fcitx4
            result = subprocess.run(['pgrep', '-f', 'fcitx[^5]'], capture_output=True, timeout=1)
            if result.returncode == 0:
                running.append('fcitx')
        except:
            pass
            
        try:
            # Check IBus
            result = subprocess.run(['pgrep', '-f', 'ibus-daemon'], capture_output=True, timeout=1)
            if result.returncode == 0:
                running.append('ibus')
        except:
            pass
            
        return running
    
    async def _detect_ibus_type(self) -> str:
        """Detect if IBus is real or compatibility layer."""
        try:
            # Check if Fcitx5 is running - if so, IBus is likely compat layer
            result = subprocess.run(['pgrep', '-f', 'fcitx5'], capture_output=True, timeout=1)
            if result.returncode == 0:
                return 'fcitx5_compat'
            
            # Check for real IBus daemon
            result = subprocess.run(['pgrep', '-f', 'ibus-daemon'], capture_output=True, timeout=1)
            if result.returncode == 0:
                return 'real_ibus'
                
            return 'unknown'
        except:
            return 'unknown'
    
    async def _try_connect_ibus(self) -> bool:
        """Try to connect to IBus."""
        try:
            self.logger.debug("Attempting to connect to IBus...")
            # Check if IBus service is available on DBus (may be provided by fcitx5)
            try:
                # Try to get IBus service directly via DBus
                ibus_proxy = self._bus.get_object('org.freedesktop.IBus', '/org/freedesktop/IBus')
                ibus_interface = dbus.Interface(ibus_proxy, 'org.freedesktop.IBus')
                self.logger.info("Successfully found IBus DBus service")
            except dbus.DBusException as e:
                self.logger.error(f"IBus DBus service not available: {e}")
                return False
            
            # Try to get IBus proxy
            proxy = self._bus.get_object('org.freedesktop.IBus', '/org/freedesktop/IBus')
            self._ime_proxy = dbus.Interface(proxy, 'org.freedesktop.IBus')
            
            # Test connection with a basic method call
            try:
                # Try to get current input context instead of listing engines
                current_ic = self._ime_proxy.CurrentInputContext()
                self.logger.debug(f"IBus connected, current input context: {current_ic}")
                return True
            except dbus.DBusException as e:
                self.logger.debug(f"IBus connection test failed: {e}")
                # IBus service exists but may not have expected methods
                # Still consider it connected for injection attempts
                self.logger.info("IBus service found but with different interface, proceeding anyway")
                return True
            
        except Exception as e:
            self.logger.debug(f"Failed to connect to IBus: {e}")
            return False
    
    async def _try_connect_fcitx(self) -> bool:
        """Try to connect to Fcitx."""
        try:
            # Check if Fcitx is running
            result = subprocess.run(['pgrep', '-f', 'fcitx'], 
                                  capture_output=True, text=True, timeout=1)
            if result.returncode != 0:
                self.logger.debug("Fcitx not running")
                return False
            
            # Try to get Fcitx proxy
            proxy = self._bus.get_object('org.fcitx.Fcitx', '/inputmethod')
            self._ime_proxy = dbus.Interface(proxy, 'org.fcitx.Fcitx.InputMethod')
            
            # Test connection
            current_im = self._ime_proxy.GetCurrentIM()
            self.logger.debug(f"Fcitx connected, current IM: {current_im}")
            return True
            
        except Exception as e:
            self.logger.debug(f"Failed to connect to Fcitx: {e}")
            return False
    
    async def _try_connect_fcitx5(self) -> bool:
        """Try to connect to Fcitx5."""
        try:
            # Check if Fcitx5 is running
            result = subprocess.run(['pgrep', '-f', 'fcitx5'], 
                                  capture_output=True, text=True, timeout=1)
            if result.returncode != 0:
                self.logger.debug("Fcitx5 not running")
                return False
            
            # Try to get Fcitx5 proxy
            proxy = self._bus.get_object('org.fcitx.Fcitx5', '/controller')
            self._ime_proxy = dbus.Interface(proxy, 'org.fcitx.Fcitx.Controller1')
            
            # Test connection by getting current state
            state = self._ime_proxy.State()
            current_im = self._ime_proxy.CurrentInputMethod()
            self.logger.debug(f"Fcitx5 connected, state: {state}, current IM: {current_im}")
            return True
            
        except Exception as e:
            self.logger.debug(f"Failed to connect to Fcitx5: {e}")
            return False
    
    async def _inject_text_ibus_native(self, text: str) -> bool:
        """
        Inject text through IBus using correct DBus interface.
        
        Uses the proper org.freedesktop.IBus interface with CurrentInputContext property.
        """
        try:
            if not self._bus:
                self.logger.error("DBus connection not available")
                return False
            
            # Get IBus service proxy
            ibus_proxy = self._bus.get_object('org.freedesktop.IBus', '/org/freedesktop/IBus')
            
            # Get current input context using Properties interface (correct way)
            props_interface = dbus.Interface(ibus_proxy, 'org.freedesktop.DBus.Properties')
            
            try:
                # Get CurrentInputContext property
                context_path_variant = props_interface.Get('org.freedesktop.IBus', 'CurrentInputContext')
                context_path = str(context_path_variant)
                
                if not context_path or context_path == '/' or context_path == '':
                    self.logger.error("No active IBus input context found")
                    return False
                
                self.logger.debug(f"Found IBus input context: {context_path}")
                
                # Get input context proxy
                context_proxy = self._bus.get_object('org.freedesktop.IBus', context_path)
                context_interface = dbus.Interface(context_proxy, 'org.freedesktop.IBus.InputContext')
                
                # Create proper IBus text structure
                # IBus text is a variant containing text string and attributes array
                ibus_text = dbus.Struct([
                    text,  # text string
                    dbus.Array([], signature='(iiiv)')  # attributes array (empty)
                ], signature='(sav)')
                
                # Commit text through IBus input context
                context_interface.CommitText(ibus_text)
                
                self.logger.debug(f"Text committed through IBus: {text}")
                return True
                
            except dbus.DBusException as e:
                if 'No such property' in str(e):
                    self.logger.error("IBus CurrentInputContext property not available")
                else:
                    self.logger.error(f"IBus property access failed: {e}")
                return False
            
        except Exception as e:
            self.logger.error(f"IBus injection failed: {e}")
            return False
    
    async def _inject_text_fcitx_native(self, text: str) -> bool:
        """
        Inject text through Fcitx4 native DBus API.
        
        Uses Fcitx4's InputMethod interface for direct text commitment.
        """
        try:
            if not self._ime_proxy:
                self.logger.error("Fcitx proxy not available")
                return False
            
            # Try to get input method interface
            im_interface = dbus.Interface(self._ime_proxy, 'org.fcitx.Fcitx.InputMethod')
            
            # Get current input context for proper text commitment
            current_ic = self._ime_proxy.GetCurrentIC()
            if not current_ic:
                self.logger.error("No active Fcitx input context")
                return False
                
            # Set current IC first for proper context
            im_interface.SetCurrentIC(current_ic)
            
            # Commit text through Fcitx4 native interface
            im_interface.CommitString(text)
            
            self.logger.debug(f"Text committed through Fcitx4 API: {text}")
            return True
            
        except dbus.DBusException as e:
            self.logger.error(f"Fcitx4 DBus error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Fcitx4 injection failed: {e}")
            return False
    
    async def _inject_text_fcitx5_native(self, text: str) -> bool:
        """
        Inject text through Fcitx5 using character-by-character simulation.
        
        Since direct text injection isn't available, we simulate typing by:
        1. Ensuring Fcitx5 is active
        2. Using X11 events to simulate character input
        3. Letting Fcitx5 process and forward the characters naturally
        """
        try:
            # Validate DBus connection
            if not self._bus:
                self.logger.error("DBus connection not available")
                return False
            
            # Get the Fcitx5 Controller interface
            controller_proxy = self._bus.get_object('org.fcitx.Fcitx5', '/controller')
            controller_interface = dbus.Interface(controller_proxy, 'org.fcitx.Fcitx.Controller1')
            
            # Check if Fcitx5 is available and get current state
            try:
                current_state = controller_interface.State()
                self.logger.debug(f"Fcitx5 state: {current_state} (0=closed, 1=inactive, 2=active)")
                
                # Ensure Fcitx5 is active
                if current_state != 2:  # Not active
                    controller_interface.Activate()
                    self.logger.debug("Activated Fcitx5")
                    
                # Get current input method
                current_im = controller_interface.CurrentInputMethod()
                self.logger.debug(f"Current IM: {current_im}")
                
            except dbus.DBusException as e:
                self.logger.error(f"Fcitx5 controller access failed: {e}")
                return False
            
            # Use X11 to simulate typing through the input method
            return await self._inject_via_x11_ime(text)
                
        except Exception as e:
            self.logger.error(f"Fcitx5 injection failed: {e}")
            return False
    
    async def _inject_via_x11_ime(self, text: str) -> bool:
        """
        Inject text by simulating keyboard input through X11.
        This allows the IME to process the input naturally.
        """
        try:
            import subprocess
            
            # Use xdotool to simulate typing - this goes through the IME
            for char in text:
                if ord(char) > 127:  # Non-ASCII character
                    # For Unicode characters, use key simulation
                    result = subprocess.run([
                        'xdotool', 'key', '--clearmodifiers', 
                        f'U{ord(char):04X}'
                    ], capture_output=True, timeout=1)
                else:
                    # For ASCII characters, direct type
                    result = subprocess.run([
                        'xdotool', 'type', '--clearmodifiers', char
                    ], capture_output=True, timeout=1)
                
                if result.returncode != 0:
                    self.logger.error(f"xdotool failed for character '{char}': {result.stderr}")
                    return False
                
                # Small delay between characters to ensure proper processing
                await asyncio.sleep(0.001)
            
            self.logger.debug(f"Text injected via X11 IME simulation: {text}")
            return True
            
        except FileNotFoundError:
            self.logger.error("xdotool not found - install with: sudo apt install xdotool")
            return False
        except Exception as e:
            self.logger.error(f"X11 IME simulation failed: {e}")
            return False
    
    
    
    async def _detect_ibus_ime(self) -> Optional[IMEInfo]:
        """Detect current IBus IME."""
        try:
            engines = self._ime_proxy.ListEngines()
            if engines:
                # Get first available engine as current
                engine = engines[0]
                return IMEInfo(
                    name=str(engine.get('name', 'Unknown')),
                    framework=IMEFramework.IBUS,
                    language=str(engine.get('language', 'en')),
                    is_active=True
                )
            return None
        except Exception as e:
            self.logger.debug(f"Failed to detect IBus IME: {e}")
            return None
    
    async def _detect_fcitx_ime(self) -> Optional[IMEInfo]:
        """Detect current Fcitx IME."""
        try:
            current_im = self._ime_proxy.GetCurrentIM()
            if current_im:
                return IMEInfo(
                    name=str(current_im),
                    framework=IMEFramework.FCITX,
                    language='zh',  # Assume Chinese for Fcitx
                    is_active=True
                )
            return None
        except Exception as e:
            self.logger.debug(f"Failed to detect Fcitx IME: {e}")
            return None
    
    async def _get_focus_info(self) -> Dict[str, Any]:
        """Get information about currently focused window."""
        try:
            # Use xdotool to get active window info
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True, text=True, timeout=1
            )
            
            window_title = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Try to get process name
            try:
                result = subprocess.run(
                    ['xdotool', 'getactivewindow', 'getwindowpid'],
                    capture_output=True, text=True, timeout=1
                )
                
                if result.returncode == 0:
                    pid = int(result.stdout.strip())
                    # Get process name from /proc
                    try:
                        with open(f'/proc/{pid}/comm', 'r') as f:
                            app_name = f.read().strip()
                    except:
                        app_name = "unknown"
                else:
                    app_name = "unknown"
                    
            except:
                app_name = "unknown"
            
            return {
                'window_title': window_title,
                'app_name': app_name
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to get focus info: {e}")
            return {
                'window_title': 'unknown',
                'app_name': 'unknown'
            }


class LinuxIMEStateMonitor(IMEStateMonitor):
    """Linux IME state monitor."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Linux IME state monitor."""
        super().__init__(config)
        self._adapter = LinuxIMEAdapter(config)
        self._monitor_interval = config.get('state_monitor_interval', 0.1)
    
    async def start_monitoring(self) -> None:
        """Start monitoring IME state changes."""
        if not await self._adapter.initialize():
            raise IMEInitializationError("Failed to initialize IME adapter for monitoring")
        
        self._set_monitoring(True)
        self.logger.info("Started Linux IME state monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring IME state changes."""
        self._set_monitoring(False)
        await self._adapter.cleanup()
        self.logger.info("Stopped Linux IME state monitoring")
    
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
                        process_id=0,  # TODO: Get actual PID
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
                old_status.focus_app != new_status.focus_app)