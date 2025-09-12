"""
增强的图标管理器 - 支持跨桌面环境的图标显示优化
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
import tempfile

logger = logging.getLogger(__name__)

# 尝试导入SVG渲染库
try:
    import cairosvg
    SVG_RENDER_AVAILABLE = True
except ImportError:
    SVG_RENDER_AVAILABLE = False
    logger.debug("cairosvg not available, PNG generation disabled")

# 尝试导入PIL用于图像处理
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
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
    - 启动时预加载所有图标文件到内存
    - 自动检测桌面环境和主题
    - 支持多种尺寸的图标生成
    - SVG到PNG的内存转换
    - 主题感知的图标选择
    - 多级回退机制确保兼容性
    """

    ICON_SIZES = [16, 22, 24, 32, 48]  # 支持的图标尺寸
    ICON_STATUSES = ["idle", "active", "error"]  # 支持的图标状态

    def __init__(self) -> None:
        """初始化预加载式图标管理器"""
        self.icons_dir = Path(__file__).parent / "icons"
        self.cache_dir = Path(tempfile.gettempdir()) / "nextalk_icons"
        self.env_info = DesktopEnvironment.detect_environment()

        # 预加载的图标数据 (状态 -> SVG内容)
        self.preloaded_icons: Dict[str, str] = {}
        # PNG缓存 ("状态-尺寸" -> PNG字节数据)
        self.png_cache: Dict[str, bytes] = {}

        # 创建缓存目录
        self.cache_dir.mkdir(exist_ok=True)

        # 图标状态颜色映射
        self.status_colors = {"idle": "#4a90e2", "active": "#4caf50", "error": "#f44336"}  # 蓝色  # 绿色  # 红色

        # 系统图标备用方案
        self.fallback_icons = {
            "idle": "audio-input-microphone",
            "active": "audio-input-microphone-high",
            "error": "dialog-error",
        }

        # 预加载所有图标
        self._preload_icons()

        logger.info(f"Icon manager initialized for {self.env_info['desktop']} desktop")
        logger.info(f"Preloaded {len(self.preloaded_icons)} icon files")

    def _preload_icons(self) -> None:
        """预加载所有图标文件到内存"""
        for status in self.ICON_STATUSES:
            svg_file = self.icons_dir / f"microphone-{status}.svg"
            if svg_file.exists():
                try:
                    with open(svg_file, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    self.preloaded_icons[status] = svg_content
                    logger.debug(f"Preloaded SVG icon: {status}")
                except Exception as e:
                    logger.warning(f"Failed to preload icon {status}: {e}")
            else:
                logger.warning(f"Icon file not found: {svg_file}")

    def get_icon_path(self, status: str, size: Optional[int] = None) -> Optional[str]:
        """
        获取最适合当前环境的图标路径

        Args:
            status: 图标状态 (idle, active, error)
            size: 期望的图标尺寸，None使用环境默认

        Returns:
            图标文件路径或系统图标名称
        """
        # 确定图标尺寸
        if size is None:
            preferred_sizes = self.env_info.get("preferred_sizes", [22])
            size = int(preferred_sizes[0]) if preferred_sizes else 22

        # 检查是否有预加载的图标
        if status not in self.preloaded_icons:
            # 如果没有预加载的图标，回退到系统图标
            system_icon = self.fallback_icons.get(status, "dialog-information")
            logger.debug(f"No preloaded icon for {status}, using system icon: {system_icon}")
            return system_icon

        # 如果需要PNG图标或不支持SVG
        if self.env_info["needs_png_fallback"] or not self.env_info["supports_svg"]:
            png_path = self._get_or_generate_png_from_memory(status, size)
            if png_path:
                logger.debug(f"Using generated PNG icon: {png_path}")
                return png_path

        # 如果支持SVG，生成临时SVG文件
        svg_path = self._get_temporary_svg_path(status)
        if svg_path:
            logger.debug(f"Using temporary SVG icon: {svg_path}")
            return svg_path

        # 最终回退到系统图标
        system_icon = self.fallback_icons.get(status, "dialog-information")
        logger.debug(f"Using system fallback icon: {system_icon}")
        return system_icon

    def _get_temporary_svg_path(self, status: str) -> Optional[str]:
        """从内存中的SVG数据生成临时文件路径"""
        if status not in self.preloaded_icons:
            return None

        try:
            # 生成临时SVG文件
            temp_svg = self.cache_dir / f"microphone-{status}.svg"

            # 如果文件不存在，创建它
            if not temp_svg.exists():
                with open(temp_svg, "w", encoding="utf-8") as f:
                    f.write(self.preloaded_icons[status])

            return str(temp_svg.absolute())

        except Exception as e:
            logger.warning(f"Failed to create temporary SVG file: {e}")
            return None

    def _get_or_generate_png_from_memory(self, status: str, size: int) -> Optional[str]:
        """从内存中的SVG数据生成PNG图标"""
        if status not in self.preloaded_icons:
            return None

        cache_key = f"{status}-{size}"

        # 检查内存缓存
        if cache_key in self.png_cache:
            # 从内存缓存写入临时文件
            png_file = self.cache_dir / f"microphone-{status}-{size}.png"
            try:
                with open(png_file, "wb") as f:
                    f.write(self.png_cache[cache_key])
                return str(png_file)
            except Exception as e:
                logger.warning(f"Failed to write cached PNG: {e}")

        # 检查磁盘缓存
        png_file = self.cache_dir / f"microphone-{status}-{size}.png"
        if png_file.exists():
            return str(png_file)

        # 生成新的PNG
        if SVG_RENDER_AVAILABLE:
            return self._generate_png_from_memory(status, size)

        return None

    def _generate_png_from_memory(self, status: str, size: int) -> Optional[str]:
        """从内存中的SVG数据生成PNG图标"""
        if status not in self.preloaded_icons:
            return None

        try:
            svg_content = self.preloaded_icons[status]
            png_file = self.cache_dir / f"microphone-{status}-{size}.png"

            # 使用cairosvg从字符串转换
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"), 
                output_width=size, 
                output_height=size
                # 不设置background_color
            )

            # 保存到文件
            with open(png_file, "wb") as f:
                f.write(png_data)

            # 缓存到内存
            cache_key = f"{status}-{size}"
            self.png_cache[cache_key] = png_data

            logger.debug(f"Generated PNG icon from memory: {png_file}")
            return str(png_file)

        except Exception as e:
            logger.warning(f"Failed to generate PNG from memory: {e}")
            return None

    def get_available_sizes(self) -> List[int]:
        """获取可用的图标尺寸"""
        return self.ICON_SIZES.copy()

    def get_preferred_size(self) -> int:
        """获取当前环境的首选图标尺寸"""
        preferred_sizes = self.env_info.get("preferred_sizes", [22])
        return int(preferred_sizes[0]) if preferred_sizes else 22

    def is_available(self) -> bool:
        """检查图标是否可用"""
        # 检查是否至少有一个预加载的图标
        return len(self.preloaded_icons) > 0

    def get_preloaded_statuses(self) -> List[str]:
        """获取已预加载的图标状态列表"""
        return list(self.preloaded_icons.keys())

    def cleanup_cache(self) -> None:
        """清理图标缓存"""
        try:
            # 清理磁盘缓存
            if self.cache_dir.exists():
                for file in self.cache_dir.glob("microphone-*"):
                    file.unlink()
                logger.info("Disk icon cache cleaned")

            # 清理内存缓存
            self.png_cache.clear()
            logger.info("Memory icon cache cleaned")

        except Exception as e:
            logger.warning(f"Failed to cleanup icon cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "preloaded_icons": len(self.preloaded_icons),
            "memory_cached_pngs": len(self.png_cache),
            "disk_cache_dir": str(self.cache_dir),
            "available_statuses": list(self.preloaded_icons.keys()),
        }

    def get_svg_path_direct(self, status: str) -> Optional[str]:
        """
        直接获取SVG文件的绝对路径，用于pystray直接使用
        
        Args:
            status: 图标状态 (idle, active, error)
            
        Returns:
            SVG文件的绝对路径，如果文件不存在则返回None
        """
        if status in self.preloaded_icons:
            # 优先使用原始SVG文件路径
            svg_file = self.icons_dir / f"microphone-{status}.svg"
            if svg_file.exists():
                logger.debug(f"Found direct SVG file: {svg_file}")
                return str(svg_file.absolute())
        
        # 如果原始文件不存在，尝试临时文件
        temp_svg = self.cache_dir / f"microphone-{status}.svg"
        if temp_svg.exists():
            logger.debug(f"Using cached SVG file: {temp_svg}")
            return str(temp_svg.absolute())
        
        # 如果没有临时文件，创建一个
        if status in self.preloaded_icons:
            try:
                with open(temp_svg, 'w', encoding='utf-8') as f:
                    f.write(self.preloaded_icons[status])
                logger.debug(f"Created temporary SVG file: {temp_svg}")
                return str(temp_svg.absolute())
            except Exception as e:
                logger.warning(f"Failed to create temporary SVG: {e}")
        
        return None

    def get_optimized_icon_image(self, status: str):
        """
        获取优化的PIL Image对象，专门针对系统托盘显示优化
        
        Args:
            status: 图标状态 (idle, active, error)
            
        Returns:
            PIL Image对象或None
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot create optimized image")
            return self._create_fallback_image(status, 22)
        
        # 检查是否有预加载的图标
        if status not in self.preloaded_icons:
            logger.debug(f"No preloaded icon for {status}")
            return self._create_fallback_image(status, 22)
        
        try:
            # 如果有cairosvg，进行优化转换
            if SVG_RENDER_AVAILABLE:
                svg_content = self.preloaded_icons[status]
                
                # 直接使用22x22尺寸，避免缩放导致的比例问题
                final_size = 22   # SVG原始设计尺寸
                
                # 使用cairosvg转换为PNG，不设置背景色以保持透明
                png_data = cairosvg.svg2png(
                    bytestring=svg_content.encode('utf-8'),
                    output_width=final_size,
                    output_height=final_size
                    # 不设置background_color参数，让SVG的透明背景自然保留
                )
                
                # 从字节数据创建PIL Image
                import io
                image = PILImage.open(io.BytesIO(png_data))
                
                # 确保是RGBA模式以支持透明背景
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                logger.debug(f"Generated optimized PIL image for {status}: {image.mode} {image.size}")
                return image
            
            else:
                # 没有cairosvg，使用改进的回退方案
                logger.debug(f"cairosvg not available, using fallback for {status}")
                return self._create_fallback_image(status, 22)
                
        except Exception as e:
            logger.warning(f"Failed to create optimized PIL image for {status}: {e}")
            return self._create_fallback_image(status, 22)

    def get_desktop_info(self) -> Dict[str, Any]:
        """获取桌面环境信息"""
        return self.env_info.copy()

    def get_icon_image(self, status: str, size: int = 22):
        """
        获取PIL Image对象，专为pystray使用
        
        Args:
            status: 图标状态 (idle, active, error)
            size: 图标尺寸，默认22以匹配SVG原始尺寸
            
        Returns:
            PIL Image对象或None
        """
        if not PIL_AVAILABLE:
            logger.warning("PIL not available, cannot create image")
            return self._create_fallback_image(status, size)
        
        # 检查是否有预加载的图标
        if status not in self.preloaded_icons:
            logger.debug(f"No preloaded icon for {status}")
            return self._create_fallback_image(status, size)
        
        try:
            # 如果有cairosvg，从SVG直接生成PIL Image
            if SVG_RENDER_AVAILABLE:
                svg_content = self.preloaded_icons[status]
                
                # 使用cairosvg转换为PNG字节数据
                png_data = cairosvg.svg2png(
                    bytestring=svg_content.encode('utf-8'),
                    output_width=size,
                    output_height=size
                    # 不设置background_color参数
                )
                
                # 从字节数据创建PIL Image
                import io
                image = PILImage.open(io.BytesIO(png_data))
                
                # 保持RGBA模式以支持透明背景
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                logger.debug(f"Generated PIL Image from SVG for {status}: mode={image.mode}, size={image.size}")
                return image
            
            else:
                # 没有cairosvg，使用回退方案
                logger.debug(f"cairosvg not available, using fallback for {status}")
                return self._create_fallback_image(status, size)
                
        except Exception as e:
            logger.warning(f"Failed to create PIL image for {status}: {e}")
            return self._create_fallback_image(status, size)
    
    def _create_fallback_image(self, status: str, size: int):
        """创建回退的PIL Image对象，带透明背景的圆形图标"""
        if not PIL_AVAILABLE:
            return None
        
        # 创建带透明背景的图像
        image = PILImage.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # 创建一个简单的圆形图标
        from PIL import ImageDraw
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


# 全局实例
_icon_manager: Optional[IconManager] = None


def get_icon_manager() -> IconManager:
    """获取图标管理器实例（单例模式）。"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager


def reload_icon_manager() -> IconManager:
    """重新加载图标管理器实例。"""
    global _icon_manager
    if _icon_manager:
        _icon_manager.cleanup_cache()
    _icon_manager = IconManager()
    return _icon_manager
