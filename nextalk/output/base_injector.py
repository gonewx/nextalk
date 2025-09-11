"""
Abstract base class for text injection implementations.

Defines the common interface that all text injector implementations must follow,
ensuring consistency and enabling polymorphic usage across the system.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .injection_models import (
    InjectorState,
    InjectionResult,
    InjectionMethod,
    InjectorConfiguration,
    InjectorStatistics,
)
from .injection_exceptions import InjectionError


logger = logging.getLogger(__name__)


@dataclass
class InjectorCapabilities:
    """Describes the capabilities of an injector implementation."""

    method: InjectionMethod
    supports_keyboard: bool = True
    supports_mouse: bool = False
    requires_permissions: bool = False
    requires_external_tools: bool = False
    platform_specific: bool = False
    description: str = ""

    def __post_init__(self):
        """Set default description if not provided."""
        if not self.description:
            self.description = f"{self.method.value.title()} text injection"


class BaseInjector(ABC):
    """
    Abstract base class for all text injection implementations.

    This class defines the common interface that all injector implementations
    must follow, including lifecycle management, configuration handling,
    and text injection operations.
    """

    def __init__(self, config: Optional[InjectorConfiguration] = None):
        """
        Initialize the base injector.

        Args:
            config: Injector configuration
        """
        self.config = config or InjectorConfiguration()
        self._state = InjectorState.UNINITIALIZED
        self._statistics = InjectorStatistics()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._lock = asyncio.Lock()

    # Abstract properties that must be implemented

    @property
    @abstractmethod
    def capabilities(self) -> InjectorCapabilities:
        """Get the capabilities of this injector implementation."""
        pass

    @property
    @abstractmethod
    def method(self) -> InjectionMethod:
        """Get the injection method type."""
        pass

    # State management properties

    @property
    def state(self) -> InjectorState:
        """Get current injector state."""
        return self._state

    @property
    def is_initialized(self) -> bool:
        """Check if injector is initialized."""
        return self._state in (InjectorState.READY, InjectorState.INJECTING)

    @property
    def is_ready(self) -> bool:
        """Check if injector is ready for text injection."""
        return self._state == InjectorState.READY

    @property
    def statistics(self) -> InjectorStatistics:
        """Get injection statistics."""
        return self._statistics

    # Abstract lifecycle methods

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the injector implementation.

        This method should perform all necessary setup operations,
        including checking dependencies, establishing connections,
        and preparing for text injection.

        Returns:
            True if initialization succeeded, False otherwise

        Raises:
            InitializationError: If initialization fails critically
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up injector resources.

        This method should release all resources, close connections,
        and perform any necessary cleanup operations.
        """
        pass

    # Abstract injection methods

    @abstractmethod
    async def inject_text(self, text: str) -> InjectionResult:
        """
        Inject text using this implementation.

        Args:
            text: Text to inject

        Returns:
            InjectionResult with operation details

        Raises:
            InjectionError: If injection fails
        """
        pass

    @abstractmethod
    async def test_injection(self) -> bool:
        """
        Test if text injection is working.

        This method should perform a basic test to verify that
        text injection is functioning properly.

        Returns:
            True if test succeeded, False otherwise
        """
        pass

    # Abstract capability checking

    @abstractmethod
    async def check_availability(self) -> bool:
        """
        Check if this injector implementation is available.

        This method should verify that all required dependencies,
        services, and permissions are available.

        Returns:
            True if implementation is available, False otherwise
        """
        pass

    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get detailed health status information.

        Returns:
            Dictionary with health status details
        """
        pass

    # Protected helper methods for concrete implementations

    async def _set_state(self, new_state: InjectorState):
        """Thread-safe state transition."""
        async with self._lock:
            old_state = self._state
            self._state = new_state
            self._logger.debug(f"State transition: {old_state.value} -> {new_state.value}")

    async def _validate_text(self, text: str) -> str:
        """
        Validate and prepare text for injection.

        Args:
            text: Text to validate

        Returns:
            Validated and prepared text

        Raises:
            InjectionError: If text is invalid
        """
        if not text:
            raise InjectionError("Text cannot be empty")

        if len(text) > 10000:  # Reasonable limit
            raise InjectionError(f"Text too long: {len(text)} characters")

        # Basic sanitization - remove null bytes and control characters
        sanitized = text.replace("\0", "").replace("\x08", "")  # Remove null and backspace

        return sanitized

    async def _update_statistics_success(self, result: InjectionResult):
        """Update statistics for successful injection."""
        self._statistics.update_success(result.method_used, result.injection_time)

    async def _update_statistics_failure(self):
        """Update statistics for failed injection."""
        self._statistics.update_failure()

    # Common implementation methods

    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status information.

        Returns:
            Dictionary with status information
        """
        health_status = await self.get_health_status()

        return {
            "state": self._state.value,
            "method": self.method.value,
            "initialized": self.is_initialized,
            "ready": self.is_ready,
            "capabilities": {
                "supports_keyboard": self.capabilities.supports_keyboard,
                "supports_mouse": self.capabilities.supports_mouse,
                "requires_permissions": self.capabilities.requires_permissions,
                "requires_external_tools": self.capabilities.requires_external_tools,
                "platform_specific": self.capabilities.platform_specific,
                "description": self.capabilities.description,
            },
            "statistics": {
                "total_injections": self._statistics.total_injections,
                "successful_injections": self._statistics.successful_injections,
                "failed_injections": self._statistics.failed_injections,
                "success_rate": self._statistics.success_rate,
                "average_injection_time": self._statistics.average_injection_time,
            },
            "health": health_status,
            "config": {
                "retry_attempts": self.config.retry_attempts,
                "retry_delay": self.config.retry_delay,
                "debug_logging": self.config.debug_logging,
            },
        }

    async def inject_text_with_retry(self, text: str) -> InjectionResult:
        """
        Inject text with automatic retry on failure.

        Args:
            text: Text to inject

        Returns:
            InjectionResult with operation details
        """
        if not self.is_ready:
            raise InjectionError(f"Injector not ready. Current state: {self._state.value}")

        last_error = None

        for attempt in range(self.config.retry_attempts + 1):
            try:
                await self._set_state(InjectorState.INJECTING)

                result = await self.inject_text(text)
                result.retry_count = attempt

                await self._set_state(InjectorState.READY)
                await self._update_statistics_success(result)

                return result

            except InjectionError as e:
                last_error = e
                self._logger.warning(f"Injection attempt {attempt + 1} failed: {e}")

                if attempt < self.config.retry_attempts:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    await self._update_statistics_failure()
                    await self._set_state(InjectorState.ERROR)

        # All retries exhausted
        raise InjectionError(
            f"Text injection failed after {self.config.retry_attempts + 1} attempts"
        ) from last_error

    @asynccontextmanager
    async def managed_lifecycle(self):
        """
        Context manager for automatic lifecycle management.

        Usage:
            async with injector.managed_lifecycle():
                result = await injector.inject_text("Hello")
        """
        try:
            await self.initialize()
            yield self
        finally:
            await self.cleanup()

    def clear_statistics(self):
        """Clear injection statistics."""
        self._statistics = InjectorStatistics()
        self._logger.debug("Statistics cleared")

    def __str__(self) -> str:
        """String representation of the injector."""
        return f"{self.__class__.__name__}({self.method.value}, {self._state.value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"{self.__class__.__name__}("
            f"method={self.method.value}, "
            f"state={self._state.value}, "
            f"initialized={self.is_initialized}"
            f")"
        )


