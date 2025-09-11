"""
Data models and enums for text injection system.

Defines the core data structures for the modernized text injection architecture,
including injector states, environment information, and session management.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import time


class InjectorState(Enum):
    """Text injector states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    INJECTING = "injecting"
    ERROR = "error"
    DISABLED = "disabled"


class DisplayServerType(Enum):
    """Display server types for Linux desktops."""

    WAYLAND = "wayland"
    X11 = "x11"
    UNKNOWN = "unknown"


class DesktopEnvironment(Enum):
    """Common Linux desktop environments."""

    GNOME = "gnome"
    KDE = "kde"
    XFCE = "xfce"
    GNOME_WAYLAND = "gnome-wayland"
    KDE_WAYLAND = "kde-wayland"
    SWAY = "sway"
    HYPRLAND = "hyprland"
    I3 = "i3"
    UNKNOWN = "unknown"


class InjectionMethod(Enum):
    """Available text injection methods."""

    PORTAL = "portal"
    XDOTOOL = "xdotool"
    AUTO = "auto"


@dataclass
class InjectionCapabilities:
    """Capabilities and characteristics of an injection method."""

    method: InjectionMethod
    supports_keyboard: bool = True
    supports_mouse: bool = False
    requires_permissions: bool = False
    requires_external_tools: bool = False
    platform_specific: bool = True
    description: str = ""


@dataclass
class EnvironmentInfo:
    """Information about the desktop environment and available capabilities."""

    display_server: DisplayServerType
    desktop_environment: DesktopEnvironment
    available_methods: List[InjectionMethod] = field(default_factory=list)
    desktop_session: Optional[str] = None
    wayland_display: Optional[str] = None
    x11_display: Optional[str] = None
    portal_available: bool = False
    xdotool_available: bool = False
    recommended_method: InjectionMethod = InjectionMethod.AUTO
    detection_time: float = field(default_factory=time.time)

    def __post_init__(self):
        """Validate environment information after initialization."""
        if self.portal_available and self.display_server == DisplayServerType.WAYLAND:
            self.recommended_method = InjectionMethod.PORTAL
        elif self.xdotool_available and self.display_server == DisplayServerType.X11:
            self.recommended_method = InjectionMethod.XDOTOOL
        elif self.portal_available:
            self.recommended_method = InjectionMethod.PORTAL
        elif self.xdotool_available:
            self.recommended_method = InjectionMethod.XDOTOOL


@dataclass
class PortalCapabilities:
    """xdg-desktop-portal capabilities information."""

    remote_desktop_available: bool = False
    keyboard_available: bool = False
    version: Optional[str] = None
    implementation: Optional[str] = None  # e.g., "xdg-desktop-portal-gtk"
    interfaces: List[str] = field(default_factory=list)


@dataclass
class PortalSession:
    """Portal RemoteDesktop session state."""

    session_handle: Optional[str] = None
    devices_selected: bool = False
    session_started: bool = False
    session_ready: bool = False
    bus_connection: Optional[Any] = None  # dbus.SessionBus instance
    remote_desktop_interface: Optional[Any] = None  # DBus interface
    creation_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize session state."""
        if self.session_handle and self.devices_selected and self.session_started:
            self.session_ready = True

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()


@dataclass
class InjectionResult:
    """Result of a text injection operation."""

    success: bool
    method_used: InjectionMethod
    text_length: int = 0
    injection_time: float = field(default_factory=time.time)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    error: Optional[str] = None  # Alias for error_message
    retry_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Set error alias if error_message is provided."""
        if self.error_message and not self.error:
            self.error = self.error_message


@dataclass
class InjectorStatistics:
    """Statistics for text injection operations."""

    total_injections: int = 0
    successful_injections: int = 0
    failed_injections: int = 0
    portal_injections: int = 0
    xdotool_injections: int = 0
    average_injection_time: float = 0.0
    last_injection_time: Optional[float] = None
    session_start_time: float = field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_injections == 0:
            return 0.0
        return (self.successful_injections / self.total_injections) * 100.0

    def update_success(self, method: InjectionMethod, injection_time: float):
        """Update statistics for successful injection."""
        self.total_injections += 1
        self.successful_injections += 1
        self.last_injection_time = injection_time

        if method == InjectionMethod.PORTAL:
            self.portal_injections += 1
        elif method == InjectionMethod.XDOTOOL:
            self.xdotool_injections += 1

        # Update average injection time
        if self.successful_injections > 0:
            current_avg = self.average_injection_time
            new_time = injection_time - time.time()  # Duration calculation
            self.average_injection_time = (
                current_avg * (self.successful_injections - 1) + abs(new_time)
            ) / self.successful_injections

    def update_failure(self):
        """Update statistics for failed injection."""
        self.total_injections += 1
        self.failed_injections += 1


@dataclass
class InjectorConfiguration:
    """Configuration for text injection behavior."""

    preferred_method: InjectionMethod = InjectionMethod.AUTO
    portal_timeout: float = 30.0
    xdotool_delay: float = 0.02
    inject_delay: float = 0.1  # General injection delay
    retry_attempts: int = 3
    retry_delay: float = 0.5
    fallback_enabled: bool = True
    performance_monitoring: bool = True
    debug_logging: bool = False

    def __post_init__(self):
        """Validate configuration values."""
        if self.portal_timeout <= 0:
            self.portal_timeout = 30.0
        if self.xdotool_delay < 0:
            self.xdotool_delay = 0.02
        if self.inject_delay < 0:
            self.inject_delay = 0.1
        if self.retry_attempts < 0:
            self.retry_attempts = 3


@dataclass
class SystemCompatibility:
    """System compatibility information for debugging."""

    platform: str
    python_version: str
    dbus_available: bool = False
    glib_available: bool = False
    xdotool_path: Optional[str] = None
    portal_services: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def detect(cls) -> "SystemCompatibility":
        """Detect system compatibility information."""
        import platform
        import sys
        import shutil
        import os

        # Detect xdotool
        xdotool_path = shutil.which("xdotool")

        # Check for dbus and glib availability
        dbus_available = False
        glib_available = False

        try:
            import dbus

            dbus_available = True
        except ImportError:
            pass

        try:
            import gi

            gi.require_version("GLib", "2.0")
            from gi.repository import GLib

            glib_available = True
        except (ImportError, ValueError):
            pass

        # Collect relevant environment variables
        env_vars = {
            key: os.environ.get(key, "")
            for key in [
                "XDG_SESSION_TYPE",
                "XDG_CURRENT_DESKTOP",
                "WAYLAND_DISPLAY",
                "DISPLAY",
                "DESKTOP_SESSION",
                "GDMSESSION",
            ]
            if os.environ.get(key)
        }

        return cls(
            platform=platform.system(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            dbus_available=dbus_available,
            glib_available=glib_available,
            xdotool_path=xdotool_path,
            environment_variables=env_vars,
        )
