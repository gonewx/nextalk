"""
NexTalk Server 包

提供基于FunASR的实时语音识别服务。
"""

__version__ = "0.1.0"

from .app import app, create_app
from .websocket_handler import WebSocketHandler
from .funasr_model import FunASRModel
from .config import get_config, update_config

__all__ = [
    'app',
    'create_app',
    'WebSocketHandler',
    'FunASRModel',
    'AudioBuffer',
    'get_config',
    'update_config',
] 