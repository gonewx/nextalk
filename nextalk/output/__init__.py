"""
Output handling module for NexTalk.

Provides text injection and clipboard management functionality.
"""

from .text_injector import TextInjector, InjectionMethod
from .clipboard import ClipboardManager

__all__ = [
    'TextInjector',
    'InjectionMethod',
    'ClipboardManager',
]