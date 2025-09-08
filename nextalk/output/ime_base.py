"""
IME (Input Method Editor) base classes and interfaces.

Provides abstract interfaces for cross-platform IME integration.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime


logger = logging.getLogger(__name__)


class CompositionState(Enum):
    """IME composition states."""
    INACTIVE = "inactive"
    COMPOSING = "composing" 
    CONVERTING = "converting"
    COMMITTED = "committed"
    CANCELLED = "cancelled"


class IMEFramework(Enum):
    """Supported IME frameworks."""
    IBUS = "ibus"
    FCITX = "fcitx"
    UNKNOWN = "unknown"


@dataclass
class IMEInfo:
    """Information about the current IME."""
    name: str
    framework: IMEFramework
    language: str
    is_active: bool
    version: Optional[str] = None


@dataclass
class IMEResult:
    """Result of an IME operation."""
    success: bool
    text_injected: str
    ime_used: str
    injection_time: float
    error: Optional[str] = None
    retry_count: int = 0


@dataclass  
class IMEStatus:
    """Current IME system status."""
    is_active: bool
    current_ime: str
    composition_state: CompositionState
    input_language: str
    focus_app: str
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class IMEStateEvent:
    """IME state change event."""
    event_type: str
    old_state: Optional[IMEStatus]
    new_state: IMEStatus
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FocusEvent:
    """Window focus change event."""
    window_title: str
    app_name: str
    process_id: int
    timestamp: datetime = field(default_factory=datetime.now)


class IMEAdapter(ABC):
    """Abstract base class for platform-specific IME adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IME adapter with configuration.
        
        Args:
            config: IME configuration parameters
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the IME adapter.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up IME adapter resources."""
        pass
    
    @abstractmethod
    async def inject_text(self, text: str) -> IMEResult:
        """
        Inject text through the IME framework.
        
        Args:
            text: Text to inject
            
        Returns:
            IMEResult with operation status and details
        """
        pass
    
    @abstractmethod
    async def get_ime_status(self) -> IMEStatus:
        """
        Get current IME status.
        
        Returns:
            Current IME status information
        """
        pass
    
    @abstractmethod
    async def detect_active_ime(self) -> Optional[IMEInfo]:
        """
        Detect the currently active IME.
        
        Returns:
            IME information if detected, None otherwise
        """
        pass
    
    @abstractmethod
    async def is_ime_ready(self) -> bool:
        """
        Check if IME is ready for text injection.
        
        Returns:
            True if IME is ready, False otherwise
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized
    
    def _set_initialized(self, value: bool) -> None:
        """Set initialization status."""
        self._initialized = value


class IMEStateMonitor(ABC):
    """Abstract base class for IME state monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize state monitor.
        
        Args:
            config: Monitor configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._monitoring = False
    
    @abstractmethod
    async def start_monitoring(self) -> None:
        """Start monitoring IME state changes."""
        pass
    
    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop monitoring IME state changes."""
        pass
    
    @abstractmethod
    async def monitor_ime_state(self) -> AsyncGenerator[IMEStateEvent, None]:
        """
        Monitor IME state changes.
        
        Yields:
            IME state change events
        """
        pass
    
    @abstractmethod
    async def monitor_focus_changes(self) -> AsyncGenerator[FocusEvent, None]:
        """
        Monitor window focus changes.
        
        Yields:
            Focus change events
        """
        pass
    
    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring
    
    def _set_monitoring(self, value: bool) -> None:
        """Set monitoring status."""
        self._monitoring = value


class IMEException(Exception):
    """Base exception for IME operations."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        """
        Initialize IME exception.
        
        Args:
            message: Error message
            error_code: Optional error code
        """
        super().__init__(message)
        self.error_code = error_code


class IMEInitializationError(IMEException):
    """Exception raised when IME initialization fails."""
    pass


class IMEPermissionError(IMEException):
    """Exception raised when IME operations are denied due to permissions."""
    pass


class IMECompatibilityError(IMEException):
    """Exception raised when IME is not compatible with target application."""
    pass


class IMETimeoutError(IMEException):
    """Exception raised when IME operations timeout."""
    pass


class IMEStateError(IMEException):
    """Exception raised when IME is in invalid state."""
    pass