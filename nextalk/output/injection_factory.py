"""
Injection strategy factory for automatic injector selection.

Provides intelligent selection of the best available text injection method
based on environment detection, with proper fallback and caching mechanisms.
"""

import logging
import time
from typing import Optional, Dict, Any, List, Type
from dataclasses import dataclass
from enum import Enum

from .base_injector import BaseInjector, InjectorManager
from .portal_injector import PortalInjector
from .xdotool_injector import XDoToolInjector
from .environment_detector import EnvironmentDetector, detect_environment
from .injection_models import (
    InjectionMethod,
    EnvironmentInfo,
    InjectorConfiguration,
    DisplayServerType,
    InjectorStatistics,
)
from .injection_exceptions import (
    InjectionError,
    EnvironmentError,
    InitializationError,
    ConfigurationError,
)


logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Strategy selection approaches."""

    PREFER_PORTAL = "prefer_portal"  # Portal first, xdotool fallback
    PREFER_XDOTOOL = "prefer_xdotool"  # xdotool first, Portal fallback
    PORTAL_ONLY = "portal_only"  # Portal only, no fallback
    XDOTOOL_ONLY = "xdotool_only"  # xdotool only, no fallback
    AUTO = "auto"  # Smart selection based on environment


@dataclass
class SelectionResult:
    """Result of injector selection."""

    injector: Optional[BaseInjector]
    method: InjectionMethod
    selection_reason: str
    fallback_used: bool = False
    selection_time: float = 0.0
    environment_info: Optional[EnvironmentInfo] = None
    alternatives_considered: List[InjectionMethod] = None

    def __post_init__(self):
        if self.alternatives_considered is None:
            self.alternatives_considered = []


class InjectionStrategyFactory:
    """
    Factory for creating and selecting optimal text injection strategies.

    This factory intelligently selects the best available injection method
    based on environment detection, user preferences, and system capabilities.
    """

    def __init__(self, config: Optional[InjectorConfiguration] = None):
        """
        Initialize the strategy factory.

        Args:
            config: Configuration for injectors and selection logic
        """
        self.config = config or InjectorConfiguration()
        self._environment_detector = EnvironmentDetector()
        self._cached_result: Optional[SelectionResult] = None
        self._cache_valid_until = 0.0
        self._cache_duration = 300.0  # 5 minutes cache

        # Selection preferences
        self._selection_strategy = self._determine_selection_strategy()

        # Available injector classes
        self._injector_classes: Dict[InjectionMethod, Type[BaseInjector]] = {
            InjectionMethod.PORTAL: PortalInjector,
            InjectionMethod.XDOTOOL: XDoToolInjector,
        }

        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._logger.debug(
            f"Strategy factory initialized with strategy: {self._selection_strategy.value}"
        )

    def _determine_selection_strategy(self) -> SelectionStrategy:
        """Determine selection strategy from configuration."""
        preferred = self.config.preferred_method

        if preferred == InjectionMethod.PORTAL:
            return (
                SelectionStrategy.PORTAL_ONLY
                if not self.config.fallback_enabled
                else SelectionStrategy.PREFER_PORTAL
            )
        elif preferred == InjectionMethod.XDOTOOL:
            return (
                SelectionStrategy.XDOTOOL_ONLY
                if not self.config.fallback_enabled
                else SelectionStrategy.PREFER_XDOTOOL
            )
        else:
            return SelectionStrategy.AUTO

    async def create_injector(self, force_refresh: bool = False) -> SelectionResult:
        """
        Create the best available injector for the current environment.

        Args:
            force_refresh: If True, bypass cache and re-evaluate

        Returns:
            SelectionResult with chosen injector and metadata

        Raises:
            InjectionError: If no suitable injector can be created
        """
        start_time = time.time()

        # Check cache first
        if not force_refresh and self._is_cache_valid():
            self._logger.debug("Returning cached injector selection")
            cached_result = self._cached_result
            cached_result.selection_time = time.time() - start_time
            return cached_result

        try:
            self._logger.info("Selecting optimal text injection strategy")

            # Detect environment
            env_info = self._environment_detector.detect_environment(force_refresh)
            self._logger.debug(
                f"Environment: {env_info.display_server.value}, recommended: {env_info.recommended_method.value}"
            )

            # Select strategy based on configuration and environment
            result = await self._select_injector_strategy(env_info)
            result.selection_time = time.time() - start_time
            result.environment_info = env_info

            # Cache successful result
            if result.injector:
                self._cache_result(result)
                self._logger.info(
                    f"Selected {result.method.value} injector ({result.selection_reason})"
                )
            else:
                self._logger.error("No suitable injector available")
                raise InjectionError("No suitable text injection method available")

            return result

        except Exception as e:
            self._logger.error(f"Injector selection failed: {e}")
            raise InjectionError(f"Failed to create text injector: {e}") from e

    async def _select_injector_strategy(self, env_info: EnvironmentInfo) -> SelectionResult:
        """Select injector based on strategy and environment."""
        alternatives = []

        if self._selection_strategy == SelectionStrategy.AUTO:
            # Smart selection based on environment
            return await self._auto_select_injector(env_info, alternatives)

        elif self._selection_strategy == SelectionStrategy.PREFER_PORTAL:
            # Try Portal first, fallback to xdotool
            alternatives = [InjectionMethod.PORTAL, InjectionMethod.XDOTOOL]
            return await self._try_injectors_in_order(alternatives, env_info)

        elif self._selection_strategy == SelectionStrategy.PREFER_XDOTOOL:
            # Try xdotool first, fallback to Portal
            alternatives = [InjectionMethod.XDOTOOL, InjectionMethod.PORTAL]
            return await self._try_injectors_in_order(alternatives, env_info)

        elif self._selection_strategy == SelectionStrategy.PORTAL_ONLY:
            # Portal only, no fallback
            return await self._try_single_injector(
                InjectionMethod.PORTAL, env_info, "Portal only (configured)"
            )

        elif self._selection_strategy == SelectionStrategy.XDOTOOL_ONLY:
            # xdotool only, no fallback
            return await self._try_single_injector(
                InjectionMethod.XDOTOOL, env_info, "xdotool only (configured)"
            )

        else:
            raise ConfigurationError(f"Unknown selection strategy: {self._selection_strategy}")

    async def _auto_select_injector(
        self, env_info: EnvironmentInfo, alternatives: List[InjectionMethod]
    ) -> SelectionResult:
        """Automatically select the best injector based on environment."""

        # Use environment recommendation as starting point
        preferred_method = env_info.recommended_method

        if preferred_method == InjectionMethod.PORTAL:
            alternatives = [InjectionMethod.PORTAL, InjectionMethod.XDOTOOL]
            reason = f"Portal preferred for {env_info.display_server.value}"
        elif preferred_method == InjectionMethod.XDOTOOL:
            alternatives = [InjectionMethod.XDOTOOL, InjectionMethod.PORTAL]
            reason = f"xdotool preferred for {env_info.display_server.value}"
        else:
            # No clear preference, try both
            alternatives = [InjectionMethod.PORTAL, InjectionMethod.XDOTOOL]
            reason = "No clear preference, trying Portal first"

        result = await self._try_injectors_in_order(alternatives, env_info)
        if result.injector:
            result.selection_reason = f"Auto: {reason}"

        return result

    async def _try_injectors_in_order(
        self, methods: List[InjectionMethod], env_info: EnvironmentInfo
    ) -> SelectionResult:
        """Try injectors in the specified order."""
        last_error = None

        for i, method in enumerate(methods):
            try:
                result = await self._try_single_injector(
                    method,
                    env_info,
                    f"Preferred method" if i == 0 else f"Fallback after {methods[0].value} failed",
                )

                if result.injector:
                    result.fallback_used = i > 0
                    result.alternatives_considered = methods.copy()
                    return result

            except Exception as e:
                self._logger.debug(f"{method.value} injector failed: {e}")
                last_error = e
                continue

        # All methods failed
        return SelectionResult(
            injector=None,
            method=InjectionMethod.AUTO,
            selection_reason=f"All methods failed (tried: {[m.value for m in methods]})",
            alternatives_considered=methods,
        )

    async def _try_single_injector(
        self, method: InjectionMethod, env_info: EnvironmentInfo, reason: str
    ) -> SelectionResult:
        """Try to create a single injector."""
        try:
            injector_class = self._injector_classes.get(method)
            if not injector_class:
                raise InjectionError(f"Unknown injection method: {method}")

            # Check availability first
            injector = injector_class(self.config)
            available = await injector.check_availability()

            if not available:
                self._logger.debug(f"{method.value} injector not available")
                return SelectionResult(
                    injector=None, method=method, selection_reason=f"{method.value} not available"
                )

            # Try to initialize
            success = await injector.initialize()

            if success:
                return SelectionResult(injector=injector, method=method, selection_reason=reason)
            else:
                await injector.cleanup()  # Cleanup failed initialization
                return SelectionResult(
                    injector=None,
                    method=method,
                    selection_reason=f"{method.value} initialization failed",
                )

        except Exception as e:
            self._logger.debug(f"Failed to create {method.value} injector: {e}")
            return SelectionResult(
                injector=None,
                method=method,
                selection_reason=f"{method.value} creation failed: {e}",
            )

    def _cache_result(self, result: SelectionResult):
        """Cache a successful selection result."""
        self._cached_result = result
        self._cache_valid_until = time.time() + self._cache_duration
        self._logger.debug(f"Cached injector selection for {self._cache_duration}s")

    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid."""
        return (
            self._cached_result is not None
            and time.time() < self._cache_valid_until
            and self._cached_result.injector is not None
            and self._cached_result.injector.is_initialized
        )

    def clear_cache(self):
        """Clear cached selection result."""
        if self._cached_result and self._cached_result.injector:
            # Don't cleanup the injector here - it might be in use
            pass

        self._cached_result = None
        self._cache_valid_until = 0.0
        self._logger.debug("Injector selection cache cleared")

    async def get_available_methods(self) -> List[InjectionMethod]:
        """
        Get list of available injection methods.

        Returns:
            List of methods that are available in current environment
        """
        available = []

        for method, injector_class in self._injector_classes.items():
            try:
                injector = injector_class(self.config)
                if await injector.check_availability():
                    available.append(method)
            except Exception as e:
                self._logger.debug(f"Availability check for {method.value} failed: {e}")

        return available

    async def create_specific_injector(self, method: InjectionMethod) -> Optional[BaseInjector]:
        """
        Create a specific injector type.

        Args:
            method: Injection method to create

        Returns:
            Initialized injector or None if creation failed
        """
        try:
            injector_class = self._injector_classes.get(method)
            if not injector_class:
                raise InjectionError(f"Unknown injection method: {method}")

            injector = injector_class(self.config)

            if await injector.check_availability():
                if await injector.initialize():
                    return injector
                else:
                    await injector.cleanup()

            return None

        except Exception as e:
            self._logger.error(f"Failed to create {method.value} injector: {e}")
            return None

    async def test_all_injectors(self) -> Dict[InjectionMethod, bool]:
        """
        Test all available injectors.

        Returns:
            Dictionary mapping methods to test results
        """
        results = {}

        for method in self._injector_classes.keys():
            try:
                injector = await self.create_specific_injector(method)
                if injector:
                    try:
                        result = await injector.test_injection()
                        results[method] = result
                    finally:
                        await injector.cleanup()
                else:
                    results[method] = False

            except Exception as e:
                self._logger.debug(f"Test for {method.value} failed: {e}")
                results[method] = False

        return results

    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status and configuration."""
        status = {
            "selection_strategy": self._selection_strategy.value,
            "cache_valid": self._is_cache_valid(),
            "cache_expires_in": (
                max(0, self._cache_valid_until - time.time()) if self._cache_valid_until > 0 else 0
            ),
            "config": {
                "preferred_method": self.config.preferred_method.value,
                "fallback_enabled": self.config.fallback_enabled,
                "retry_attempts": self.config.retry_attempts,
            },
            "available_injectors": list(self._injector_classes.keys()),
        }

        if self._cached_result:
            status["cached_selection"] = {
                "method": self._cached_result.method.value,
                "reason": self._cached_result.selection_reason,
                "fallback_used": self._cached_result.fallback_used,
                "selection_time": self._cached_result.selection_time,
            }

        return status


# Singleton instance for global access
_factory_instance: Optional[InjectionStrategyFactory] = None


def get_injection_factory(
    config: Optional[InjectorConfiguration] = None,
) -> InjectionStrategyFactory:
    """Get the global injection strategy factory instance."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = InjectionStrategyFactory(config)
    return _factory_instance


async def create_best_injector(config: Optional[InjectorConfiguration] = None) -> SelectionResult:
    """Convenience function to create the best available injector."""
    factory = get_injection_factory(config)
    return await factory.create_injector()


def clear_factory_cache():
    """Clear the global factory cache."""
    global _factory_instance
    if _factory_instance:
        _factory_instance.clear_cache()
