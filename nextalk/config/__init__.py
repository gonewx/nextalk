"""
Configuration management package for NexTalk.

Provides configuration loading, validation, and management functionality.
"""

from .manager import ConfigManager
from .models import NexTalkConfig

__all__ = ["ConfigManager", "NexTalkConfig"]