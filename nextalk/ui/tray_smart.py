"""
Smart system tray manager for NexTalk.

Automatically selects the best tray implementation based on the current environment.
"""

import logging
import sys
from enum import Enum
from typing import Optional, Callable, Any, Type

logger = logging.getLogger(__name__)


# Import TrayStatus from main tray module to ensure consistency
from .tray import TrayStatus


def detect_gtk_environment():
    """
    Detect the current GTK environment and available backends.
    
    Returns:
        dict: Environment information including GTK version, AppIndicator support, etc.
    """
    env_info = {
        'gtk_loaded': False,
        'gtk_version': None,
        'gtk3_available': False,
        'gtk4_available': False,
        'appindicator_available': False,
        'pystray_available': False,
        'recommended_backend': None
    }
    
    try:
        # Check if gi is available
        import gi
        
        # Check if GTK is already loaded
        if 'gi.repository.Gtk' in sys.modules:
            env_info['gtk_loaded'] = True
            import gi.repository.Gtk as Gtk
            env_info['gtk_version'] = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}"
            logger.info(f"GTK already loaded: version {env_info['gtk_version']}")
        
        # Test GTK3 availability
        try:
            if not env_info['gtk_loaded']:
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk
                env_info['gtk3_available'] = True
                env_info['gtk_version'] = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}"
                logger.debug("GTK3 is available")
            elif env_info['gtk_version'].startswith('3.'):
                env_info['gtk3_available'] = True
        except (ImportError, ValueError):
            logger.debug("GTK3 not available")
            
        # Test GTK4 availability (only if GTK is not already loaded)
        if not env_info['gtk_loaded']:
            try:
                gi.require_version('Gtk', '4.0')
                from gi.repository import Gtk as Gtk4
                env_info['gtk4_available'] = True
                logger.debug("GTK4 is available")
            except (ImportError, ValueError):
                logger.debug("GTK4 not available")
        
        # Test AppIndicator availability
        try:
            # Reset GTK version for AppIndicator test
            if env_info['gtk3_available']:
                gi.require_version('Gtk', '3.0')
                gi.require_version('AppIndicator3', '0.1')
                from gi.repository import AppIndicator3
                env_info['appindicator_available'] = True
                logger.debug("AppIndicator3 is available")
        except (ImportError, ValueError):
            try:
                # Try Ayatana AppIndicator
                gi.require_version('AyatanaAppIndicator3', '0.1')
                from gi.repository import AyatanaAppIndicator3
                env_info['appindicator_available'] = True
                logger.debug("AyatanaAppIndicator3 is available")
            except (ImportError, ValueError):
                logger.debug("No AppIndicator available")
                
    except ImportError:
        logger.debug("gi (PyGObject) not available")
    
    # Test pystray availability
    try:
        import pystray
        from PIL import Image
        env_info['pystray_available'] = True
        logger.debug("pystray is available")
    except ImportError:
        logger.debug("pystray not available")
    
    # Determine recommended backend
    if env_info['gtk3_available'] and env_info['appindicator_available']:
        env_info['recommended_backend'] = 'gtk3_appindicator'
    elif env_info['gtk4_available'] and not env_info['gtk_loaded']:
        env_info['recommended_backend'] = 'gtk4'
    elif env_info['pystray_available']:
        env_info['recommended_backend'] = 'pystray'
    else:
        env_info['recommended_backend'] = None
        
    logger.info(f"Recommended tray backend: {env_info['recommended_backend']}")
    return env_info


def create_optimal_tray_manager(config: Any):
    """
    Create the best available tray manager for the current environment.
    
    Args:
        config: UI configuration object
        
    Returns:
        Tray manager instance or None if none available
    """
    env_info = detect_gtk_environment()
    
    if env_info['recommended_backend'] == 'gtk3_appindicator':
        logger.info("Using GTK3 + AppIndicator tray manager")
        try:
            from .tray_gtk3_appindicator import GTK3AppIndicatorTrayManager
            return GTK3AppIndicatorTrayManager(config)
        except Exception as e:
            logger.warning(f"GTK3 AppIndicator failed: {e}")
    
    elif env_info['recommended_backend'] == 'gtk4':
        logger.info("Using GTK4 tray manager")
        try:
            from .tray_gtk4 import GTK4TrayManager
            return GTK4TrayManager(config)
        except Exception as e:
            logger.warning(f"GTK4 tray manager failed: {e}")
    
    elif env_info['recommended_backend'] == 'pystray':
        logger.info("Using pystray tray manager")
        try:
            from .tray import SystemTrayManager
            return SystemTrayManager(config)
        except Exception as e:
            logger.warning(f"pystray tray manager failed: {e}")
    
    logger.error("No suitable tray manager available")
    return None


class SmartTrayManager:
    """
    Smart tray manager that automatically selects the best implementation.
    
    Acts as a proxy to the actual tray implementation.
    """
    
    def __init__(self, config: Any):
        """Initialize smart tray manager."""
        self.config = config
        self._impl = None
        self._create_implementation()
    
    def _create_implementation(self):
        """Create the actual tray implementation."""
        self._impl = create_optimal_tray_manager(self.config)
        if not self._impl:
            logger.error("Failed to create any tray manager implementation")
    
    # Proxy all methods to the actual implementation
    def start(self) -> None:
        """Start the tray manager."""
        if self._impl:
            return self._impl.start()
        else:
            logger.warning("No tray implementation available")
    
    def stop(self) -> None:
        """Stop the tray manager."""
        if self._impl:
            return self._impl.stop()
    
    def update_status(self, status: TrayStatus) -> None:
        """Update tray status."""
        if self._impl:
            return self._impl.update_status(status)
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """Show a notification."""
        if self._impl:
            return self._impl.show_notification(title, message, timeout)
    
    def set_on_quit(self, callback: Callable) -> None:
        """Set quit callback."""
        if self._impl:
            return self._impl.set_on_quit(callback)
    
    def set_on_toggle(self, callback: Callable) -> None:
        """Set toggle recognition callback."""
        if self._impl:
            return self._impl.set_on_toggle(callback)
    
    def set_on_settings(self, callback: Callable) -> None:
        """Set open settings callback."""
        if self._impl:
            return self._impl.set_on_settings(callback)
    
    def set_on_about(self, callback: Callable) -> None:
        """Set about callback."""
        if self._impl:
            return self._impl.set_on_about(callback)
    
    def is_running(self) -> bool:
        """Check if tray is running."""
        if self._impl:
            return self._impl.is_running()
        return False