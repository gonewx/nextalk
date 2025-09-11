"""
Environment detection for text injection system.

Detects desktop environment, display server, and available capabilities
to enable optimal injection strategy selection.
"""

import os
import shutil
import subprocess
import logging
import time
from typing import Optional, Dict, Any, List

from .injection_models import (
    EnvironmentInfo,
    DisplayServerType,
    DesktopEnvironment,
    InjectionMethod,
    PortalCapabilities,
    SystemCompatibility,
)
from .injection_exceptions import EnvironmentError


logger = logging.getLogger(__name__)


class EnvironmentDetector:
    """
    Detects and analyzes the desktop environment and available capabilities.

    This class provides comprehensive detection of:
    - Display server type (Wayland/X11)
    - Desktop environment (GNOME, KDE, etc.)
    - Portal service availability and capabilities
    - xdotool availability and functionality
    """

    def __init__(self):
        """Initialize the environment detector."""
        self._cached_info: Optional[EnvironmentInfo] = None
        self._cached_portal_caps: Optional[PortalCapabilities] = None
        self._cache_valid = False

    def detect_environment(self, force_refresh: bool = False) -> EnvironmentInfo:
        """
        Detect comprehensive environment information.

        Args:
            force_refresh: If True, bypass cache and re-detect

        Returns:
            EnvironmentInfo with complete environment details

        Raises:
            EnvironmentError: If critical environment detection fails
        """
        if self._cached_info and not force_refresh and self._cache_valid:
            return self._cached_info

        try:
            logger.debug("Starting environment detection")

            # Detect display server
            display_server = self._detect_display_server()
            logger.debug(f"Display server: {display_server.value}")

            # Detect desktop environment
            desktop_env = self._detect_desktop_environment()
            logger.debug(f"Desktop environment: {desktop_env.value}")

            # Get session information
            session_info = self._get_session_info()

            # Check capabilities
            portal_available = self._check_portal_availability()
            xdotool_available = self._check_xdotool_availability()

            logger.debug(f"Portal available: {portal_available}")
            logger.debug(f"xdotool available: {xdotool_available}")

            # Build available methods list based on capabilities
            available_methods = []
            if portal_available:
                available_methods.append(InjectionMethod.PORTAL)
            if xdotool_available:
                available_methods.append(InjectionMethod.XDOTOOL)

            # Build environment info
            current_time = time.time()
            env_info = EnvironmentInfo(
                display_server=display_server,
                desktop_environment=desktop_env,
                available_methods=available_methods,
                desktop_session=session_info.get("desktop_session"),
                wayland_display=session_info.get("wayland_display"),
                x11_display=session_info.get("x11_display"),
                portal_available=portal_available,
                xdotool_available=xdotool_available,
                detection_time=current_time,
            )

            # Cache the result
            self._cached_info = env_info
            self._cache_valid = True

            logger.info(f"Environment detection complete: {env_info.recommended_method.value}")
            return env_info

        except Exception as e:
            logger.error(f"Environment detection failed: {e}")
            raise EnvironmentError("Failed to detect environment") from e

    def _detect_display_server(self) -> DisplayServerType:
        """Detect the display server type (Wayland/X11)."""
        # Check for Wayland first
        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        wayland_display = os.environ.get("WAYLAND_DISPLAY")

        if session_type == "wayland" or wayland_display:
            return DisplayServerType.WAYLAND

        # Check for X11
        x11_display = os.environ.get("DISPLAY")
        if x11_display or session_type == "x11":
            return DisplayServerType.X11

        # Additional checks for edge cases
        if self._check_wayland_compositor():
            return DisplayServerType.WAYLAND

        if self._check_x11_server():
            return DisplayServerType.X11

        return DisplayServerType.UNKNOWN

    def _detect_desktop_environment(self) -> DesktopEnvironment:
        """Detect the desktop environment."""
        # Check XDG_CURRENT_DESKTOP
        current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        if "gnome" in current_desktop:
            # Check if it's Wayland GNOME
            if self._detect_display_server() == DisplayServerType.WAYLAND:
                return DesktopEnvironment.GNOME_WAYLAND
            return DesktopEnvironment.GNOME

        if "kde" in current_desktop or "plasma" in current_desktop:
            if self._detect_display_server() == DisplayServerType.WAYLAND:
                return DesktopEnvironment.KDE_WAYLAND
            return DesktopEnvironment.KDE

        if "xfce" in current_desktop:
            return DesktopEnvironment.XFCE

        # Check for tiling window managers
        if "sway" in current_desktop or self._check_process("sway"):
            return DesktopEnvironment.SWAY

        if "hyprland" in current_desktop or self._check_process("Hyprland"):
            return DesktopEnvironment.HYPRLAND

        if "i3" in current_desktop or self._check_process("i3"):
            return DesktopEnvironment.I3

        # Fallback checks using other environment variables
        desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()
        gdm_session = os.environ.get("GDMSESSION", "").lower()

        for session in [desktop_session, gdm_session]:
            if "gnome" in session:
                return DesktopEnvironment.GNOME
            if "kde" in session or "plasma" in session:
                return DesktopEnvironment.KDE
            if "xfce" in session:
                return DesktopEnvironment.XFCE

        return DesktopEnvironment.UNKNOWN

    def _get_session_info(self) -> Dict[str, Optional[str]]:
        """Get detailed session information."""
        return {
            "desktop_session": os.environ.get("DESKTOP_SESSION"),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY"),
            "x11_display": os.environ.get("DISPLAY"),
            "xdg_session_type": os.environ.get("XDG_SESSION_TYPE"),
            "xdg_current_desktop": os.environ.get("XDG_CURRENT_DESKTOP"),
            "gdm_session": os.environ.get("GDMSESSION"),
        }

    def _check_portal_availability(self) -> bool:
        """Check if xdg-desktop-portal is available and functional."""
        try:
            # Check if dbus is available
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop

            # Set up dbus connection
            bus = dbus.SessionBus()

            # Try to get the portal service
            portal = bus.get_object(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
            )

            # Check if RemoteDesktop interface is available
            remote_desktop = dbus.Interface(portal, "org.freedesktop.portal.RemoteDesktop")

            logger.debug("Portal service is available")
            return True

        except ImportError:
            logger.debug("dbus module not available")
            return False
        except Exception as e:
            logger.debug(f"Portal check failed: {e}")
            return False

    def _check_xdotool_availability(self) -> bool:
        """Check if xdotool is available and functional."""
        try:
            # Check if xdotool binary exists
            xdotool_path = shutil.which("xdotool")
            if not xdotool_path:
                return False

            # Test basic xdotool functionality
            result = subprocess.run(
                ["xdotool", "--version"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                logger.debug(f"xdotool available: {result.stdout.strip()}")
                return True

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"xdotool check failed: {e}")

        return False

    def _check_wayland_compositor(self) -> bool:
        """Check for running Wayland compositor."""
        compositors = ["sway", "Hyprland", "kwin_wayland", "gnome-shell"]

        for compositor in compositors:
            if self._check_process(compositor):
                return True

        return False

    def _check_x11_server(self) -> bool:
        """Check for running X11 server."""
        return self._check_process("Xorg") or self._check_process("X")

    def _check_process(self, process_name: str) -> bool:
        """Check if a process is running."""
        try:
            result = subprocess.run(["pgrep", "-f", process_name], capture_output=True, timeout=3)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _get_available_methods(self) -> List[InjectionMethod]:
        """Get list of available injection methods based on current environment."""
        methods = []
        
        # Check portal availability
        if self._check_portal_availability():
            methods.append(InjectionMethod.PORTAL)
            
        # Check xdotool availability  
        if self._check_xdotool_availability():
            methods.append(InjectionMethod.XDOTOOL)
            
        return methods

    def get_preferred_method(self, env_info: EnvironmentInfo, user_preference: Optional[InjectionMethod] = None) -> Optional[InjectionMethod]:
        """
        Get the preferred injection method for the given environment.
        
        Args:
            env_info: Environment information
            user_preference: User's preferred method (if any)
            
        Returns:
            Preferred injection method or None if none available
        """
        # If user has a preference and it's available, use it
        if user_preference and user_preference in env_info.available_methods:
            return user_preference
            
        # Use environment-based preference logic
        if env_info.display_server == DisplayServerType.WAYLAND:
            if InjectionMethod.PORTAL in env_info.available_methods:
                return InjectionMethod.PORTAL
            elif InjectionMethod.XDOTOOL in env_info.available_methods:
                return InjectionMethod.XDOTOOL
        elif env_info.display_server == DisplayServerType.X11:
            if InjectionMethod.XDOTOOL in env_info.available_methods:
                return InjectionMethod.XDOTOOL
            elif InjectionMethod.PORTAL in env_info.available_methods:
                return InjectionMethod.PORTAL
                
        # Fallback to any available method
        if env_info.available_methods:
            return env_info.available_methods[0]
            
        return None

    def is_method_suitable(self, method: InjectionMethod, env_info: EnvironmentInfo) -> bool:
        """
        Check if an injection method is suitable for the given environment.
        
        Args:
            method: Injection method to check
            env_info: Environment information
            
        Returns:
            True if method is suitable and available
        """
        return method in env_info.available_methods

    def get_portal_capabilities(self) -> PortalCapabilities:
        """Get detailed Portal capabilities."""
        if self._cached_portal_caps and self._cache_valid:
            return self._cached_portal_caps

        capabilities = PortalCapabilities()

        try:
            import dbus

            bus = dbus.SessionBus()
            portal = bus.get_object(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
            )

            # Get available interfaces
            introspect = dbus.Interface(portal, "org.freedesktop.DBus.Introspectable")
            xml_data = introspect.Introspect()

            capabilities.remote_desktop_available = "RemoteDesktop" in xml_data
            capabilities.keyboard_available = capabilities.remote_desktop_available

            if "RemoteDesktop" in xml_data:
                capabilities.interfaces.append("org.freedesktop.portal.RemoteDesktop")

            # Try to get implementation information
            try:
                props = dbus.Interface(portal, "org.freedesktop.DBus.Properties")
                version = props.Get("org.freedesktop.portal.Desktop", "version")
                capabilities.version = str(version)
            except:
                pass

            self._cached_portal_caps = capabilities

        except Exception as e:
            logger.debug(f"Portal capabilities check failed: {e}")

        return capabilities

    def get_system_compatibility(self) -> SystemCompatibility:
        """Get comprehensive system compatibility information."""
        return SystemCompatibility.detect()

    def validate_environment(self, env_info: Optional[EnvironmentInfo] = None) -> bool:
        """
        Validate that the environment supports text injection.

        Args:
            env_info: Environment info to validate, or None to detect

        Returns:
            True if environment supports text injection

        Raises:
            EnvironmentError: If environment is incompatible
        """
        if env_info is None:
            env_info = self.detect_environment()

        # Check if any injection method is available
        if not env_info.portal_available and not env_info.xdotool_available:
            raise EnvironmentError(
                "No text injection methods available. Install xdotool or enable Portal support.",
                {"portal_available": False, "xdotool_available": False},
            )

        # Warn about suboptimal configurations
        if env_info.display_server == DisplayServerType.WAYLAND and not env_info.portal_available:
            logger.warning(
                "Running on Wayland but Portal not available. "
                "Text injection may not work properly."
            )

        if env_info.display_server == DisplayServerType.X11 and not env_info.xdotool_available:
            logger.warning(
                "Running on X11 but xdotool not available. "
                "Install xdotool for better compatibility."
            )

        return True

    def clear_cache(self):
        """Clear cached detection results."""
        self._cached_info = None
        self._cached_portal_caps = None
        self._cache_valid = False
        logger.debug("Environment detection cache cleared")

    def get_debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information about the environment."""
        env_info = self.detect_environment()
        portal_caps = self.get_portal_capabilities()
        system_compat = self.get_system_compatibility()

        return {
            "environment": {
                "display_server": env_info.display_server.value,
                "desktop_environment": env_info.desktop_environment.value,
                "recommended_method": env_info.recommended_method.value,
                "portal_available": env_info.portal_available,
                "xdotool_available": env_info.xdotool_available,
            },
            "portal_capabilities": {
                "remote_desktop_available": portal_caps.remote_desktop_available,
                "keyboard_available": portal_caps.keyboard_available,
                "version": portal_caps.version,
                "interfaces": portal_caps.interfaces,
            },
            "system_compatibility": {
                "platform": system_compat.platform,
                "python_version": system_compat.python_version,
                "dbus_available": system_compat.dbus_available,
                "glib_available": system_compat.glib_available,
                "xdotool_path": system_compat.xdotool_path,
            },
            "environment_variables": system_compat.environment_variables,
        }


# Singleton instance for global access
_detector_instance: Optional[EnvironmentDetector] = None


def get_environment_detector() -> EnvironmentDetector:
    """Get the global environment detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EnvironmentDetector()
    return _detector_instance


def detect_environment() -> EnvironmentInfo:
    """Convenience function to detect environment information."""
    return get_environment_detector().detect_environment()


def validate_environment() -> bool:
    """Convenience function to validate environment compatibility."""
    return get_environment_detector().validate_environment()
