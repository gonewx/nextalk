"""
IME Manager - Unified interface for Input Method Editor operations.

Manages platform-specific IME adapters and provides a unified API
for text injection through IME frameworks.
"""

import asyncio
import logging
import platform
import time
from typing import Optional, Dict, Any, Type
from enum import Enum
from dataclasses import dataclass

from ..config.models import IMEConfig
from .ime_base import (
    IMEAdapter, IMEStateMonitor, IMEResult, IMEStatus, IMEInfo,
    IMEException, IMEInitializationError, IMEPermissionError,
    IMETimeoutError, IMEStateError
)
from .ime_linux import LinuxIMEAdapter, LinuxIMEStateMonitor
from .text_processor import TextProcessor, ProcessedText


logger = logging.getLogger(__name__)


class IMEManagerState(Enum):
    """IME Manager states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class IMEManagerStatus:
    """Status of the IME Manager."""
    state: IMEManagerState
    platform: str
    adapter_type: Optional[str]
    ime_ready: bool
    last_error: Optional[str]
    initialization_time: Optional[float]


class IMEManager:
    """
    Unified IME manager for cross-platform text injection.
    
    Provides a single interface for IME operations across different
    platforms and input method frameworks.
    """
    
    def __init__(self, config: IMEConfig):
        """
        Initialize IME manager.
        
        Args:
            config: IME configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # State management
        self._state = IMEManagerState.UNINITIALIZED
        self._adapter: Optional[IMEAdapter] = None
        self._text_processor = TextProcessor({
            'format_text': True,
            'strip_whitespace': True,
            'normalize_punctuation': True,
            'segment_mixed_text': True
        })
        
        # Platform detection
        self._platform = platform.system().lower()
        self._adapter_class: Optional[Type[IMEAdapter]] = None
        
        # Statistics
        self._injection_count = 0
        self._success_count = 0
        self._error_count = 0
        self._initialization_time: Optional[float] = None
    
    async def initialize(self) -> bool:
        """
        Initialize the IME manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if not self.config.enabled:
            self._state = IMEManagerState.DISABLED
            self.logger.info("IME manager disabled by configuration")
            return True
        
        self._state = IMEManagerState.INITIALIZING
        start_time = time.time()
        
        try:
            # Select and create adapter
            adapter_class = self._select_adapter_class()
            if not adapter_class:
                self._state = IMEManagerState.ERROR
                self.logger.error("No suitable IME adapter found for current platform")
                return False
            
            # Create and initialize adapter
            adapter_config = self._create_adapter_config()
            self._adapter = adapter_class(adapter_config)
            
            success = await self._adapter.initialize()
            
            if success:
                self._state = IMEManagerState.READY
                self._initialization_time = time.time() - start_time
                self.logger.info(f"IME manager initialized successfully in {self._initialization_time:.3f}s")
                return True
            else:
                self._state = IMEManagerState.ERROR
                self.logger.error("Failed to initialize IME adapter")
                return False
                
        except Exception as e:
            self._state = IMEManagerState.ERROR
            self.logger.error(f"IME manager initialization failed: {e}")
            return False
    
    
    async def cleanup(self) -> None:
        """Clean up IME manager resources."""
        try:
            if self._adapter:
                await self._adapter.cleanup()
                self._adapter = None
            
            self._state = IMEManagerState.UNINITIALIZED
            self.logger.info("IME manager cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during IME manager cleanup: {e}")
    
    async def inject_text(self, text: str) -> IMEResult:
        """
        Inject text using the IME framework.
        
        Args:
            text: Text to inject
            
        Returns:
            IMEResult with operation status and details
        """
        if self._state == IMEManagerState.DISABLED:
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="disabled",
                injection_time=0.0,
                error="IME manager is disabled"
            )
        
        if self._state != IMEManagerState.READY:
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="error",
                injection_time=0.0,
                error=f"IME manager not ready (state: {self._state.value})"
            )
        
        if not self._adapter:
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="error",
                injection_time=0.0,
                error="No IME adapter available"
            )
        
        self._injection_count += 1
        
        try:
            # Preprocess text for optimal IME input
            ime_info = await self._adapter.detect_active_ime()
            processed_text = self._text_processor.preprocess_for_ime(text, ime_info)
            
            if self.config.debug_mode:
                self.logger.debug(f"Processing text: {text} -> {processed_text.processed}")
                self.logger.debug(f"Text type: {processed_text.text_type.value}")
                self.logger.debug(f"IME hints: {processed_text.ime_hints}")
            
            # Inject processed text
            result = await self._adapter.inject_text(processed_text.processed)
            
            # Update statistics
            if result.success:
                self._success_count += 1
            else:
                self._error_count += 1
            
            # Add processing information to result
            result.text_injected = processed_text.processed if result.success else ""
            
            return result
            
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Text injection failed: {e}")
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="error",
                injection_time=0.0,
                error=str(e)
            )
    
    async def get_ime_status(self) -> IMEStatus:
        """
        Get current IME status.
        
        Returns:
            Current IME status information
        """
        if self._state != IMEManagerState.READY or not self._adapter:
            # Return default status when not ready
            return IMEStatus(
                is_active=False,
                current_ime="unknown",
                composition_state="inactive",
                input_language="en",
                focus_app="unknown"
            )
        
        try:
            return await self._adapter.get_ime_status()
        except Exception as e:
            self.logger.error(f"Failed to get IME status: {e}")
            return IMEStatus(
                is_active=False,
                current_ime="error",
                composition_state="inactive",
                input_language="en",
                focus_app="unknown"
            )
    
    async def detect_active_ime(self) -> Optional[IMEInfo]:
        """
        Detect the currently active IME.
        
        Returns:
            IME information if detected, None otherwise
        """
        if self._state != IMEManagerState.READY or not self._adapter:
            return None
        
        try:
            return await self._adapter.detect_active_ime()
        except Exception as e:
            self.logger.error(f"Failed to detect active IME: {e}")
            return None
    
    async def is_ime_ready(self) -> bool:
        """
        Check if IME is ready for text injection.
        
        Returns:
            True if IME is ready, False otherwise
        """
        if self._state == IMEManagerState.DISABLED:
            return False  # Disabled means not ready for IME injection
        
        if self._state != IMEManagerState.READY or not self._adapter:
            return False
        
        try:
            return await self._adapter.is_ime_ready()
        except Exception:
            return False
    
    def get_manager_status(self) -> IMEManagerStatus:
        """Get the status of the IME manager itself."""
        return IMEManagerStatus(
            state=self._state,
            platform=self._platform,
            adapter_type=self._adapter.__class__.__name__ if self._adapter else None,
            ime_ready=self._state == IMEManagerState.READY,
            last_error=None,  # TODO: Track last error
            initialization_time=self._initialization_time
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get IME injection statistics."""
        return {
            'total_injections': self._injection_count,
            'successful_injections': self._success_count,
            'failed_injections': self._error_count,
            'success_rate': (self._success_count / self._injection_count * 100) 
                          if self._injection_count > 0 else 0.0,
            'state': self._state.value,
            'platform': self._platform,
            'initialization_time': self._initialization_time
        }
    
    def _select_adapter_class(self) -> Optional[Type[IMEAdapter]]:
        """Select the appropriate IME adapter class for the current platform."""
        if self._platform == "linux":
            return LinuxIMEAdapter
        elif self._platform == "win32":
            # TODO: Implement Windows IME adapter
            self.logger.debug("Windows IME adapter not yet implemented")
            return None
        elif self._platform == "darwin":
            # TODO: Implement macOS IME adapter  
            self.logger.debug("macOS IME adapter not yet implemented")
            return None
        else:
            self.logger.debug(f"Platform {self._platform} not supported yet")
            return None
    
    def _create_adapter_config(self) -> Dict[str, Any]:
        """Create configuration for the IME adapter."""
        return {
            'enabled': self.config.enabled,
            'preferred_framework': self.config.preferred_framework,
            'fallback_timeout': self.config.fallback_timeout,
            'composition_timeout': self.config.composition_timeout,
            'state_monitor_interval': self.config.state_monitor_interval,
            'auto_detect_ime': self.config.auto_detect_ime,
            'linux_ime_frameworks': self.config.linux_ime_frameworks,
            'dbus_timeout': self.config.dbus_timeout,
            'debug_mode': self.config.debug_mode
        }
    
    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._state in [IMEManagerState.READY, IMEManagerState.DISABLED]
    
    @property
    def is_ready(self) -> bool:
        """Check if manager is ready for operations."""
        return self._state == IMEManagerState.READY
    
    @property
    def is_disabled(self) -> bool:
        """Check if manager is disabled."""
        return self._state == IMEManagerState.DISABLED


class IMEManagerFactory:
    """Factory for creating IME managers."""
    
    @staticmethod
    def create_manager(config: IMEConfig) -> IMEManager:
        """
        Create an IME manager instance.
        
        Args:
            config: IME configuration
            
        Returns:
            Configured IME manager instance
        """
        return IMEManager(config)
    
    @staticmethod
    def create_state_monitor(config: IMEConfig) -> Optional[IMEStateMonitor]:
        """
        Create an IME state monitor for the current platform.
        
        Args:
            config: IME configuration
            
        Returns:
            Platform-specific state monitor or None if not supported
        """
        platform_name = platform.system().lower()
        
        if platform_name == "linux":
            adapter_config = {
                'state_monitor_interval': config.state_monitor_interval,
                'linux_ime_frameworks': config.linux_ime_frameworks,
                'dbus_timeout': config.dbus_timeout,
                'debug_mode': config.debug_mode
            }
            return LinuxIMEStateMonitor(adapter_config)
        else:
            logger.warning(f"State monitoring not supported on platform: {platform_name}")
            return None