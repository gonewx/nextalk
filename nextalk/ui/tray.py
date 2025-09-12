"""
System tray manager for NexTalk.

Simple and lightweight tray implementation using pystray.
"""

import logging
import threading
import os
from enum import Enum
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import pystray
    from PIL import Image
from pathlib import Path

# Force GTK backend to avoid AppIndicator D-Bus issues in GNOME
os.environ.setdefault('PYSTRAY_BACKEND', 'gtk')

# Initialize GTK environment properly for terminals
try:
    # Set GTK backend to X11 for better compatibility with terminals
    os.environ.setdefault('GDK_BACKEND', 'x11')
    
    # Suppress GTK warnings about missing widgets
    os.environ.setdefault('GTK_CSD', '0')
    os.environ.setdefault('GTK_USE_PORTAL', '0')
    
    # Initialize GTK properly
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    
    # Initialize GTK main loop if not already done
    if not Gtk.init_check():
        logging.warning("GTK initialization failed, falling back to Xorg backend")
        os.environ['PYSTRAY_BACKEND'] = 'xorg'
except Exception as e:
    logging.debug(f"GTK initialization issue: {e}, using fallback backend")
    os.environ['PYSTRAY_BACKEND'] = 'xorg'

# Try to import GUI dependencies
try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    pystray = None
    Image = None
    TRAY_AVAILABLE = False
    logging.warning("System tray support not available. Install pystray and Pillow for GUI support.")

from ..config.models import UIConfig
from .menu import TrayMenu, MenuItem, MenuAction


logger = logging.getLogger(__name__)


class TrayStatus(Enum):
    """System tray status indicators."""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"


