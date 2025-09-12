"""
增强的图标管理器 - 支持跨桌面环境的图标显示优化

功能特性：
- 启动时预加载所有PNG图标文件
- 自动检测桌面环境和主题
- 图标缓存和优化
- 多级回退机制确保兼容性
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# 尝试导入PIL用于图像处理
try:
    from PIL import Image as PILImage, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PILImage = None
    ImageDraw = None
    PIL_AVAILABLE = False
    logger.debug("PIL not available, direct image processing disabled")


class DesktopEnvironment:
    """桌面环境检测和配置"""

    @staticmethod
    def detect_environment() -> Dict[str, Any]:
        """检测当前桌面环境"""
        env_info = {
            "desktop": "unknown",
            "display_protocol": "unknown", 
            "theme": "light",
            "icon_theme": "hicolor",
            "preferred_sizes": [22, 24],
            "supports_svg": True,
            "needs_png_fallback": False,
        }

        # 检测桌面环境
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        if "gnome" in desktop or "unity" in desktop:
            env_info["desktop"] = "gnome"
            env_info["preferred_sizes"] = [22, 24, 32]
        elif "kde" in desktop or "plasma" in desktop:
            env_info["desktop"] = "kde"
            env_info["preferred_sizes"] = [22, 24]
        elif "xfce" in desktop:
            env_info["desktop"] = "xfce"
            env_info["preferred_sizes"] = [16, 22, 24]
            env_info["needs_png_fallback"] = True
        elif "lxde" in desktop or "lxqt" in desktop:
            env_info["desktop"] = "lxde"
            env_info["preferred_sizes"] = [16, 22]
            env_info["needs_png_fallback"] = True

        # 检测显示协议
        if os.environ.get("WAYLAND_DISPLAY"):
            env_info["display_protocol"] = "wayland"
        elif os.environ.get("DISPLAY"):
            env_info["display_protocol"] = "x11"

        # 检测主题
        gtk_theme = os.environ.get("GTK_THEME", "").lower()
        if "dark" in gtk_theme:
            env_info["theme"] = "dark"

        # 检测图标主题
        icon_theme = os.environ.get("ICON_THEME", "hicolor")
        env_info["icon_theme"] = icon_theme

        logger.info(f"Detected desktop environment: {env_info}")
        return env_info


class IconManager:
    """
    预加载式图标管理器，支持跨桌面环境优化。

    功能特性：
    - 启动时预加载所有PNG图标文件
    - 自动检测桌面环境和主题
    - 图标缓存和优化
    - 多级回退机制确保兼容性
    """

    ICON_STATUSES = ["idle", "active", "error"]  # 支持的图标状态

    def __init__(self) -> None:
        """初始化预加载式图标管理器"""
        self.icons_dir = Path(__file__).parent / "icons"
        self.env_info = DesktopEnvironment.detect_environment()

        # 预加载的PNG图标路径 (状态 -> PNG文件路径)
        self.preloaded_icons: Dict[str, str] = {}
        # PIL Image缓存 (状态 -> PIL Image对象)
        self.image_cache: Dict[str, Any] = {}

        # 系统图标备用方案
        self.fallback_icons = {
            "idle": "audio-input-microphone",
            "active": "audio-input-microphone-high", 
            "error": "dialog-error",
        }

        # 预加载所有图标
        self._preload_icons()

        logger.info(f"Icon manager initialized for {self.env_info['desktop']} desktop")
        logger.info(f"Preloaded {len(self.preloaded_icons)} PNG icon files")

    def _preload_icons(self) -> None:
        """预加载所有PNG图标文件路径"""
        for status in self.ICON_STATUSES:
            png_file = self.icons_dir / f"microphone-{status}.png"
            if png_file.exists():
                try:
                    self.preloaded_icons[status] = str(png_file.absolute())
                    logger.debug(f"Preloaded PNG icon path: {status}")
                    
                    # 同时预加载PIL Image对象（如果PIL可用）
                    if PIL_AVAILABLE:
                        image = PILImage.open(png_file)
                        self.image_cache[status] = image
                        logger.debug(f"Cached PIL image for: {status}")
                        
                except Exception as e:
                    logger.warning(f"Failed to preload icon {status}: {e}")
            else:
                logger.warning(f"PNG icon file not found: {png_file}")

    def get_icon_path(self, status: str) -> Optional[str]:
        """
        获取图标文件路径

        Args:
            status: 图标状态 (idle, active, error)

        Returns:
            PNG图标文件路径或系统图标名称
        """
        # 检查是否有预加载的PNG图标
        if status in self.preloaded_icons:
            return self.preloaded_icons[status]

        # 回退到系统图标
        system_icon = self.fallback_icons.get(status, "dialog-information")
        logger.debug(f"No preloaded icon for {status}, using system icon: {system_icon}")
        return system_icon

    def get_icon_image(self, status: str):
        """
        获取PNG图标的PIL Image对象
        
        Args:
            status: 图标状态 (idle, active, error)
            
        Returns:
            PIL Image对象或None
        """
        # 优先使用缓存的PIL Image
        if status in self.image_cache:
            return self.image_cache[status]
        
        # 如果没有缓存但有PNG文件路径，尝试加载
        if status in self.preloaded_icons and PIL_AVAILABLE:
            try:
                png_path = self.preloaded_icons[status]
                image = PILImage.open(png_path)
                # 缓存到内存
                self.image_cache[status] = image
                return image
            except Exception as e:
                logger.warning(f"Failed to load PNG image for {status}: {e}")
        
        # 回退到创建简单图标
        return self._create_fallback_image(status, 22)

    def get_optimized_icon_image(self, status: str):
        """
        获取优化的PIL Image对象，直接使用PNG文件
        
        Args:
            status: 图标状态 (idle, active, error)
            
        Returns:
            PIL Image对象或None
        """
        # 直接使用get_icon_image方法，它已经处理了PNG加载和缓存
        return self.get_icon_image(status)

    def _create_fallback_image(self, status: str, size: int):
        """创建回退的PIL Image对象，带透明背景的圆形图标"""
        if not PIL_AVAILABLE:
            return None
        
        # 创建带透明背景的图像
        image = PILImage.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # 创建一个简单的圆形图标
        draw = ImageDraw.Draw(image)
        
        # 颜色映射
        color_map = {
            'idle': (74, 144, 226, 255),    # 蓝色 #4a90e2
            'active': (76, 175, 80, 255),   # 绿色 #4caf50
            'error': (244, 67, 54, 255)     # 红色 #f44336
        }
        
        color = color_map.get(status, (128, 128, 128, 255))
        
        # 绘制圆形（模拟麦克风主体）
        margin = size // 8
        circle_box = [margin, margin, size - margin, size - margin]
        draw.ellipse(circle_box, fill=color)
        
        # 为active状态添加小圆点表示声音
        if status == 'active':
            dot_size = size // 10
            for i, x_offset in enumerate([-1.5, 1.5]):
                dot_x = size // 2 + int(x_offset * size // 4)
                dot_y = size // 2 + (i - 0.5) * size // 8
                dot_box = [
                    dot_x - dot_size, dot_y - dot_size,
                    dot_x + dot_size, dot_y + dot_size
                ]
                draw.ellipse(dot_box, fill=color)
        
        # 为error状态添加X标记
        elif status == 'error':
            line_width = max(1, size // 16)
            cross_margin = size // 4
            draw.line(
                [(cross_margin, cross_margin), (size - cross_margin, size - cross_margin)],
                fill=(255, 255, 255, 255), width=line_width
            )
            draw.line(
                [(size - cross_margin, cross_margin), (cross_margin, size - cross_margin)],
                fill=(255, 255, 255, 255), width=line_width
            )
        
        logger.debug(f"Created fallback PIL image for {status}: mode={image.mode}, size={image.size}")
        return image

    def get_preferred_size(self) -> int:
        """获取当前环境的首选图标尺寸"""
        preferred_sizes = self.env_info.get("preferred_sizes", [22])
        return int(preferred_sizes[0]) if preferred_sizes else 22

    def is_available(self) -> bool:
        """检查图标是否可用"""
        return len(self.preloaded_icons) > 0

    def get_preloaded_statuses(self) -> List[str]:
        """获取已预加载的图标状态列表"""
        return list(self.preloaded_icons.keys())

    def cleanup_cache(self) -> None:
        """清理图标缓存"""
        try:
            # 清理PIL Image内存缓存
            self.image_cache.clear()
            logger.info("Memory icon cache cleaned")
        except Exception as e:
            logger.warning(f"Failed to cleanup icon cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "preloaded_png_paths": len(self.preloaded_icons),
            "memory_cached_images": len(self.image_cache),
            "available_statuses": list(self.preloaded_icons.keys()),
        }

    def get_desktop_info(self) -> Dict[str, Any]:
        """获取桌面环境信息"""
        return self.env_info.copy()


# 全局实例
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """获取图标管理器实例（单例模式）"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager


def reload_icon_manager() -> IconManager:
    """重新加载图标管理器实例"""
    global _icon_manager
    if _icon_manager:
        _icon_manager.cleanup_cache()
    _icon_manager = IconManager()
    return _icon_manager