"""
文本注入模块。

提供跨平台的文本注入功能，支持多种注入方式：
- 输入法框架（Fcitx/IBus）
- 剪贴板粘贴
- 模拟键盘输入
"""

from .injector_base import BaseInjector, get_injector
from .injector_manager import SmartInjector
from .ime_detector import IMEDetector

__all__ = [
    'BaseInjector',
    'get_injector',
    'SmartInjector',
    'IMEDetector',
]