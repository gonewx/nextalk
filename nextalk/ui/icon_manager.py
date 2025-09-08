"""
简化的图标管理器 - 直接使用项目中的 SVG 文件
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class IconManager:
    """
    简化的图标管理器。
    
    直接使用项目中的 SVG 图标文件，无需复制、转换或安装操作。
    
    图标状态颜色：
    - idle: 蓝色 (#4a90e2) - 空闲状态  
    - active: 绿色 (#4caf50) - 活跃录音状态
    - error: 红色 (#f44336) - 错误状态
    """
    
    def __init__(self):
        """Initialize simple icon manager."""
        self.icons_dir = Path(__file__).parent / "icons"
        
        # 确保图标目录存在
        if not self.icons_dir.exists():
            logger.warning(f"Icons directory not found: {self.icons_dir}")
    
    def get_icon_path(self, status: str) -> Optional[str]:
        """
        直接获取项目中 SVG 图标的文件路径。
        
        Args:
            status: Icon status (idle, active, error)
            
        Returns:
            绝对路径字符串或 None
        """
        icon_file = self.icons_dir / f"microphone-{status}.svg"
        
        if icon_file.exists():
            return str(icon_file.absolute())
        else:
            logger.warning(f"Icon file not found: {icon_file}")
            return None
    
    def is_available(self) -> bool:
        """检查图标是否可用。"""
        return (
            self.icons_dir.exists() and 
            (self.icons_dir / "microphone-idle.svg").exists()
        )

# 全局实例
_icon_manager = None

def get_icon_manager() -> IconManager:
    """获取图标管理器实例。"""
    global _icon_manager
    if _icon_manager is None:
        _icon_manager = IconManager()
    return _icon_manager