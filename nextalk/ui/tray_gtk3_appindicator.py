"""
GTK3 + AppIndicator 托盘管理器

提供最佳的Linux桌面环境兼容性，支持AppIndicator3和AyatanaAppIndicator3
"""

import logging
import threading
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import gi.repository.Gtk as Gtk
    import gi.repository.GLib as GLib

from ..config.models import UIConfig
from .tray import TrayStatus
from .menu import TrayMenu, MenuItem, MenuAction
from .icon_manager import get_icon_manager

logger = logging.getLogger(__name__)

# 尝试导入GTK3和AppIndicator
GTK_AVAILABLE = False
APPINDICATOR_AVAILABLE = False
AppIndicator = None
Gtk = None
GLib = None

try:
    import gi
    gi.require_version('Gtk', '3.0')
    
    # 尝试AppIndicator3
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
        APPINDICATOR_AVAILABLE = True
        logger.debug("Using AppIndicator3")
    except (ImportError, ValueError):
        try:
            # 尝试AyatanaAppIndicator3
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3 as AppIndicator
            APPINDICATOR_AVAILABLE = True
            logger.debug("Using AyatanaAppIndicator3")
        except (ImportError, ValueError):
            logger.debug("No AppIndicator available")
    
    if APPINDICATOR_AVAILABLE:
        from gi.repository import Gtk, GLib
        GTK_AVAILABLE = True
        
        # 初始化GTK
        if not Gtk.init_check():
            logger.warning("GTK initialization failed")
            GTK_AVAILABLE = False
        
except ImportError:
    logger.debug("GTK3/AppIndicator dependencies not available")