class InjectorManager:
    """
    Helper class for managing multiple injector instances.

    This class provides utilities for working with multiple injector
    implementations, including selection and failover logic.
    """

    def __init__(self):
        """Initialize the injector manager."""
        self._injectors: List[BaseInjector] = []
        self._active_injector: Optional[BaseInjector] = None

    def register_injector(self, injector: BaseInjector):
        """Register an injector implementation."""
        self._injectors.append(injector)
        logger.debug(f"Registered injector: {injector}")

    def get_available_injectors(self) -> List[BaseInjector]:
        """Get list of registered injectors."""
        return self._injectors.copy()

    def get_methods(self) -> List[InjectionMethod]:
        """Get list of available injection methods."""
        return [injector.method for injector in self._injectors]

    async def select_best_injector(self) -> Optional[BaseInjector]:
        """
        Select the best available injector.

        Returns:
            Best available injector or None if none available
        """
        available = []

        for injector in self._injectors:
            try:
                if await injector.check_availability():
                    available.append(injector)
            except Exception as e:
                logger.debug(f"Injector {injector} availability check failed: {e}")

        if not available:
            return None

        # Prefer Portal over xdotool
        for injector in available:
            if injector.method == InjectionMethod.PORTAL:
                return injector

        # Return first available as fallback
        return available[0]

    async def get_status_all(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all registered injectors."""
        status = {}

        for injector in self._injectors:
            try:
                status[injector.method.value] = await injector.get_status()
            except Exception as e:
                status[injector.method.value] = {"error": str(e), "available": False}

        return status
