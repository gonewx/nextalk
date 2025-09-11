"""
Text injection module for NexTalk.

Provides automatic text injection through modern injection mechanisms
with backward compatibility for legacy configurations.
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from .injection_factory import InjectionStrategyFactory, SelectionResult, get_injection_factory
from .base_injector import BaseInjector
from .injection_models import InjectorConfiguration, InjectionMethod, InjectionResult
from .injection_exceptions import InjectionError, InitializationError


logger = logging.getLogger(__name__)


class TextInjector:
    """
    Manages text injection through modern injection mechanisms.

    This class provides backward compatibility with the legacy IME-based
    text injection API while internally using the new strategy factory
    and injection architecture.
    """

    def __init__(self, config: Optional[InjectorConfiguration] = None):
        """
        Initialize the text injector.

        Args:
            config: Injector configuration
        """
        self._injector_config = config or InjectorConfiguration()
        
        # For backward compatibility, also store as legacy config
        self.config = self._injector_config

        # Strategy factory and active injector
        self._factory: Optional[InjectionStrategyFactory] = None
        self._active_injector: Optional[BaseInjector] = None
        self._selection_result: Optional[SelectionResult] = None

        # Legacy compatibility state
        self._initialized = False

        # Statistics (legacy compatibility)
        self._injection_count = 0
        self._success_count = 0

        logger.debug("TextInjector created with modern architecture")


    async def initialize(self) -> bool:
        """
        Initialize the text injector.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            logger.info("Initializing modern text injector")

            # Create strategy factory
            self._factory = InjectionStrategyFactory(self._injector_config)

            # Select and initialize best injector
            self._selection_result = await self._factory.create_injector()

            if self._selection_result.injector:
                self._active_injector = self._selection_result.injector
                self._initialized = True

                logger.info(
                    f"Text injector initialized with {self._selection_result.method.value} "
                    f"({self._selection_result.selection_reason})"
                )

                # Modern injection system fully initialized

                return True
            else:
                logger.error(
                    f"No suitable injector available: {self._selection_result.selection_reason}"
                )
                return False

        except Exception as e:
            logger.error(f"Text injector initialization failed: {e}")
            return False

    async def cleanup(self) -> None:
        """
        Clean up text injector resources.
        """
        try:
            logger.info("Cleaning up text injector")

            if self._active_injector:
                await self._active_injector.cleanup()
                self._active_injector = None

            self._selection_result = None
            self._factory = None
            self._initialized = False

            logger.info("Text injector cleanup complete")

        except Exception as e:
            logger.warning(f"Error during text injector cleanup: {e}")

    async def inject_text(self, text: str) -> InjectionResult:
        """
        Inject text using the selected injection method.

        Args:
            text: Text to inject

        Returns:
            InjectionResult with operation details
        """
        if not text:
            logger.warning("Empty text, nothing to inject")
            # Return success result for empty text
            return InjectionResult(
                success=True,
                method_used=InjectionMethod.AUTO,
                text_length=0,
                error_message="Empty text - nothing to inject"
            )

        if not self._initialized or not self._active_injector:
            logger.error("Text injector not initialized")
            return InjectionResult(
                success=False,
                method_used=InjectionMethod.AUTO,
                text_length=len(text),
                error_message="Text injector not initialized"
            )

        self._injection_count += 1

        try:
            # Apply legacy injection delay if configured
            if self.config.inject_delay > 0:
                await asyncio.sleep(self.config.inject_delay)

            # Use modern injection with retry
            result: InjectionResult = await self._active_injector.inject_text_with_retry(text)

            if result.success:
                self._success_count += 1
                logger.info(f"Text injected successfully via {result.method_used.value}")

            return result

        except Exception as e:
            logger.error(f"Text injection failed with exception: {e}")

            # Attempt recovery by re-selecting injector
            await self._attempt_recovery()
            
            # Return failure result
            return InjectionResult(
                success=False,
                method_used=self._active_injector.method if self._active_injector else InjectionMethod.AUTO,
                text_length=len(text),
                error_message=str(e)
            )

    async def _attempt_recovery(self):
        """Attempt to recover from injection failure by re-selecting injector."""
        try:
            logger.info("Attempting injector recovery")

            if self._factory:
                # Clear cache and try to get a new injector
                self._factory.clear_cache()
                new_result = await self._factory.create_injector(force_refresh=True)

                if new_result.injector and new_result.injector != self._active_injector:
                    # Clean up old injector
                    if self._active_injector:
                        await self._active_injector.cleanup()

                    # Switch to new injector
                    self._active_injector = new_result.injector
                    self._selection_result = new_result

                    logger.info(f"Recovered with {new_result.method.value} injector")

        except Exception as e:
            logger.warning(f"Recovery attempt failed: {e}")

    async def get_ime_status(self) -> Dict[str, Any]:
        """
        Get current injection system status.

        Legacy compatibility method - returns status in expected format.

        Returns:
            Dictionary with status information
        """
        if not self._initialized:
            return {"status": "not_initialized"}

        if not self._active_injector:
            return {"status": "no_active_injector"}

        try:
            # Get modern injector status
            status = await self._active_injector.get_status()

            # Convert to legacy-compatible format
            return {
                "status": "active",
                "injector_type": status["method"],
                "initialized": status["initialized"],
                "ready": status["ready"],
                "method_used": status["method"],
                "active_method": status["method"],  # Add active_method for controller compatibility
                "statistics": status["statistics"],
                "modern_status": status,  # Include full modern status
            }

        except Exception as e:
            logger.error(f"Failed to get injector status: {e}")
            return {"status": "error", "error": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get injection statistics.

        Returns:
            Dictionary with statistics (legacy compatible)
        """
        stats = {
            "total_injections": self._injection_count,
            "successful_injections": self._success_count,
            "failed_injections": self._injection_count - self._success_count,
            "success_rate": (
                (self._success_count / self._injection_count * 100)
                if self._injection_count > 0
                else 0.0
            ),
            "initialized": self._initialized,
            "mode": "modern",
        }

        # Add modern injector statistics if available
        if self._active_injector:
            try:
                modern_stats = self._active_injector.statistics
                stats.update(
                    {
                        "modern_total": modern_stats.total_injections,
                        "modern_success": modern_stats.successful_injections,
                        "modern_failed": modern_stats.failed_injections,
                        "modern_success_rate": modern_stats.success_rate,
                        "average_injection_time": modern_stats.average_injection_time,
                        "portal_injections": modern_stats.portal_injections,
                        "xdotool_injections": modern_stats.xdotool_injections,
                    }
                )
            except Exception as e:
                logger.debug(f"Could not get modern statistics: {e}")

        return stats

    async def test_injection(self) -> bool:
        """
        Test text injection with a simple string.

        Returns:
            True if test successful, False otherwise
        """
        if not self._initialized or not self._active_injector:
            logger.error("Cannot test injection - injector not initialized")
            return False

        try:
            test_text = "NexTalk modern injection test"
            logger.info("Testing modern text injection...")

            success = await self.inject_text(test_text)

            if success:
                logger.info("Modern text injection test successful")
            else:
                logger.error("Modern text injection test failed")

            return success

        except Exception as e:
            logger.error(f"Text injection test failed: {e}")
            return False

    @property
    def is_initialized(self) -> bool:
        """
        Check if text injector is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    @property
    def ime_ready(self) -> bool:
        """
        Check if injection system is ready.

        Legacy compatibility property.

        Returns:
            True if ready, False otherwise
        """
        return (
            self._initialized
            and self._active_injector is not None
            and self._active_injector.is_ready
        )

    def clear_statistics(self) -> None:
        """
        Clear injection statistics.
        """
        self._injection_count = 0
        self._success_count = 0

        if self._active_injector:
            self._active_injector.clear_statistics()

        logger.debug("Cleared text injection statistics")

    def get_compatibility_report(self) -> Dict[str, Any]:
        """
        Get a compatibility report for debugging.

        Returns:
            Dictionary with compatibility information
        """
        report = {
            "platform": "Linux",
            "initialized": self._initialized,
            "mode": "modern",
            "legacy_compatibility": True,
            "config_type": "modern",
            "statistics": self.get_statistics(),
        }

        # Add selection information
        if self._selection_result:
            report.update(
                {
                    "selected_method": self._selection_result.method.value,
                    "selection_reason": self._selection_result.selection_reason,
                    "fallback_used": self._selection_result.fallback_used,
                    "selection_time": self._selection_result.selection_time,
                    "alternatives_considered": [
                        m.value for m in self._selection_result.alternatives_considered
                    ],
                }
            )

        # Add active injector status
        if self._active_injector:
            try:
                injector_status = asyncio.create_task(self._active_injector.get_status())
                # We can't await here, so just indicate availability
                report["active_injector"] = {
                    "type": self._active_injector.method.value,
                    "state": self._active_injector.state.value,
                    "capabilities": {
                        "supports_keyboard": self._active_injector.capabilities.supports_keyboard,
                        "requires_permissions": self._active_injector.capabilities.requires_permissions,
                        "requires_external_tools": self._active_injector.capabilities.requires_external_tools,
                    },
                }
            except Exception as e:
                report["active_injector_error"] = str(e)

        return report

    async def get_factory_status(self) -> Dict[str, Any]:
        """
        Get status of the injection factory (new method).

        Returns:
            Factory status information
        """
        if not self._factory:
            return {"error": "Factory not initialized"}

        return self._factory.get_factory_status()

    async def switch_method(self, method: InjectionMethod) -> bool:
        """
        Switch to a specific injection method (new method).

        Args:
            method: Injection method to switch to

        Returns:
            True if switch successful
        """
        try:
            if not self._factory:
                logger.error("Cannot switch method - factory not initialized")
                return False

            # Create specific injector
            new_injector = await self._factory.create_specific_injector(method)

            if new_injector:
                # Clean up old injector
                if self._active_injector:
                    await self._active_injector.cleanup()

                # Switch to new injector
                self._active_injector = new_injector
                logger.info(f"Switched to {method.value} injection method")
                return True
            else:
                logger.error(f"Could not create {method.value} injector")
                return False

        except Exception as e:
            logger.error(f"Method switch failed: {e}")
            return False

    # Legacy compatibility methods (deprecated but maintained)
    def inject_text_sync(self, text: str) -> bool:
        """
        Legacy synchronous text injection method.

        This method is deprecated. Use inject_text() with async/await instead.

        Args:
            text: Text to inject

        Returns:
            True if successful, False otherwise
        """
        logger.warning("inject_text_sync is deprecated, use async inject_text instead")

        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.inject_text(text))
            return result.success if result else False
        except RuntimeError:
            # No event loop running, create new one
            result = asyncio.run(self.inject_text(text))
            return result.success if result else False
        except Exception as e:
            logger.error(f"inject_text_sync failed: {e}")
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of the modern injection system.
        
        Returns:
            Dictionary with health status information
        """
        status = {
            "initialized": self._initialized,
            "active_injector": self._active_injector is not None,
            "factory_available": self._factory is not None,
        }
        
        if not self._initialized:
            status["status"] = "not_initialized"
            return status
            
        if not self._active_injector:
            status["status"] = "no_active_injector"
            return status
            
        try:
            # Get injector health status
            injector_status = await self._active_injector.get_health_status()
            status.update(injector_status)
            status["status"] = "healthy"
            
            # Add injection statistics
            status.update({
                "total_injections": self._injection_count,
                "successful_injections": self._success_count,
                "success_rate": (
                    (self._success_count / self._injection_count * 100) 
                    if self._injection_count > 0 else 0.0
                ),
            })
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            status["status"] = "error" 
            status["error"] = str(e)
            
        return status
