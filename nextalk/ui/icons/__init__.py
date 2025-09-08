"""
NexTalk custom icons package.

Contains SVG icons specifically designed for NexTalk system tray.
"""

# 重新导出原来的IconManager，保持向后兼容
from .icons import IconManager, IconTheme

__all__ = ['IconManager', 'IconTheme']