"""
System tray manager for NexTalk.

Provides system tray integration using pystray library.
"""

import logging
import threading
from enum import Enum
from typing import Optional, Callable, Any
import io
from pathlib import Path

# Try to import GUI dependencies
try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    logging.warning("System tray support not available. Install pystray and Pillow for GUI support.")
    
    # Create dummy classes for when pystray is not available
    class DummyIcon:
        def __init__(self, *args, **kwargs):
            self.visible = False
        def run(self, *args, **kwargs):
            pass
        def stop(self):
            pass
        def update_menu(self):
            pass
        @property
        def icon(self):
            return None
        @icon.setter 
        def icon(self, value):
            pass
        @property
        def menu(self):
            return None
        @menu.setter
        def menu(self, value):
            pass
    
    class DummyMenu:
        def __init__(self, *args, **kwargs):
            pass
    
    class DummyMenuItem:
        def __init__(self, *args, **kwargs):
            pass
    
    # Create dummy pystray module
    class DummyPystray:
        Icon = DummyIcon
        Menu = DummyMenu
        MenuItem = DummyMenuItem
    
    pystray = DummyPystray()
    
    # Dummy Image class
    class Image:
        @staticmethod
        def new(*args, **kwargs):
            return None

from ..config.models import UIConfig
from .menu import TrayMenu, MenuItem, MenuAction
from .icon_manager import get_icon_manager


logger = logging.getLogger(__name__)


class TrayStatus(Enum):
    """System tray status indicators."""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"


class SystemTrayManager:
    """
    Manages the system tray icon and interactions.
    
    Provides status indication and menu management.
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
        self._icon_manager = get_icon_manager()
        self._status = TrayStatus.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._on_quit: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_settings: Optional[Callable] = None
        self._on_about: Optional[Callable] = None
        
        # Setup menu handlers
        self._setup_menu_handlers()
    
    def _setup_menu_handlers(self) -> None:
        """Setup default menu action handlers."""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
    
    def start(self) -> None:
        """Start the system tray icon."""
        if self._running:
            logger.warning("System tray already running")
            return
        
        if not self.config.show_tray_icon:
            logger.info("System tray disabled in configuration")
            return
        
        self._running = True
        
        # Create tray icon
        self._create_icon()
        
        # Run in separate thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        logger.info("System tray started")
    
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
            # 先尝试正常等待
            self._thread.join(timeout=2.0)
            
            # 如果线程还在运行，记录警告
            if self._thread.is_alive():
                logger.warning("Tray thread did not stop cleanly, forcing shutdown")
        
        self._icon = None
        self._thread = None
        
        logger.info("System tray stopped")
    
    def _create_icon(self) -> None:
        """Create the system tray icon."""
        # Get initial icon image
        image = self._get_icon_image(self._status)
        
        # Create pystray menu
        menu = self._create_pystray_menu()
        
        # Create icon
        # 在 X11 系统下使用英文标题避免编码问题
        title = "NexTalk - Voice Recognition"
        self._icon = pystray.Icon(
            "NexTalk",
            image,
            title,
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
    
    def _get_icon_image(self, status: TrayStatus) -> Image:
        """
        Get icon image for the given status.
        
        Args:
            status: Current status
            
        Returns:
            PIL Image object
        """
        try:
            status_map = {
                TrayStatus.IDLE: "idle",
                TrayStatus.ACTIVE: "active", 
                TrayStatus.ERROR: "error"
            }
            
            status_str = status_map.get(status, "idle")
            
            # 使用优化的SVG到PIL转换
            image = self._icon_manager.get_optimized_icon_image(status_str)
            if image is not None:
                logger.debug(f"Got optimized PIL Image for {status_str}: {image.mode} {image.size}")
                return image
            else:
                # 使用内嵌的备用图标
                logger.debug(f"No optimized image available, using fallback for {status_str}")
                return self._create_fallback_icon(status)
            
        except Exception as e:
            logger.debug(f"Could not get icon image: {e}")
            return self._create_fallback_icon(status)
    
    def _create_fallback_icon(self, status: TrayStatus) -> Image:
        """Create a fallback icon."""
        # Create a simple colored square with transparent background
        color_map = {
            TrayStatus.IDLE: (128, 128, 128, 255),    # Gray with alpha
            TrayStatus.ACTIVE: (0, 255, 0, 255),      # Green with alpha
            TrayStatus.ERROR: (255, 0, 0, 255)        # Red with alpha
        }
        
        color = color_map.get(status, (128, 128, 128, 255))
        # 使用RGBA模式支持透明背景
        image = Image.new('RGBA', (22, 22), (0, 0, 0, 0))  # 透明背景
        
        # 在透明背景上绘制彩色圆形
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        draw.ellipse([2, 2, 20, 20], fill=color)
        
        return image
    
    def _create_pystray_menu(self) -> pystray.Menu:
        """Create pystray menu from TrayMenu."""
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
        
        if self._icon:
            # Update icon image
            self._icon.icon = self._get_icon_image(status)
            
            # Update tooltip based on status - 使用英文避免编码问题
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
            timeout: Notification timeout in seconds (ignored in this implementation)
        """
        if not self.config.show_notifications:
            return
        
        if self._icon:
            try:
                self._icon.notify(title, message)
            except Exception as e:
                # Log as debug since notifications are non-critical
                logger.debug(f"Could not show notification: {e}")
                logger.info(f"Notification: {title} - {message}")  # Show content in log instead
    
    def update_menu(self) -> None:
        """Update the tray menu."""
        if self._icon:
            self._icon.menu = self._create_pystray_menu()
    
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
        return self._running