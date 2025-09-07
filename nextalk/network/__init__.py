"""
Network communication package for NexTalk.

Provides WebSocket client functionality for communicating with FunASR servers.
"""

from .ws_client import FunASRWebSocketClient, WebSocketError, ConnectionState
from .protocol import FunASRProtocol, MessageType

__all__ = [
    "FunASRWebSocketClient", 
    "WebSocketError", 
    "ConnectionState",
    "FunASRProtocol",
    "MessageType"
]