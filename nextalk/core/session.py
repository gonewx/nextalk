"""
Recognition session management for NexTalk.

Manages individual voice recognition sessions.
"""

import logging
import time
import uuid
from enum import Enum
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
import asyncio


logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Recognition session states."""
    IDLE = "idle"
    STARTING = "starting"
    LISTENING = "listening"
    PROCESSING = "processing"
    INJECTING = "injecting"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class SessionMetrics:
    """Metrics for a recognition session."""
    session_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    audio_duration: float = 0.0
    processing_time: float = 0.0
    injection_time: float = 0.0
    total_duration: float = 0.0
    audio_bytes: int = 0
    recognized_text: str = ""
    injected_successfully: bool = False
    error_message: Optional[str] = None
    # IME-specific metrics
    ime_used: Optional[str] = None
    ime_ready: bool = False
    injection_method: str = "ime"
    
    def calculate_totals(self) -> None:
        """Calculate total durations."""
        if self.end_time > 0 and self.start_time > 0:
            self.total_duration = self.end_time - self.start_time


class RecognitionSession:
    """
    Manages a single voice recognition session.
    
    Handles the complete flow from audio capture to text injection.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize a recognition session.
        
        Args:
            session_id: Optional session ID (generated if not provided)
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.state = SessionState.IDLE
        self.metrics = SessionMetrics(session_id=self.session_id)
        
        # Audio buffer for captured audio
        self.audio_buffer: List[bytes] = []
        
        # Recognized text
        self.recognized_text = ""
        
        # Callbacks
        self._on_state_change: Optional[Callable[[SessionState], None]] = None
        self._on_text_recognized: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_complete: Optional[Callable[[SessionMetrics], None]] = None
        
        # Async event loop reference
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        logger.debug(f"Created session: {self.session_id}")
    
    def start(self) -> None:
        """Start the recognition session."""
        if self.state != SessionState.IDLE:
            logger.warning(f"Cannot start session in state: {self.state}")
            return
        
        self._change_state(SessionState.STARTING)
        self.metrics.start_time = time.time()
        
        logger.info(f"Session {self.session_id} started")
        self._change_state(SessionState.LISTENING)
    
    def stop(self) -> None:
        """Stop the recognition session."""
        if self.state not in [SessionState.LISTENING, SessionState.PROCESSING]:
            logger.warning(f"Cannot stop session in state: {self.state}")
            return
        
        self.metrics.end_time = time.time()
        self.metrics.calculate_totals()
        
        if self.state == SessionState.LISTENING:
            # Process any remaining audio
            self._change_state(SessionState.PROCESSING)
        
        logger.info(f"Session {self.session_id} stopped")
    
    def cancel(self) -> None:
        """Cancel the recognition session."""
        if self.state in [SessionState.COMPLETED, SessionState.CANCELLED]:
            return
        
        previous_state = self.state
        self._change_state(SessionState.CANCELLED)
        
        self.metrics.end_time = time.time()
        self.metrics.calculate_totals()
        
        logger.info(f"Session {self.session_id} cancelled from state: {previous_state}")
    
    def add_audio_data(self, data: bytes) -> None:
        """
        Add audio data to the session buffer.
        
        Args:
            data: Audio data bytes
        """
        if self.state != SessionState.LISTENING:
            logger.warning(f"Cannot add audio in state: {self.state}")
            return
        
        self.audio_buffer.append(data)
        self.metrics.audio_bytes += len(data)
        
        logger.info(f"Session {self.session_id}: Added {len(data)} bytes, total: {len(self.audio_buffer)} chunks, {self.metrics.audio_bytes} bytes")
    
    def process_recognition(self, text: str) -> None:
        """
        Process recognized text.
        
        Args:
            text: Recognized text from speech
        """
        if self.state not in [SessionState.LISTENING, SessionState.PROCESSING]:
            logger.warning(f"Cannot process recognition in state: {self.state}")
            return
        
        self._change_state(SessionState.PROCESSING)
        
        self.recognized_text = text
        self.metrics.recognized_text = text
        
        logger.info(f"Session {self.session_id} recognized: {text[:50]}...")
        
        if self._on_text_recognized:
            self._on_text_recognized(text)
        
        # Move to injection phase
        self._change_state(SessionState.INJECTING)
    
    def complete_injection(self, success: bool, ime_used: Optional[str] = None, 
                          injection_time: Optional[float] = None) -> None:
        """
        Complete the text injection phase.
        
        Args:
            success: Whether injection was successful
            ime_used: Name of IME used for injection
            injection_time: Time taken for injection in seconds
        """
        if self.state != SessionState.INJECTING:
            logger.warning(f"Cannot complete injection in state: {self.state}")
            return
        
        self.metrics.injected_successfully = success
        if ime_used:
            self.metrics.ime_used = ime_used
        if injection_time:
            self.metrics.injection_time = injection_time
        self.metrics.end_time = time.time()
        self.metrics.calculate_totals()
        
        self._change_state(SessionState.COMPLETED)
        
        logger.info(f"Session {self.session_id} completed (injection: {success}, IME: {ime_used})")
        
        if self._on_complete:
            self._on_complete(self.metrics)
    
    def report_error(self, error_message: str) -> None:
        """
        Report an error in the session.
        
        Args:
            error_message: Error description
        """
        self.metrics.error_message = error_message
        self.metrics.end_time = time.time()
        self.metrics.calculate_totals()
        
        self._change_state(SessionState.ERROR)
        
        logger.error(f"Session {self.session_id} error: {error_message}")
        
        if self._on_error:
            self._on_error(error_message)
    
    def _change_state(self, new_state: SessionState) -> None:
        """
        Change the session state.
        
        Args:
            new_state: New state to transition to
        """
        if new_state == self.state:
            return
        
        old_state = self.state
        self.state = new_state
        
        logger.debug(f"Session {self.session_id}: {old_state.value} -> {new_state.value}")
        
        if self._on_state_change:
            self._on_state_change(new_state)
    
    def set_on_state_change(self, callback: Callable[[SessionState], None]) -> None:
        """Set state change callback."""
        self._on_state_change = callback
    
    def set_on_text_recognized(self, callback: Callable[[str], None]) -> None:
        """Set text recognized callback."""
        self._on_text_recognized = callback
    
    def set_on_error(self, callback: Callable[[str], None]) -> None:
        """Set error callback."""
        self._on_error = callback
    
    def set_on_complete(self, callback: Callable[[SessionMetrics], None]) -> None:
        """Set completion callback."""
        self._on_complete = callback
    
    def update_ime_status(self, ime_ready: bool, ime_used: Optional[str] = None) -> None:
        """
        Update IME status information for this session.
        
        Args:
            ime_ready: Whether IME is ready for injection
            ime_used: Name of the IME being used
        """
        self.metrics.ime_ready = ime_ready
        if ime_used:
            self.metrics.ime_used = ime_used
        
        logger.debug(f"Session {self.session_id} IME status updated: ready={ime_ready}, ime={ime_used}")
    
    def get_audio_buffer(self) -> bytes:
        """
        Get the complete audio buffer.
        
        Returns:
            Combined audio data
        """
        # Only return audio if we have data
        if not self.audio_buffer:
            return b''
        return b''.join(self.audio_buffer)
    
    def clear_audio_buffer(self) -> None:
        """Clear the audio buffer."""
        self.audio_buffer.clear()
        logger.debug(f"Cleared audio buffer for session {self.session_id}")
    
    def is_active(self) -> bool:
        """
        Check if the session is active.
        
        Returns:
            True if session is in an active state
        """
        return self.state in [
            SessionState.STARTING,
            SessionState.LISTENING,
            SessionState.PROCESSING,
            SessionState.INJECTING
        ]
    
    def is_complete(self) -> bool:
        """
        Check if the session is complete.
        
        Returns:
            True if session has ended
        """
        return self.state in [
            SessionState.COMPLETED,
            SessionState.ERROR,
            SessionState.CANCELLED
        ]
    
    def get_summary(self) -> dict:
        """
        Get a summary of the session.
        
        Returns:
            Dictionary with session summary
        """
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "duration": self.metrics.total_duration,
            "audio_bytes": self.metrics.audio_bytes,
            "recognized_text": self.recognized_text[:100] if self.recognized_text else "",
            "success": self.metrics.injected_successfully,
            "error": self.metrics.error_message
        }