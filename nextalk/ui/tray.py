"""
System tray manager for NexTalk.

Provides system tray integration using pystray library.
"""

import logging
import threading
from enum import Enum
from typing import Optional, Callable, Any, Dict
import io

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
from .icons import IconManager, IconTheme


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
        self._icon_manager = IconManager(self._get_icon_theme())
        self._status = TrayStatus.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Callbacks
        self._on_quit: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_settings: Optional[Callable] = None
        self._on_about: Optional[Callable] = None
        
        # IME related callbacks
        self._on_ime_toggle: Optional[Callable] = None
        self._on_ime_settings: Optional[Callable] = None
        self._on_ime_test: Optional[Callable] = None
        self._on_ime_status: Optional[Callable] = None
        
        # IME状态缓存
        self._ime_enabled = True
        self._ime_status_info = None
        
        # Setup menu handlers
        self._setup_menu_handlers()
    
    def _get_icon_theme(self) -> IconTheme:
        """Get icon theme from configuration."""
        theme_map = {
            "auto": IconTheme.AUTO,
            "light": IconTheme.LIGHT,
            "dark": IconTheme.DARK
        }
        return theme_map.get(self.config.tray_icon_theme, IconTheme.AUTO)
    
    def _setup_menu_handlers(self) -> None:
        """Setup default menu action handlers."""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
        
        # IME related handlers
        self._menu.register_handler(MenuAction.VIEW_IME_STATUS, self._handle_ime_status)
        self._menu.register_handler(MenuAction.TOGGLE_IME, self._handle_ime_toggle)
        self._menu.register_handler(MenuAction.IME_SETTINGS, self._handle_ime_settings)
        self._menu.register_handler(MenuAction.TEST_IME_INJECTION, self._handle_ime_test)
    
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
    
    def _get_icon_image(self, status: TrayStatus) -> Image.Image:
        """
        Get icon image for the given status.
        
        Args:
            status: Current status
            
        Returns:
            PIL Image object
        """
        try:
            # Get icon data from icon manager
            icon_data = self._icon_manager.get_icon(status.value)
            
            # Create PIL image from data
            image = Image.open(io.BytesIO(icon_data))
            
            # Convert to RGB mode to avoid RGBA issues
            if image.mode in ('RGBA', 'LA'):
                image = image.convert('RGB')
            
            # Ensure it's the right size (16x16 or 32x32)
            if image.size != (16, 16):
                image = image.resize((16, 16), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            # Log as debug since we have fallback icons
            logger.debug(f"Could not load icon from data: {e}")
            # Return a simple colored square as fallback
            return self._create_fallback_icon(status)
    
    def _create_fallback_icon(self, status: TrayStatus) -> Image.Image:
        """Create a fallback icon."""
        # Create a simple colored square
        color_map = {
            TrayStatus.IDLE: (128, 128, 128),  # Gray
            TrayStatus.ACTIVE: (0, 255, 0),    # Green
            TrayStatus.ERROR: (255, 0, 0)      # Red
        }
        
        color = color_map.get(status, (128, 128, 128))
        image = Image.new('RGB', (16, 16), color)
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
    
    def show_notification(self, title: str, message: str) -> None:
        """
        Show a system notification.
        
        Args:
            title: Notification title
            message: Notification message
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
    
    def set_on_ime_toggle(self, callback: Callable) -> None:
        """Set IME toggle callback."""
        self._on_ime_toggle = callback
    
    def set_on_ime_settings(self, callback: Callable) -> None:
        """Set IME settings callback."""
        self._on_ime_settings = callback
    
    def set_on_ime_test(self, callback: Callable) -> None:
        """Set IME test callback."""
        self._on_ime_test = callback
    
    def set_on_ime_status(self, callback: Callable) -> None:
        """Set IME status callback."""
        self._on_ime_status = callback
    
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
    
    def _handle_ime_status(self, item: MenuItem) -> None:
        """Handle IME status view action."""
        logger.info("IME status requested from tray")
        if self._on_ime_status:
            self._on_ime_status()
        else:
            status_text = "IME功能已启用" if self._ime_enabled else "IME功能已禁用"
            if self._ime_status_info:
                status_text += f"\n当前IME: {self._ime_status_info.get('current_ime', '未知')}"
                status_text += f"\n语言: {self._ime_status_info.get('language', '未知')}"
                status_text += f"\n目标应用: {self._ime_status_info.get('focus_app', '未知')}"
            self.show_notification("IME状态", status_text)
    
    def _handle_ime_toggle(self, item: MenuItem) -> None:
        """Handle IME toggle action."""
        logger.info("IME toggle requested from tray")
        if self._on_ime_toggle:
            result = self._on_ime_toggle()
            if result is not None:
                self._ime_enabled = result
                self._update_ime_menu_items()
                status = "启用" if self._ime_enabled else "禁用"
                self.show_notification("IME状态", f"IME注入已{status}")
        else:
            self._ime_enabled = not self._ime_enabled
            self._update_ime_menu_items()
            status = "启用" if self._ime_enabled else "禁用"
            self.show_notification("IME状态", f"IME注入已{status}")
    
    def _handle_ime_settings(self, item: MenuItem) -> None:
        """Handle IME settings action."""
        logger.info("IME settings requested from tray")
        if self._on_ime_settings:
            self._on_ime_settings()
        else:
            self.show_notification("IME设置", "IME设置界面尚未实现")
    
    def _handle_ime_test(self, item: MenuItem) -> None:
        """Handle IME test injection action."""
        logger.info("IME test injection requested from tray")
        if self._on_ime_test:
            self._on_ime_test()
        else:
            self.show_notification("IME测试", "正在测试IME文本注入功能...")
    
    def update_ime_status(self, ime_enabled: bool, status_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Update IME status in tray menu.
        
        Args:
            ime_enabled: Whether IME is enabled
            status_info: Detailed status information
        """
        self._ime_enabled = ime_enabled
        self._ime_status_info = status_info
        self._update_ime_menu_items()
    
    def _update_ime_menu_items(self) -> None:
        """Update IME-related menu items."""
        # 更新IME状态显示
        if self._ime_status_info:
            current_ime = self._ime_status_info.get('current_ime', '未知')
            is_active = self._ime_status_info.get('is_active', False)
            status_text = f"IME状态: {current_ime}" + ("(活跃)" if is_active else "(非活跃)")
        else:
            status_text = f"IME状态: {'已启用' if self._ime_enabled else '已禁用'}"
        
        self._menu.update_item(
            MenuAction.VIEW_IME_STATUS,
            label=status_text
        )
        
        # 更新切换按钮
        toggle_text = "禁用IME注入" if self._ime_enabled else "启用IME注入"
        self._menu.update_item(
            MenuAction.TOGGLE_IME,
            label=toggle_text,
            checked=self._ime_enabled
        )
        
        # 更新测试按钮可用性
        self._menu.update_item(
            MenuAction.TEST_IME_INJECTION,
            enabled=self._ime_enabled
        )
        
        # 刷新托盘菜单
        if self._running:
            self.update_menu()
    
    def is_running(self) -> bool:
        """Check if tray is running."""
        return self._running