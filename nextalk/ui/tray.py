"""
系统托盘管理器 - 智能选择最佳托盘实现

自动检测环境并选择最佳的托盘后端：GTK3+AppIndicator → GTK4 → pystray
"""

import logging
import os
import sys
from enum import Enum
from typing import Optional, Callable, Any, Dict

from ..config.models import UIConfig

logger = logging.getLogger(__name__)


class TrayStatus(Enum):
    """系统托盘状态指示器"""
    IDLE = "idle"
    ACTIVE = "active"
    ERROR = "error"


def detect_gtk_environment() -> Dict[str, Any]:
    """
    检测当前GTK环境和可用后端
    
    Returns:
        dict: 环境信息包括GTK版本、AppIndicator支持等
    """
    env_info = {
        'gtk_loaded': False,
        'gtk_version': None,
        'gtk3_available': False,
        'gtk4_available': False,
        'appindicator_available': False,
        'pystray_available': False,
        'recommended_backend': None,
        'desktop_environment': 'unknown',
        'display_protocol': 'unknown'
    }
    
    # 检测桌面环境
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'gnome' in desktop or 'unity' in desktop:
        env_info['desktop_environment'] = 'gnome'
    elif 'kde' in desktop or 'plasma' in desktop:
        env_info['desktop_environment'] = 'kde'
    elif 'xfce' in desktop:
        env_info['desktop_environment'] = 'xfce'
    elif 'lxde' in desktop or 'lxqt' in desktop:
        env_info['desktop_environment'] = 'lxde'
    
    # 检测显示协议
    if os.environ.get('WAYLAND_DISPLAY'):
        env_info['display_protocol'] = 'wayland'
    elif os.environ.get('DISPLAY'):
        env_info['display_protocol'] = 'x11'
    
    try:
        # 检查gi是否可用
        import gi
        
        # 检查GTK是否已加载
        if 'gi.repository.Gtk' in sys.modules:
            env_info['gtk_loaded'] = True
            import gi.repository.Gtk as Gtk
            env_info['gtk_version'] = f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}"
            logger.debug(f"GTK already loaded: version {env_info['gtk_version']}")
        
        # 测试GTK3可用性
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
            
        # 测试GTK4可用性（仅在GTK未预加载时）
        if not env_info['gtk_loaded']:
            try:
                gi.require_version('Gtk', '4.0')
                from gi.repository import Gtk as Gtk4
                env_info['gtk4_available'] = True
                logger.debug("GTK4 is available")
            except (ImportError, ValueError):
                logger.debug("GTK4 not available")
        
        # 测试AppIndicator可用性
        try:
            # 重置GTK版本用于AppIndicator测试
            if env_info['gtk3_available']:
                gi.require_version('Gtk', '3.0')
                gi.require_version('AppIndicator3', '0.1')
                from gi.repository import AppIndicator3
                env_info['appindicator_available'] = True
                logger.debug("AppIndicator3 is available")
        except (ImportError, ValueError):
            try:
                # 尝试Ayatana AppIndicator
                gi.require_version('AyatanaAppIndicator3', '0.1')
                from gi.repository import AyatanaAppIndicator3
                env_info['appindicator_available'] = True
                logger.debug("AyatanaAppIndicator3 is available")
            except (ImportError, ValueError):
                logger.debug("No AppIndicator available")
                
    except ImportError:
        logger.debug("gi (PyGObject) not available")
    
    # 测试pystray可用性
    try:
        import pystray
        from PIL import Image
        env_info['pystray_available'] = True
        logger.debug("pystray is available")
    except ImportError:
        logger.debug("pystray not available")
    
    # 确定推荐后端
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


def create_optimal_tray_manager(config: UIConfig):
    """
    创建最佳可用的托盘管理器
    
    Args:
        config: UI配置对象
        
    Returns:
        托盘管理器实例或None（如果没有可用的）
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
            from .tray_pystray import PystrayTrayManager
            return PystrayTrayManager(config)
        except Exception as e:
            logger.warning(f"pystray tray manager failed: {e}")
    
    logger.error("No suitable tray manager available")
    return None


class SystemTrayManager:
    """
    智能系统托盘管理器 - 自动选择最佳实现
    
    作为实际托盘实现的代理，提供统一的接口。
    根据环境自动选择最适合的托盘后端实现。
    """
    
    def __init__(self, config: Optional[UIConfig] = None):
        """初始化智能托盘管理器"""
        self.config = config or UIConfig()
        self._impl = None
        self._env_info = detect_gtk_environment()
        self._create_implementation()
    
    def _create_implementation(self):
        """创建实际的托盘实现"""
        self._impl = create_optimal_tray_manager(self.config)
        if not self._impl:
            logger.error("Failed to create any tray manager implementation")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境检测信息"""
        return self._env_info.copy()
    
    def get_backend_name(self) -> str:
        """获取当前使用的后端名称"""
        if not self._impl:
            return "none"
        
        impl_class = self._impl.__class__.__name__
        if "GTK3" in impl_class:
            return "gtk3_appindicator"
        elif "GTK4" in impl_class:
            return "gtk4"
        elif "Pystray" in impl_class:
            return "pystray"
        else:
            return "unknown"
    
    # 代理所有方法到实际实现
    def start(self) -> None:
        """启动托盘管理器"""
        if self._impl:
            return self._impl.start()
        else:
            logger.warning("No tray implementation available")
    
    def stop(self) -> None:
        """停止托盘管理器"""
        if self._impl:
            return self._impl.stop()
    
    def update_status(self, status: TrayStatus) -> None:
        """更新托盘状态"""
        if self._impl:
            return self._impl.update_status(status)
    
    def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
        """显示通知"""
        if self._impl:
            return self._impl.show_notification(title, message, timeout)
    
    def set_on_quit(self, callback: Callable) -> None:
        """设置退出回调"""
        if self._impl:
            return self._impl.set_on_quit(callback)
    
    def set_on_toggle(self, callback: Callable) -> None:
        """设置切换识别回调"""
        if self._impl:
            return self._impl.set_on_toggle(callback)
    
    def set_on_settings(self, callback: Callable) -> None:
        """设置打开设置回调"""
        if self._impl:
            return self._impl.set_on_settings(callback)
    
    def set_on_about(self, callback: Callable) -> None:
        """设置关于回调"""
        if self._impl:
            return self._impl.set_on_about(callback)
    
    def update_menu(self) -> None:
        """更新托盘菜单"""
        if self._impl and hasattr(self._impl, 'update_menu'):
            return self._impl.update_menu()
    
    def is_running(self) -> bool:
        """检查托盘是否运行"""
        if self._impl:
            return self._impl.is_running()
        return False
    
    def is_available(self) -> bool:
        """检查托盘是否可用"""
        return self._impl is not None


# 向后兼容性别名
TrayManager = SystemTrayManager