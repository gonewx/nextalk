"""
GTK4 托盘管理器

基于现代GTK4应用框架的托盘实现，适用于新版桌面环境
"""

import logging
import threading
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import gi.repository.Gtk as Gtk
    import gi.repository.Gio as Gio
    import gi.repository.GLib as GLib

from ..config.models import UIConfig
from .tray import TrayStatus
from .menu import TrayMenu, MenuItem, MenuAction
from .icon_manager import get_icon_manager

logger = logging.getLogger(__name__)

# 尝试导入GTK4
GTK4_AVAILABLE = False
Gtk = None
Gio = None
GLib = None

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gio', '2.0')
    from gi.repository import Gtk, Gio, GLib
    GTK4_AVAILABLE = True
    logger.debug("GTK4 dependencies available")
except (ImportError, ValueError) as e:
    logger.debug(f"GTK4 dependencies not available: {e}")


class GTK4TrayManager:
    """
    GTK4 托盘管理器
    
    特性:
    - 基于GApplication的现代应用架构
    - 声明式Gio.Menu菜单系统
    - 原生Gio.Notification通知支持
    - GAction驱动的菜单响应
    """
    
    def __init__(self, config: UIConfig):
        """初始化GTK4托盘管理器"""
        if not GTK4_AVAILABLE:
            raise RuntimeError("GTK4 not available")
        
        self.config = config
        self._app: Optional[Gtk.Application] = None
        self._menu = TrayMenu()
        self._gio_menu: Optional[Gio.Menu] = None
        self._status = TrayStatus.IDLE
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
        
        logger.info("GTK4 tray manager initialized")
    
    def _setup_menu_handlers(self) -> None:
        """设置默认菜单动作处理器"""
        self._menu.register_handler(MenuAction.QUIT, self._handle_quit)
        self._menu.register_handler(MenuAction.TOGGLE_RECOGNITION, self._handle_toggle)
        self._menu.register_handler(MenuAction.OPEN_SETTINGS, self._handle_settings)
        self._menu.register_handler(MenuAction.ABOUT, self._handle_about)
        self._menu.register_handler(MenuAction.VIEW_STATISTICS, self._handle_statistics)
    
    def start(self) -> None:
        """启动托盘图标"""
        if not GTK4_AVAILABLE:
            logger.error("GTK4 not available")
            return
        
        if self._running:
            logger.warning("GTK4 tray already running")
            return
        
        if not self.config.show_tray_icon:
            logger.info("System tray disabled in configuration")
            return
        
        self._running = True
        
        # 在独立线程中运行GTK主循环
        self._thread = threading.Thread(target=self._run_gtk_loop, daemon=True)
        self._thread.start()
        
        logger.info("GTK4 tray started")
    
    def stop(self) -> None:
        """停止托盘图标"""
        if not self._running:
            return
        
        self._running = False
        
        # 退出应用
        if self._app:
            GLib.idle_add(self._app.quit)
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("GTK4 thread did not stop cleanly")
        
        self._app = None
        self._thread = None
        
        logger.info("GTK4 tray stopped")
    
    def _run_gtk_loop(self) -> None:
        """运行GTK4主循环（在独立线程中）"""
        try:
            # 创建GTK Application
            self._app = Gtk.Application(
                application_id='com.nextalk.app',
                flags=Gio.ApplicationFlags.FLAGS_NONE
            )
            
            # 连接生命周期信号
            self._app.connect('activate', self._on_app_activate)
            self._app.connect('shutdown', self._on_app_shutdown)
            
            # 注册动作
            self._register_actions()
            
            # 运行应用
            self._app.run([])
            
        except Exception as e:
            logger.error(f"Error in GTK4 main loop: {e}")
        finally:
            self._running = False
    
    def _on_app_activate(self, app: Gtk.Application) -> None:
        """应用激活回调"""
        try:
            logger.debug("GTK4 application activated")
            
            # 创建菜单模型
            self._create_gio_menu()
            
            # 在GTK4中，系统托盘通常通过桌面环境的扩展或StatusNotifierItem支持
            # 这里主要是设置应用菜单和通知功能
            
        except Exception as e:
            logger.error(f"Error in app activate: {e}")
    
    def _on_app_shutdown(self, app: Gtk.Application) -> None:
        """应用关闭回调"""
        logger.debug("GTK4 application shutting down")
        self._running = False
    
    def _register_actions(self) -> None:
        """注册GAction动作"""
        try:
            # 为每个菜单项创建动作
            for item in self._menu.get_items():
                if item.action != MenuAction.SEPARATOR:
                    action = Gio.SimpleAction.new(item.action.value, None)
                    action.connect('activate', self._on_action_activate, item)
                    self._app.add_action(action)
            
            logger.debug("GTK4 actions registered")
            
        except Exception as e:
            logger.error(f"Failed to register actions: {e}")
    
    def _create_gio_menu(self) -> None:
        """创建Gio.Menu模型"""
        try:
            self._gio_menu = Gio.Menu()
            
            for item in self._menu.get_items():
                if item.action == MenuAction.SEPARATOR:
                    # GTK4菜单分隔符通过分组实现
                    continue
                else:
                    # 创建菜单项
                    menu_item = Gio.MenuItem.new(item.label, f"app.{item.action.value}")
                    self._gio_menu.append_item(menu_item)
            
            # 设置应用菜单
            self._app.set_menubar(self._gio_menu)
            
            logger.debug("Gio.Menu created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create Gio.Menu: {e}")
    
    def _on_action_activate(self, action: Gio.SimpleAction, parameter, menu_item: MenuItem) -> None:
        """动作激活处理器"""
        try:
            # 在独立线程中处理以避免阻塞GTK主循环
            def handle_action():
                try:
                    self._menu.trigger_action(menu_item)
                except Exception as e:
                    logger.error(f"Error handling menu action: {e}")
            
            threading.Thread(target=handle_action, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error in action activate handler: {e}")
    
    def update_status(self, status: TrayStatus) -> None:
        """更新托盘状态"""
        if status == self._status:
            return
        
        self._status = status
        
        # GTK4中状态更新主要通过通知或应用指示器
        # 这里可以扩展为使用StatusNotifierItem或其他机制
        
        logger.debug(f"GTK4 tray status updated to: {status.value}")
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """显示系统通知"""
        if not self.config.show_notifications:
            return
        
        if self._app and self._running:
            def send_notification():
                try:
                    # 使用Gio.Notification发送通知
                    notification = Gio.Notification.new(title)
                    notification.set_body(message)
                    
                    # 设置图标
                    icon_path = self._icon_manager.get_icon_path(self._status.value)
                    if icon_path:
                        icon = Gio.FileIcon.new(Gio.File.new_for_path(icon_path))
                        notification.set_icon(icon)
                    
                    # 发送通知
                    self._app.send_notification("nextalk", notification)
                    
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
                    # 回退到日志
                    logger.info(f"Notification: {title} - {message}")
            
            GLib.idle_add(send_notification)
        else:
            logger.info(f"Notification: {title} - {message}")
    
    def update_menu(self) -> None:
        """更新托盘菜单"""
        if self._app and self._running:
            def recreate_menu():
                try:
                    self._create_gio_menu()
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
        logger.info("Quit requested from GTK4 tray")
        if self._on_quit:
            self._on_quit()
        self.stop()
    
    def _handle_toggle(self, item: MenuItem) -> None:
        """处理切换识别动作"""
        logger.info("Toggle recognition requested from GTK4 tray")
        if self._on_toggle:
            self._on_toggle()
    
    def _handle_settings(self, item: MenuItem) -> None:
        """处理打开设置动作"""
        logger.info("Open settings requested from GTK4 tray")
        if self._on_settings:
            self._on_settings()
        else:
            self.show_notification("设置", "设置界面尚未实现")
    
    def _handle_about(self, item: MenuItem) -> None:
        """处理关于动作"""
        logger.info("About requested from GTK4 tray")
        if self._on_about:
            self._on_about()
        else:
            self.show_notification(
                "关于 NexTalk",
                "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
            )
    
    def _handle_statistics(self, item: MenuItem) -> None:
        """处理查看统计信息动作"""
        logger.info("View statistics requested from GTK4 tray")
        self.show_notification("统计信息", "统计功能尚未实现")
    
    def is_running(self) -> bool:
        """检查托盘是否运行"""
        return self._running and self._app is not None