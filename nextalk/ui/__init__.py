"""
User interface module for NexTalk.

Provides system tray integration and user interaction components.
"""

from .tray import SystemTrayManager, TrayStatus
from .menu import TrayMenu, MenuAction

__all__ = [
    'SystemTrayManager',
    'TrayStatus',
    'TrayMenu',
    'MenuAction',
]