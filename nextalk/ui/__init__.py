"""
User interface module for NexTalk.

Provides system tray integration and user interaction components.
"""

from .tray import SystemTrayManager, TrayStatus
from .menu import TrayMenu, MenuAction
from .icon_manager import get_icon_manager

__all__ = [
    'SystemTrayManager',
    'TrayStatus',
    'TrayMenu',
    'MenuAction',
    'get_icon_manager',
]