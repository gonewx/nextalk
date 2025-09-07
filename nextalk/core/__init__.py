"""
Core control module for NexTalk.

Provides main controller and session management.
"""

from .controller import (
    MainController,
    ControllerState,
    ControllerEvent,
    StateManager,
    StateTransition
)
from .session import RecognitionSession, SessionState

__all__ = [
    'MainController',
    'ControllerState',
    'ControllerEvent',
    'StateManager',
    'StateTransition',
    'RecognitionSession',
    'SessionState',
]