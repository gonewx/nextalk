"""
Portal-based text injection implementation.

Provides text injection through xdg-desktop-portal RemoteDesktop interface,
designed for modern Wayland desktop environments with proper permission handling.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from .base_injector import BaseInjector, InjectorCapabilities
from .injection_models import (
    InjectorState,
    InjectionResult,
    InjectionMethod,
    PortalSession,
    InjectorConfiguration,
)
from .injection_exceptions import (
    PortalError,
    PortalConnectionError,
    PortalPermissionError,
    PortalSessionError,
    PortalTimeoutError,
    InjectionFailedError,
    DependencyError,
    InitializationError,
)

# Initialize D-Bus main loop at module import time (like final_portal_test.py)
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    
    # Set up D-Bus main loop as default immediately
    DBusGMainLoop(set_as_default=True)
    _dbus_available = True
except ImportError:
    _dbus_available = False


logger = logging.getLogger(__name__)


class PortalInjector(BaseInjector):
    """
    Text injector implementation using xdg-desktop-portal RemoteDesktop.

    This implementation provides text injection for modern Wayland desktop
    environments through the standardized Portal interface, with proper
    permission handling and session management.
    """

    def __init__(self, config: Optional[InjectorConfiguration] = None):
        """
        Initialize Portal injector.

        Args:
            config: Injector configuration
        """
        super().__init__(config)
        self._portal_session: Optional[PortalSession] = None
        self._dbus_bus = None
        self._remote_desktop_interface = None
        self._session_callbacks: Dict[str, Callable] = {}
        self._glib_mainloop = None
        self._glib_thread = None
        self._dbus_main_loop = None

        # Portal-specific configuration
        self._portal_timeout = getattr(config, "portal_timeout", 30.0) if config else 30.0

        self._logger.debug("Portal injector created")

    @property
    def capabilities(self) -> InjectorCapabilities:
        """Get Portal injector capabilities."""
        return InjectorCapabilities(
            method=InjectionMethod.PORTAL,
            supports_keyboard=True,
            supports_mouse=False,  # Not implemented yet
            requires_permissions=True,
            requires_external_tools=False,
            platform_specific=True,
            description="xdg-desktop-portal RemoteDesktop text injection",
        )

    @property
    def method(self) -> InjectionMethod:
        """Get injection method."""
        return InjectionMethod.PORTAL

    @property
    def session_ready(self) -> bool:
        """Check if Portal session is ready."""
        return self._portal_session is not None and self._portal_session.session_ready

    async def initialize(self) -> bool:
        """
        Initialize Portal injector.

        Returns:
            True if initialization successful

        Raises:
            InitializationError: If initialization fails
        """
        if self.is_initialized:
            return True

        await self._set_state(InjectorState.INITIALIZING)

        try:
            self._logger.info("Initializing Portal injector")

            # Check dependencies
            await self._check_dependencies()

            # Connect to DBus
            await self._connect_dbus()

            # Create Portal session
            await self._create_portal_session()

            await self._set_state(InjectorState.READY)
            self._logger.info("Portal injector initialized successfully")
            return True

        except Exception as e:
            await self._set_state(InjectorState.ERROR)
            self._logger.error(f"Portal injector initialization failed: {e}")
            raise InitializationError(
                "Portal injector initialization failed", "PortalInjector", e
            ) from e

    async def cleanup(self) -> None:
        """Clean up Portal injector resources."""
        try:
            self._logger.info("Cleaning up Portal injector")

            # Close Portal session
            if self._portal_session:
                await self._close_portal_session()

            # Stop GLib main loop
            if self._glib_mainloop and self._glib_mainloop.is_running():
                self._glib_mainloop.quit()
                
            # Wait for thread to finish
            if self._glib_thread and self._glib_thread.is_alive():
                self._glib_thread.join(timeout=2.0)

            # Cleanup DBus connection
            self._remote_desktop_interface = None
            if self._dbus_bus:
                # DBus bus cleanup is handled by the library
                self._dbus_bus = None

            # Reset GLib resources
            self._glib_mainloop = None
            self._glib_thread = None

            await self._set_state(InjectorState.UNINITIALIZED)
            self._logger.info("Portal injector cleanup complete")

        except Exception as e:
            self._logger.warning(f"Error during Portal cleanup: {e}")

    async def inject_text(self, text: str) -> InjectionResult:
        """
        Inject text using Portal RemoteDesktop.

        Args:
            text: Text to inject

        Returns:
            InjectionResult with operation details

        Raises:
            InjectionFailedError: If injection fails
        """
        start_time = time.time()

        try:
            # Validate text
            validated_text = await self._validate_text(text)

            # Check session readiness
            if not self.session_ready:
                raise InjectionFailedError(
                    "Portal session not ready for injection",
                    text=validated_text,
                    method=self.method.value,
                )

            # Perform text injection
            await self._inject_text_portal(validated_text)

            # Build successful result
            result = InjectionResult(
                success=True,
                method_used=self.method,
                text_length=len(validated_text),
                injection_time=start_time,
                performance_metrics={
                    "duration": time.time() - start_time,
                    "characters_per_second": len(validated_text) / (time.time() - start_time),
                },
            )

            self._logger.debug(f"Portal injection successful: {len(validated_text)} characters")
            return result

        except Exception as e:
            self._logger.error(f"Portal text injection failed: {e}")
            raise InjectionFailedError(
                f"Portal text injection failed: {e}", text=text, method=self.method.value
            ) from e

    async def test_injection(self) -> bool:
        """
        Test Portal text injection.

        Returns:
            True if test successful
        """
        try:
            test_text = "Portal test"
            result = await self.inject_text(test_text)
            return result.success
        except Exception as e:
            self._logger.debug(f"Portal test injection failed: {e}")
            return False

    async def check_availability(self) -> bool:
        """
        Check if Portal injector is available.

        Returns:
            True if Portal is available
        """
        try:
            # Check dependencies
            await self._check_dependencies()

            # Try to connect to Portal service
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop

            bus = dbus.SessionBus()
            portal = bus.get_object(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
            )

            # Check if RemoteDesktop interface is available
            remote_desktop = dbus.Interface(portal, "org.freedesktop.portal.RemoteDesktop")

            self._logger.debug("Portal RemoteDesktop interface available")
            return True

        except Exception as e:
            self._logger.debug(f"Portal availability check failed: {e}")
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """Get Portal injector health status."""
        status = {
            "portal_connected": self._dbus_bus is not None,
            "session_exists": self._portal_session is not None,
            "session_ready": self.session_ready,
            "dependencies_ok": False,
        }

        # Check dependencies
        try:
            await self._check_dependencies()
            status["dependencies_ok"] = True
        except Exception as e:
            status["dependency_error"] = str(e)

        # Session details
        if self._portal_session:
            status.update(
                {
                    "session_handle": self._portal_session.session_handle,
                    "devices_selected": self._portal_session.devices_selected,
                    "session_started": self._portal_session.session_started,
                    "session_age": time.time() - self._portal_session.creation_time,
                }
            )

        return status

    # Private implementation methods

    async def _check_dependencies(self) -> None:
        """Check required dependencies."""
        try:
            import dbus
            import gi

            gi.require_version("GLib", "2.0")
            from gi.repository import GLib
            from dbus.mainloop.glib import DBusGMainLoop

        except ImportError as e:
            raise DependencyError(
                "Required Portal dependencies not available",
                str(e).split()[-1],
                "Install python3-dbus and python3-gi",
            ) from e

    async def _connect_dbus(self) -> None:
        """Connect to DBus and Portal service."""
        try:
            if not _dbus_available:
                raise ImportError("D-Bus modules not available")
                
            import gi
            gi.require_version("GLib", "2.0")
            from gi.repository import GLib
            import threading

            # Connect to session bus (main loop already set as default at module level)
            self._dbus_bus = dbus.SessionBus()

            # Get Portal object
            portal = self._dbus_bus.get_object(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
            )

            # Create RemoteDesktop interface
            self._remote_desktop_interface = dbus.Interface(
                portal, "org.freedesktop.portal.RemoteDesktop"
            )
            
            # Create and start GLib main loop in a separate thread (similar to final_portal_test.py)
            self._glib_mainloop = GLib.MainLoop()
            self._glib_thread = threading.Thread(
                target=self._glib_mainloop.run, daemon=True
            )
            self._glib_thread.start()
            
            # Wait a moment for the main loop to start
            await asyncio.sleep(0.1)

            self._logger.debug("Connected to Portal RemoteDesktop interface with module-level D-Bus main loop")

        except Exception as e:
            raise PortalConnectionError(f"Failed to connect to Portal service: {e}") from e

    async def _create_portal_session(self) -> None:
        """Create Portal RemoteDesktop session."""
        try:
            self._logger.info("Creating Portal session (permission dialog will appear)")

            # Initialize session data
            self._portal_session = PortalSession()
            session_future = asyncio.Future()
            loop = asyncio.get_running_loop()

            def handle_session_response(response_code, results):
                """Handle session creation response - thread safe callback."""
                def set_result():
                    try:
                        self._logger.debug(f"Session response: code={response_code}, results={results}")

                        if response_code == 0:
                            session_handle = results.get("session_handle")
                            if session_handle:
                                self._portal_session.session_handle = session_handle
                                self._logger.debug(f"Session created: {session_handle}")
                                if not session_future.done():
                                    session_future.set_result(True)
                            else:
                                if not session_future.done():
                                    session_future.set_exception(
                                        PortalSessionError("No session handle received")
                                    )
                        elif response_code == 1:
                            if not session_future.done():
                                session_future.set_exception(
                                    PortalPermissionError("User denied Portal permissions")
                                )
                        else:
                            if not session_future.done():
                                session_future.set_exception(
                                    PortalSessionError(f"Session creation failed: {response_code}")
                                )

                    except Exception as e:
                        if not session_future.done():
                            session_future.set_exception(e)

                # Schedule callback in asyncio loop
                loop.call_soon_threadsafe(set_result)

            # Create session request
            import dbus

            options = dbus.Dictionary(
                {
                    "handle_token": dbus.String("session_token"),
                    "session_handle_token": dbus.String("session_handle_token"),
                },
                signature="sv",
            )

            request_path = self._remote_desktop_interface.CreateSession(options)
            self._logger.debug(f"Session request: {request_path}")
            
            # Validate request path before using it
            if not request_path or not isinstance(request_path, str) or not request_path.startswith('/'):
                raise PortalSessionError(f"Invalid request path returned: {request_path}")

            # Listen for response
            try:
                request_obj = self._dbus_bus.get_object("org.freedesktop.portal.Desktop", request_path)
                request_obj.connect_to_signal("Response", handle_session_response)
            except Exception as e:
                raise PortalSessionError(f"Failed to connect to request signal for path {request_path}: {e}")

            # Wait for session creation with timeout
            await asyncio.wait_for(session_future, timeout=self._portal_timeout)

            # Proceed with device selection and session start
            await self._select_devices()
            await self._start_session()

        except asyncio.TimeoutError:
            raise PortalTimeoutError(
                "Portal session creation timed out", "CreateSession", self._portal_timeout
            )
        except Exception as e:
            raise PortalSessionError(f"Portal session creation failed: {e}") from e

    async def _select_devices(self) -> None:
        """Select keyboard devices for the session."""
        device_future = asyncio.Future()
        loop = asyncio.get_running_loop()

        def handle_devices_response(response_code, results):
            """Handle device selection response - thread safe."""
            def set_result():
                try:
                    if response_code == 0:
                        self._portal_session.devices_selected = True
                        if not device_future.done():
                            device_future.set_result(True)
                    else:
                        if not device_future.done():
                            device_future.set_exception(
                                PortalSessionError(f"Device selection failed: {response_code}")
                            )
                except Exception as e:
                    if not device_future.done():
                        device_future.set_exception(e)
                        
            loop.call_soon_threadsafe(set_result)

        try:
            import dbus

            options = dbus.Dictionary(
                {
                    "handle_token": dbus.String("select_devices_token"),
                    "types": dbus.UInt32(1),  # Keyboard
                    "multiple": dbus.Boolean(False),
                },
                signature="sv",
            )

            request_path = self._remote_desktop_interface.SelectDevices(
                self._portal_session.session_handle, options
            )
            
            # Validate request path before using it
            if not request_path or not isinstance(request_path, str) or not request_path.startswith('/'):
                raise PortalSessionError(f"Invalid request path returned for SelectDevices: {request_path}")

            # Listen for response
            try:
                request_obj = self._dbus_bus.get_object("org.freedesktop.portal.Desktop", request_path)
                request_obj.connect_to_signal("Response", handle_devices_response)
            except Exception as e:
                raise PortalSessionError(f"Failed to connect to SelectDevices signal for path {request_path}: {e}")

            await asyncio.wait_for(device_future, timeout=self._portal_timeout)
            self._logger.debug("Device selection completed")

        except asyncio.TimeoutError:
            raise PortalTimeoutError(
                "Device selection timed out", "SelectDevices", self._portal_timeout
            )

    async def _start_session(self) -> None:
        """Start the Portal session."""
        start_future = asyncio.Future()
        loop = asyncio.get_running_loop()

        def handle_start_response(response_code, results):
            """Handle session start response - thread safe."""
            def set_result():
                try:
                    if response_code == 0:
                        self._portal_session.session_started = True
                        self._portal_session.session_ready = True
                        if not start_future.done():
                            start_future.set_result(True)
                    else:
                        if not start_future.done():
                            start_future.set_exception(
                                PortalSessionError(f"Session start failed: {response_code}")
                            )
                except Exception as e:
                    if not start_future.done():
                        start_future.set_exception(e)
                        
            loop.call_soon_threadsafe(set_result)

        try:
            import dbus

            options = dbus.Dictionary(
                {"handle_token": dbus.String("start_session_token")}, signature="sv"
            )

            request_path = self._remote_desktop_interface.Start(
                self._portal_session.session_handle, "", options  # parent_window
            )
            
            # Validate request path before using it
            if not request_path or not isinstance(request_path, str) or not request_path.startswith('/'):
                raise PortalSessionError(f"Invalid request path returned for Start: {request_path}")

            # Listen for response
            try:
                request_obj = self._dbus_bus.get_object("org.freedesktop.portal.Desktop", request_path)
                request_obj.connect_to_signal("Response", handle_start_response)
            except Exception as e:
                raise PortalSessionError(f"Failed to connect to Start signal for path {request_path}: {e}")

            await asyncio.wait_for(start_future, timeout=self._portal_timeout)
            self._logger.info("Portal session started successfully")

        except asyncio.TimeoutError:
            raise PortalTimeoutError("Session start timed out", "Start", self._portal_timeout)

    async def _inject_text_portal(self, text: str) -> None:
        """Inject text through Portal keyboard events."""
        if not self.session_ready:
            raise PortalSessionError("Portal session not ready")

        try:
            import dbus
            import subprocess

            # Check if text contains non-ASCII characters (like Chinese)
            has_non_ascii = any(ord(char) > 127 for char in text)
            self._logger.info(f"Portal injection: text='{text}', has_non_ascii={has_non_ascii}")
            
            if has_non_ascii:
                # For non-ASCII text (Chinese, etc), use clipboard paste method
                self._logger.info(f"Using clipboard paste for non-ASCII text: {text}")
                
                # Copy text to clipboard
                clipboard_success = False
                try:
                    # Try wl-copy for Wayland
                    self._logger.debug("Trying wl-copy for clipboard...")
                    process = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
                    process.communicate(input=text.encode('utf-8'), timeout=1)
                    if process.returncode == 0:
                        clipboard_success = True
                        self._logger.info("Successfully copied to clipboard with wl-copy")
                    else:
                        raise Exception(f"wl-copy failed with code {process.returncode}")
                except (FileNotFoundError, Exception) as e1:
                    # Fallback to xclip for X11
                    self._logger.debug(f"wl-copy failed: {e1}, trying xclip...")
                    try:
                        process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                        process.communicate(input=text.encode('utf-8'), timeout=1)
                        if process.returncode == 0:
                            clipboard_success = True
                            self._logger.info("Successfully copied to clipboard with xclip")
                        else:
                            raise Exception(f"xclip failed with code {process.returncode}")
                    except (FileNotFoundError, Exception) as e2:
                        self._logger.error(f"Both clipboard tools failed - wl-copy: {e1}, xclip: {e2}")
                        raise InjectionFailedError("No clipboard tool available (wl-copy or xclip)")
                
                if not clipboard_success:
                    raise InjectionFailedError("Failed to copy text to clipboard")
                
                # Detect if we should use terminal paste (Ctrl+Shift+V) or normal paste (Ctrl+V)
                await asyncio.sleep(0.1)  # Small delay for clipboard to update
                
                # Try to detect if active window is a terminal
                is_terminal = await self._detect_terminal_window()
                
                if is_terminal:
                    self._logger.info("Terminal detected, sending Ctrl+Shift+V...")
                    await self._send_terminal_paste()
                else:
                    self._logger.info("Non-terminal app detected, sending Ctrl+V...")
                    await self._send_normal_paste()
                
                self._logger.info(f"Pasted {len(text)} characters via clipboard")
                
            else:
                # For ASCII text, inject character by character
                self._logger.debug(f"Using character injection for ASCII text: {text}")
                
                for char in text:
                    keysym = ord(char)

                    # Key press
                    self._remote_desktop_interface.NotifyKeyboardKeysym(
                        self._portal_session.session_handle,
                        dbus.Dictionary({}, signature="sv"),
                        dbus.Int32(keysym),
                        dbus.UInt32(1),  # pressed
                    )

                    # Small delay for natural typing
                    await asyncio.sleep(0.02)

                    # Key release
                    self._remote_desktop_interface.NotifyKeyboardKeysym(
                        self._portal_session.session_handle,
                        dbus.Dictionary({}, signature="sv"),
                        dbus.Int32(keysym),
                        dbus.UInt32(0),  # released
                    )

                    await asyncio.sleep(0.02)
                
                self._logger.debug(f"Injected {len(text)} ASCII characters via Portal")

            # Update session activity
            self._portal_session.update_activity()

        except Exception as e:
            raise InjectionFailedError(f"Portal text injection failed: {e}") from e

    async def _detect_terminal_window(self) -> bool:
        """
        Detect if the active window is a terminal application.
        
        Returns:
            True if terminal detected, False otherwise
        """
        try:
            import subprocess
            
            # Try to get active window class (works on X11/Xwayland)
            try:
                # Get active window info using xprop
                result = subprocess.run(
                    ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                    capture_output=True, text=True, timeout=0.5
                )
                if result.returncode == 0 and 'window id' in result.stdout:
                    # Extract window ID
                    window_id = result.stdout.split()[-1]
                    
                    # Get window class
                    result = subprocess.run(
                        ['xprop', '-id', window_id, 'WM_CLASS'],
                        capture_output=True, text=True, timeout=0.5
                    )
                    if result.returncode == 0:
                        window_class = result.stdout.lower()
                        # Check for common terminal identifiers
                        terminal_apps = [
                            'terminal', 'konsole', 'gnome-terminal', 'xterm',
                            'terminator', 'tilix', 'alacritty', 'kitty', 
                            'urxvt', 'rxvt', 'termite', 'st', 'wezterm'
                        ]
                        is_terminal = any(term in window_class for term in terminal_apps)
                        self._logger.debug(f"Window class: {window_class}, is_terminal: {is_terminal}")
                        return is_terminal
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # Fallback: check if $TERM is set (we're likely in a terminal)
            import os
            if os.environ.get('TERM'):
                self._logger.debug("$TERM environment variable detected, assuming terminal")
                return True
                
            # Default to False (safer for non-terminal apps)
            return False
            
        except Exception as e:
            self._logger.debug(f"Terminal detection failed: {e}, defaulting to non-terminal")
            return False
    
    async def _send_terminal_paste(self) -> None:
        """Send Ctrl+Shift+V for terminal paste."""
        import dbus
        
        # Ctrl key press
        ctrl_keysym = 0xffe3  # Left Control
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(ctrl_keysym),
            dbus.UInt32(1),  # pressed
        )
        await asyncio.sleep(0.05)
        
        # Shift key press
        shift_keysym = 0xffe1  # Left Shift
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(shift_keysym),
            dbus.UInt32(1),  # pressed
        )
        await asyncio.sleep(0.05)
        
        # V key press
        v_keysym = ord('v')
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(v_keysym),
            dbus.UInt32(1),  # pressed
        )
        await asyncio.sleep(0.05)
        
        # Release V
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(v_keysym),
            dbus.UInt32(0),  # released
        )
        await asyncio.sleep(0.05)
        
        # Release Shift
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(shift_keysym),
            dbus.UInt32(0),  # released
        )
        await asyncio.sleep(0.05)
        
        # Release Ctrl
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(ctrl_keysym),
            dbus.UInt32(0),  # released
        )
    
    async def _send_normal_paste(self) -> None:
        """Send Ctrl+V for normal application paste."""
        import dbus
        
        # Ctrl key press
        ctrl_keysym = 0xffe3  # Left Control
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(ctrl_keysym),
            dbus.UInt32(1),  # pressed
        )
        await asyncio.sleep(0.05)
        
        # V key press
        v_keysym = ord('v')
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(v_keysym),
            dbus.UInt32(1),  # pressed
        )
        await asyncio.sleep(0.05)
        
        # Release V
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(v_keysym),
            dbus.UInt32(0),  # released
        )
        await asyncio.sleep(0.05)
        
        # Release Ctrl
        self._remote_desktop_interface.NotifyKeyboardKeysym(
            self._portal_session.session_handle,
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(ctrl_keysym),
            dbus.UInt32(0),  # released
        )

    async def _close_portal_session(self) -> None:
        """Close the Portal session."""
        if not self._portal_session or not self._portal_session.session_handle:
            return

        try:
            # Portal sessions are automatically cleaned up by the service
            # We just need to reset our state
            self._portal_session = None
            self._logger.debug("Portal session closed")

        except Exception as e:
            self._logger.warning(f"Error closing Portal session: {e}")
