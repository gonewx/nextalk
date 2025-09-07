"""
Input handling module for NexTalk.

Provides global hotkey management and keyboard event handling.
"""

from .hotkey import HotkeyManager
from .listener import KeyListener, HotkeyEvent

__all__ = [
    'HotkeyManager',
    'KeyListener',
    'HotkeyEvent',
]