class SystemTrayManager:
    """
    Simple system tray manager using pystray.
    
    Provides basic tray functionality with status indication and context menu.
    """
    
    def __init__(self, config: Optional[UIConfig] = None):
        """
        Initialize the system tray manager.
        
        Args:
            config: UI configuration
        """
        self.config = config or UIConfig()
        self._icon: Optional[pystray.Icon] = None
        self._menu = TrayMenu()
        self._status = TrayStatus.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Icon paths
        self.icons_dir = Path(__file__).parent / "icons"
        self._icon_cache = {}
        
        # Callbacks
        self._on_quit: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_settings: Optional[Callable] = None
        self._on_about: Optional[Callable] = None
        
        # Setup menu handlers
        self._setup_menu_handlers()
        
        # Load icons
        self._load_icons()
    
    def _setup_menu_handlers(self) -> None:
        """Setup default menu action handlers."""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
    
    def _load_icons(self) -> None:
        """Load icon images into cache."""
        if not TRAY_AVAILABLE:
            return
            
        icon_files = {
            TrayStatus.IDLE: "microphone-idle.png",
            TrayStatus.ACTIVE: "microphone-active.png", 
            TrayStatus.ERROR: "microphone-error.png"
        }
        
        for status, filename in icon_files.items():
            icon_path = self.icons_dir / filename
            try:
                if icon_path.exists():
                    self._icon_cache[status] = Image.open(icon_path)
                    logger.info(f"Loaded icon: {filename}")
                else:
                    # Create fallback icon if file doesn't exist
                    self._icon_cache[status] = self._create_fallback_icon(status)
                    logger.info(f"Created fallback icon for {status.value}")
            except Exception as e:
                logger.warning(f"Failed to load icon {filename}: {e}")
                self._icon_cache[status] = self._create_fallback_icon(status)
    
    def _create_fallback_icon(self, status: TrayStatus) -> Optional['Image.Image']:
        """Create optimized fallback icon for better visibility."""
        if not TRAY_AVAILABLE:
            return None
            
        try:
            # Use 128x128 for better visibility on high-DPI displays
            size = 128
            color_map = {
                TrayStatus.IDLE: (74, 144, 226, 255),    # Blue
                TrayStatus.ACTIVE: (76, 175, 80, 255),   # Green
                TrayStatus.ERROR: (244, 67, 54, 255)     # Red
            }
            
            color = color_map.get(status, (128, 128, 128, 255))
            
            # Create RGBA image for transparency
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            
            # Reduce margin, increase content area
            margin = max(8, size // 16)
            
            # Thicker lines for better visibility
            line_width = max(4, size // 20)
            
            # Draw clearer circle outline
            draw.ellipse([margin, margin, size - margin, size - margin], 
                        fill=None, outline=color, width=line_width)
            
            # More prominent center indicators
            center = size // 2
            if status == TrayStatus.ACTIVE:
                # Thicker "+" for active
                thickness = max(6, size // 16)
                length = max(16, size // 6)
                draw.line([(center-length//2, center), (center+length//2, center)], 
                         fill=(255, 255, 255, 255), width=thickness)
                draw.line([(center, center-length//2), (center, center+length//2)], 
                         fill=(255, 255, 255, 255), width=thickness)
            elif status == TrayStatus.ERROR:
                # Thicker "X" for error
                thickness = max(6, size // 16)
                offset = max(12, size // 8)
                draw.line([(center-offset, center-offset), (center+offset, center+offset)], 
                         fill=(255, 255, 255, 255), width=thickness)
                draw.line([(center+offset, center-offset), (center-offset, center+offset)], 
                         fill=(255, 255, 255, 255), width=thickness)
            else:  # IDLE
                # Larger center dot for idle
                dot_size = max(8, size // 10)
                draw.ellipse([center-dot_size, center-dot_size, center+dot_size, center+dot_size], 
                           fill=(255, 255, 255, 255))
            
            logger.warning(f"Using optimized fallback icon for {status.value} - PNG file not found!")
            return image
            
        except Exception as e:
            logger.error(f"Failed to create fallback icon: {e}")
            return None
    
    def start(self) -> None:
        """Start the system tray icon."""
        if not TRAY_AVAILABLE:
            logger.warning("Tray not available - pystray/Pillow not installed")
            return
            
        if self._running:
            logger.warning("System tray already running")
            return
        
        if not self.config.show_tray_icon:
            logger.info("System tray disabled in configuration")
            return
        
        self._running = True
        
        try:
            # Create tray icon
            self._create_icon()
            
            # Run in separate thread
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            
            logger.info("System tray started")
        except Exception as e:
            logger.error(f"Failed to start system tray: {e}")
            self._running = False
    
    def stop(self) -> None:
        """Stop the system tray icon."""
        if not self._running:
            return
        
        self._running = False
        
        if self._icon:
            try:
                self._icon.stop()
            except Exception as e:
                logger.error(f"Error stopping tray icon: {e}")
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Tray thread did not stop cleanly")
        
        self._icon = None
        self._thread = None
        
        logger.info("System tray stopped")
    
    def _create_icon(self) -> None:
        """Create the system tray icon."""
        if not TRAY_AVAILABLE:
            return
            
        # Get initial icon image
        image = self._icon_cache.get(self._status)
        if image is None:
            logger.error("No icon available for initial state")
            return
        
        # Create pystray menu
        menu = self._create_pystray_menu()
        
        # Create icon
        self._icon = pystray.Icon(
            "NexTalk",
            image,
            "NexTalk - Voice Recognition",
            menu
        )
    
    def _run(self) -> None:
        """Run the system tray icon (blocking)."""
        try:
            if self._icon:
                self._icon.run()
        except Exception as e:
            logger.error(f"Error running tray icon: {e}")
            self._running = False
    
    def _create_pystray_menu(self) -> Optional['pystray.Menu']:
        """Create pystray menu from TrayMenu."""
        if not TRAY_AVAILABLE:
            return None
            
        menu_items = []
        
        for item in self._menu.get_items():
            if item.action == MenuAction.SEPARATOR:
                menu_items.append(pystray.Menu.SEPARATOR)
            else:
                # Create pystray menu item
                pystray_item = pystray.MenuItem(
                    item.label,
                    lambda icon, i=item: self._menu.trigger_action(i),
                    checked=lambda i=item: i.checked,
                    enabled=lambda i=item: i.enabled
                )
                menu_items.append(pystray_item)
        
        return pystray.Menu(*menu_items)
    
    def update_status(self, status: TrayStatus) -> None:
        """
        Update the tray icon status.
        
        Args:
            status: New status
        """
        if status == self._status:
            return
        
        self._status = status
        
        if self._icon and self._running:
            # Update icon image
            new_image = self._icon_cache.get(status)
            if new_image:
                self._icon.icon = new_image
                
                # Update tooltip
                tooltips = {
                    TrayStatus.IDLE: "NexTalk - Idle",
                    TrayStatus.ACTIVE: "NexTalk - Recording",
                    TrayStatus.ERROR: "NexTalk - Error"
                }
                self._icon.title = tooltips.get(status, "NexTalk")
        
        logger.debug(f"Tray status updated to: {status.value}")
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
            timeout: Notification timeout in seconds (ignored)
        """
        if not self.config.show_notifications:
            return
        
        if self._icon and TRAY_AVAILABLE:
            try:
                self._icon.notify(title, message)
            except Exception as e:
                logger.debug(f"Could not show notification: {e}")
                # Fallback to logging
                logger.info(f"Notification: {title} - {message}")
        else:
            logger.info(f"Notification: {title} - {message}")
    
    def update_menu(self) -> None:
        """Update the tray menu."""
        if self._icon and TRAY_AVAILABLE:
            self._icon.menu = self._create_pystray_menu()
    
    # Callback setters
    def set_on_quit(self, callback: Callable) -> None:
        """Set quit callback."""
        self._on_quit = callback
    
    def set_on_toggle(self, callback: Callable) -> None:
        """Set toggle recognition callback."""
        self._on_toggle = callback
    
    def set_on_settings(self, callback: Callable) -> None:
        """Set open settings callback."""
        self._on_settings = callback
    
    def set_on_about(self, callback: Callable) -> None:
        """Set about callback."""
        self._on_about = callback
    
    # Menu handlers
    def _handle_quit(self, item: MenuItem) -> None:
        """Handle quit action."""
        logger.info("Quit requested from tray")
        if self._on_quit:
            self._on_quit()
        self.stop()
    
    def _handle_toggle(self, item: MenuItem) -> None:
        """Handle toggle recognition action."""
        logger.info("Toggle recognition requested from tray")
        if self._on_toggle:
            self._on_toggle()
    
    def _handle_settings(self, item: MenuItem) -> None:
        """Handle open settings action."""
        logger.info("Open settings requested from tray")
        if self._on_settings:
            self._on_settings()
        else:
            self.show_notification("设置", "设置界面尚未实现")
    
    def _handle_about(self, item: MenuItem) -> None:
        """Handle about action."""
        logger.info("About requested from tray")
        if self._on_about:
            self._on_about()
        else:
            self.show_notification(
                "关于 NexTalk",
                "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
            )
    
    def _handle_statistics(self, item: MenuItem) -> None:
        """Handle view statistics action."""
        logger.info("View statistics requested from tray")
        self.show_notification("统计信息", "统计功能尚未实现")
    
    def is_running(self) -> bool:
        """Check if tray is running."""
        return self._running and self._icon is not None


# Provide backwards compatibility
TrayManager = SystemTrayManager