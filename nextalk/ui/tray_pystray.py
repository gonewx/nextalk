"""
Pystray 托盘管理器 - 基于pystray的跨平台托盘实现

提供简单可靠的系统托盘功能，适用于Windows、macOS和Linux
"""

import logging
import threading
import os
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import pystray
    from PIL import Image

from ..config.models import UIConfig
from .menu import TrayMenu, MenuItem, MenuAction
from .icon_manager import get_icon_manager

logger = logging.getLogger(__name__)

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


class PystrayTrayManager:
    """
    Pystray托盘管理器
    
    基于pystray库的跨平台托盘实现，提供基础的托盘功能
    """
    
    def __init__(self, config: UIConfig):
        """初始化pystray托盘管理器"""
        self.config = config
        self._icon: Optional[pystray.Icon] = None
        self._menu = TrayMenu()
        self._status_value = "idle"  # 使用字符串而非枚举
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # 图标管理器
        self._icon_manager = get_icon_manager()
        
        # 回调函数
        self._on_quit: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_settings: Optional[Callable] = None
        self._on_about: Optional[Callable] = None
        
        # 设置菜单处理器
        self._setup_menu_handlers()
        
        logger.info("Pystray tray manager initialized")
    
    def _setup_menu_handlers(self) -> None:
        """设置默认菜单动作处理器"""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
    
    def _get_icon_image(self, status: str) -> 'Optional[Image.Image]':
        """获取状态对应的图标图像"""
        if not TRAY_AVAILABLE:
            return None
        
        # 使用图标管理器获取优化的图标
        return self._icon_manager.get_optimized_icon_image(status)
    
    def _create_fallback_icon(self, status: str) -> Optional['Image.Image']:
        """创建回退图标"""
        if not TRAY_AVAILABLE:
            return None
            
        try:
            # 使用128x128以获得更好的高DPI显示效果
            size = 128
            color_map = {
                "idle": (74, 144, 226, 255),    # Blue
                "active": (76, 175, 80, 255),   # Green
                "error": (244, 67, 54, 255)     # Red
            }
            
            color = color_map.get(status, (128, 128, 128, 255))
            
            # 创建RGBA图像以支持透明背景
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            
            # 减少边距，增加内容区域
            margin = max(8, size // 16)
            
            # 更粗的线条以获得更好的可见性
            line_width = max(4, size // 20)
            
            # 画更清晰的圆形轮廓
            draw.ellipse([margin, margin, size - margin, size - margin], 
                        fill=None, outline=color, width=line_width)
            
            # 更显眼的中心指示器
            center = size // 2
            if status == "active":
                # 更粗的"+"表示活动状态
                thickness = max(6, size // 16)
                length = max(16, size // 6)
                draw.line([(center-length//2, center), (center+length//2, center)], 
                         fill=(255, 255, 255, 255), width=thickness)
                draw.line([(center, center-length//2), (center, center+length//2)], 
                         fill=(255, 255, 255, 255), width=thickness)
            elif status == "error":
                # 更粗的"X"表示错误状态
                thickness = max(6, size // 16)
                offset = max(12, size // 8)
                draw.line([(center-offset, center-offset), (center+offset, center+offset)], 
                         fill=(255, 255, 255, 255), width=thickness)
                draw.line([(center+offset, center-offset), (center-offset, center+offset)], 
                         fill=(255, 255, 255, 255), width=thickness)
            else:  # idle
                # 更大的中心点表示空闲状态
                dot_size = max(8, size // 10)
                draw.ellipse([center-dot_size, center-dot_size, center+dot_size, center+dot_size], 
                           fill=(255, 255, 255, 255))
            
            logger.warning(f"Using optimized fallback icon for {status} - PNG file not found!")
            return image
            
        except Exception as e:
            logger.error(f"Failed to create fallback icon: {e}")
            return None
    
    def start(self) -> None:
        """启动系统托盘图标"""
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
            # 创建托盘图标
            self._create_icon()
            
            # 在独立线程中运行
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            
            logger.info("System tray started")
        except Exception as e:
            logger.error(f"Failed to start system tray: {e}")
            self._running = False
    
    def stop(self) -> None:
        """停止系统托盘图标"""
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
        """创建系统托盘图标"""
        if not TRAY_AVAILABLE:
            return
            
        # 获取初始图标图像
        image = self._get_icon_image(self._status_value)
        if image is None:
            logger.error("No icon available for initial state")
            return
        
        # 创建pystray菜单
        menu = self._create_pystray_menu()
        
        # 创建图标
        self._icon = pystray.Icon(
            "NexTalk",
            image,
            "NexTalk - Voice Recognition",
            menu
        )
    
    def _run(self) -> None:
        """运行系统托盘图标（阻塞）"""
        try:
            if self._icon:
                self._icon.run()
        except Exception as e:
            logger.error(f"Error running tray icon: {e}")
            self._running = False
    
    def _create_pystray_menu(self) -> Optional['pystray.Menu']:
        """从TrayMenu创建pystray菜单"""
        if not TRAY_AVAILABLE:
            return None
            
        menu_items = []
        
        for item in self._menu.get_items():
            if item.action == MenuAction.SEPARATOR:
                menu_items.append(pystray.Menu.SEPARATOR)
            else:
                # 创建pystray菜单项
                pystray_item = pystray.MenuItem(
                    item.label,
                    lambda icon, i=item: self._menu.trigger_action(i),
                    checked=lambda i=item: i.checked,
                    enabled=lambda i=item: i.enabled
                )
                menu_items.append(pystray_item)
        
        return pystray.Menu(*menu_items)
    
    def update_status(self, status) -> None:
        """
        更新托盘图标状态
        
        Args:
            status: 新状态（可以是TrayStatus枚举或字符串）
        """
        # 处理TrayStatus枚举或字符串
        if hasattr(status, 'value'):
            status_str = status.value
        else:
            status_str = str(status)
            
        if status_str == self._status_value:
            return
        
        self._status_value = status_str
        
        if self._icon and self._running:
            # 更新图标图像
            new_image = self._get_icon_image(status_str)
            if new_image:
                self._icon.icon = new_image
                
                # 更新工具提示
                tooltips = {
                    "idle": "NexTalk - Idle",
                    "active": "NexTalk - Recording", 
                    "error": "NexTalk - Error"
                }
                self._icon.title = tooltips.get(status_str, "NexTalk")
        
        logger.debug(f"Tray status updated to: {status_str}")
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """
        显示系统通知
        
        Args:
            title: 通知标题
            message: 通知消息
            timeout: 通知超时时间（秒，被忽略）
        """
        if not self.config.show_notifications:
            return
        
        if self._icon and TRAY_AVAILABLE:
            try:
                self._icon.notify(title, message)
            except Exception as e:
                logger.debug(f"Could not show notification: {e}")
                # 回退到日志记录
                logger.info(f"Notification: {title} - {message}")
        else:
            logger.info(f"Notification: {title} - {message}")
    
    def update_menu(self) -> None:
        """更新托盘菜单"""
        if self._icon and TRAY_AVAILABLE:
            self._icon.menu = self._create_pystray_menu()
    
    # 回调设置器
    def set_on_quit(self, callback: Callable) -> None:
        """设置退出回调"""
        self._on_quit = callback
    
    def set_on_toggle(self, callback: Callable) -> None:
        """设置切换识别回调"""
        self._on_toggle = callback
    
    def set_on_settings(self, callback: Callable) -> None:
        """设置打开设置回调"""
        self._on_settings = callback
    
    def set_on_about(self, callback: Callable) -> None:
        """设置关于回调"""
        self._on_about = callback
    
    # 菜单处理器
    def _handle_quit(self, item: MenuItem) -> None:
        """处理退出动作"""
        logger.info("Quit requested from pystray tray")
        if self._on_quit:
            self._on_quit()
        self.stop()
    
    def _handle_toggle(self, item: MenuItem) -> None:
        """处理切换识别动作"""
        logger.info("Toggle recognition requested from pystray tray")
        if self._on_toggle:
            self._on_toggle()
    
    def _handle_settings(self, item: MenuItem) -> None:
        """处理打开设置动作"""
        logger.info("Open settings requested from pystray tray")
        if self._on_settings:
            self._on_settings()
        else:
            self.show_notification("设置", "设置界面尚未实现")
    
    def _handle_about(self, item: MenuItem) -> None:
        """处理关于动作"""
        logger.info("About requested from pystray tray")
        if self._on_about:
            self._on_about()
        else:
            self.show_notification(
                "关于 NexTalk",
                "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
            )
    
    def _handle_statistics(self, item: MenuItem) -> None:
        """处理查看统计信息动作"""
        logger.info("View statistics requested from pystray tray")
        self.show_notification("统计信息", "统计功能尚未实现")
    
    def is_running(self) -> bool:
        """检查托盘是否运行"""
        return self._running and self._icon is not None