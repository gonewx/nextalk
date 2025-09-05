"""
文本注入模块。

提供跨平台的文本注入功能，支持多种注入方式：
- 输入法框架（Fcitx/IBus）
- 终端专用注入器
- 剪贴板粘贴
- 模拟键盘输入
"""

from .ime_detector import IMEDetector
from .injector_base import BaseInjector, get_injector
from .injector_manager import SmartInjector
from .injector_terminal import TerminalInjector

__all__ = [
    "BaseInjector",
    "get_injector",
    "SmartInjector",
    "TerminalInjector",
    "IMEDetector",
]