class GTK3AppIndicatorTrayManager:
    """
    GTK3 + AppIndicator 托盘管理器
    
    特性:
    - 兼容AppIndicator3和AyatanaAppIndicator3
    - 线程安全的GTK主循环
    - 图标动态更新
    - 优雅关闭处理
    """
    
    def __init__(self, config: UIConfig):
        """初始化GTK3 AppIndicator托盘管理器"""
        if not GTK_AVAILABLE or not APPINDICATOR_AVAILABLE:
            raise RuntimeError("GTK3 or AppIndicator not available")
        
        self.config = config
        self._indicator = None
        self._menu = TrayMenu()
        self._gtk_menu = None
        self._status = TrayStatus.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._main_loop = None
        
        # 图标管理器
        self._icon_manager = get_icon_manager()
        
        # 回调函数
        self._on_quit: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_settings: Optional[Callable] = None
        self._on_about: Optional[Callable] = None
        
        # 设置菜单处理器
        self._setup_menu_handlers()
        
        logger.info("GTK3 AppIndicator tray manager initialized")
    
    def _setup_menu_handlers(self) -> None:
        """设置默认菜单动作处理器"""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
    
    def start(self) -> None:
        """启动托盘图标"""
        if not GTK_AVAILABLE or not APPINDICATOR_AVAILABLE:
            logger.error("GTK3 or AppIndicator not available")
            return
        
        if self._running:
            logger.warning("GTK3 AppIndicator tray already running")
            return
        
        if not self.config.show_tray_icon:
            logger.info("System tray disabled in configuration")
            return
        
        self._running = True
        
        # 在独立线程中运行GTK主循环
        self._thread = threading.Thread(target=self._run_gtk_loop, daemon=True)
        self._thread.start()
        
        logger.info("GTK3 AppIndicator tray started")
    
    def stop(self) -> None:
        """停止托盘图标"""
        if not self._running:
            return
        
        self._running = False
        
        # 停止主循环
        if self._main_loop:
            GLib.idle_add(self._main_loop.quit)
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("GTK thread did not stop cleanly")
        
        self._indicator = None
        self._main_loop = None
        self._thread = None
        
        logger.info("GTK3 AppIndicator tray stopped")
    
    def _run_gtk_loop(self) -> None:
        """运行GTK主循环（在独立线程中）"""
        try:
            # 初始化GTK环境
            if not Gtk.init_check():
                logger.error("Failed to initialize GTK in thread")
                return
            
            # 创建AppIndicator
            self._create_indicator()
            
            # 创建主循环
            self._main_loop = GLib.MainLoop()
            
            # 运行主循环
            self._main_loop.run()
            
        except Exception as e:
            logger.error(f"Error in GTK main loop: {e}")
        finally:
            self._running = False
    
    def _create_indicator(self) -> None:
        """创建AppIndicator"""
        try:
            # 获取初始图标
            icon_path = self._get_icon_path(self._status)
            if not icon_path:
                logger.error("No icon available for initial state")
                return
            
            # 创建AppIndicator  
            self._indicator = AppIndicator.Indicator.new(
                "nextalk-tray",
                icon_path,
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )
            
            # 设置状态为活跃
            self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            
            # 设置标题和标签
            self._indicator.set_title("NexTalk")
            self._indicator.set_label("NexTalk", "NexTalk")
            
            # 创建并设置菜单
            self._create_gtk_menu()
            self._indicator.set_menu(self._gtk_menu)
            
            logger.debug("AppIndicator created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create AppIndicator: {e}")
    
    def _create_gtk_menu(self) -> None:
        """创建GTK菜单"""
        try:
            self._gtk_menu = Gtk.Menu()
            
            for item in self._menu.get_items():
                if item.action == MenuAction.SEPARATOR:
                    # 分隔符
                    separator = Gtk.SeparatorMenuItem()
                    self._gtk_menu.append(separator)
                else:
                    # 普通菜单项
                    menu_item = Gtk.MenuItem(label=item.label)
                    menu_item.set_sensitive(item.enabled)
                    
                    # 连接信号
                    menu_item.connect("activate", self._on_menu_activate, item)
                    
                    self._gtk_menu.append(menu_item)
            
            # 显示所有菜单项
            self._gtk_menu.show_all()
            
            logger.debug("GTK menu created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create GTK menu: {e}")
    
    def _on_menu_activate(self, gtk_item, menu_item: MenuItem) -> None:
        """菜单项激活处理器"""
        try:
            # 在独立线程中处理以避免阻塞GTK主循环
            def handle_action():
                try:
                    self._menu.trigger_action(menu_item)
                except Exception as e:
                    logger.error(f"Error handling menu action: {e}")
            
            threading.Thread(target=handle_action, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error in menu activate handler: {e}")
    
    def _get_icon_path(self, status: TrayStatus) -> Optional[str]:
        """获取状态对应的图标路径"""
        try:
            return self._icon_manager.get_icon_path(status.value)
        except Exception as e:
            logger.warning(f"Failed to get icon path for {status}: {e}")
            return None
    
    def update_status(self, status: TrayStatus) -> None:
        """更新托盘状态"""
        if status == self._status:
            return
        
        self._status = status
        
        if self._indicator and self._running:
            # 在GTK主线程中安全更新
            def update_icon():
                try:
                    icon_path = self._get_icon_path(status)
                    if icon_path:
                        self._indicator.set_icon(icon_path)
                        
                        # 更新标签
                        labels = {
                            TrayStatus.IDLE: "NexTalk - 待机",
                            TrayStatus.ACTIVE: "NexTalk - 录音中",
                            TrayStatus.ERROR: "NexTalk - 错误"
                        }
                        label = labels.get(status, "NexTalk")
                        self._indicator.set_label(label, label)
                        
                except Exception as e:
                    logger.error(f"Failed to update indicator icon: {e}")
            
            GLib.idle_add(update_icon)
        
        logger.debug(f"Tray status updated to: {status.value}")
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """显示系统通知"""
        if not self.config.show_notifications:
            return
        
        # GTK3环境下记录到日志
        # 可以扩展为使用Gio.Notification或其他桌面通知方式
        logger.info(f"Notification: {title} - {message}")
    
    def update_menu(self) -> None:
        """更新托盘菜单"""
        if self._indicator and self._running:
            def recreate_menu():
                try:
                    self._create_gtk_menu()
                    self._indicator.set_menu(self._gtk_menu)
                except Exception as e:
                    logger.error(f"Failed to update menu: {e}")
            
            GLib.idle_add(recreate_menu)
    
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
        logger.info("Quit requested from GTK3 tray")
        if self._on_quit:
            self._on_quit()
        self.stop()
    
    def _handle_toggle(self, item: MenuItem) -> None:
        """处理切换识别动作"""
        logger.info("Toggle recognition requested from GTK3 tray")
        if self._on_toggle:
            self._on_toggle()
    
    def _handle_settings(self, item: MenuItem) -> None:
        """处理打开设置动作"""
        logger.info("Open settings requested from GTK3 tray")
        if self._on_settings:
            self._on_settings()
        else:
            self.show_notification("设置", "设置界面尚未实现")
    
    def _handle_about(self, item: MenuItem) -> None:
        """处理关于动作"""
        logger.info("About requested from GTK3 tray")
        if self._on_about:
            self._on_about()
        else:
            self.show_notification(
                "关于 NexTalk",
                "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
            )
    
    def _handle_statistics(self, item: MenuItem) -> None:
        """处理查看统计信息动作"""
        logger.info("View statistics requested from GTK3 tray")
        self.show_notification("统计信息", "统计功能尚未实现")
    
    def is_running(self) -> bool:
        """检查托盘是否运行"""
        return self._running and self._indicator is not None