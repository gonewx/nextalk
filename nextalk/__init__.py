"""
NexTalk - 个人轻量级实时语音识别与输入系统

基于 FunASR WebSocket 的语音识别系统，提供：
- 系统托盘集成
- 全局快捷键触发
- 实时语音识别
- 智能文本注入
"""

__version__ = "0.1.0"
__author__ = "NexTalk Team"
__description__ = "个人轻量级实时语音识别与输入系统"

# 导出主要组件
from .core.controller import MainController
from .config.manager import ConfigManager

# 导出主入口
try:
    from .main import main, NexTalkApp
except ImportError:
    # 允许在未安装所有依赖时导入包
    main = None
    NexTalkApp = None

__all__ = [
    "MainController",
    "ConfigManager",
    "main",
    "NexTalkApp",
    "__version__",
    "__author__", 
    "__description__"
]