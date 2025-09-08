"""
Text injection module for NexTalk.

Provides automatic text injection through IME frameworks.
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from ..config.models import TextInjectionConfig
from .ime_manager import IMEManager, IMEManagerFactory
from .ime_base import IMEResult


logger = logging.getLogger(__name__)


class TextInjector:
    """
    Manages text injection through IME frameworks.
    
    Provides IME-based text injection for stable and natural input.
    """
    
    def __init__(self, config: Optional[TextInjectionConfig] = None):
        """
        Initialize the text injector.
        
        Args:
            config: Text injection configuration
        """
        self.config = config or TextInjectionConfig()
        
        # IME Manager for text injection
        self._ime_manager: Optional[IMEManager] = None
        self._initialized = False
        
        # Statistics
        self._injection_count = 0
        self._success_count = 0
    
    async def initialize(self) -> bool:
        """
        Initialize the text injector.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
        
        try:
            # Check if IME is enabled
            if not self.config.use_ime:
                logger.warning("IME injection is disabled in configuration")
                return False
            
            # Create IME manager
            self._ime_manager = IMEManagerFactory.create_manager(self.config.ime_config)
            
            # Initialize IME manager
            if await self._ime_manager.initialize():
                self._initialized = True
                logger.info("Text injector initialized with IME support")
                return True
            else:
                logger.error("Failed to initialize IME manager")
                return False
                
        except Exception as e:
            logger.error(f"Text injector initialization failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """
        Clean up text injector resources.
        """
        try:
            if self._ime_manager:
                await self._ime_manager.cleanup()
                self._ime_manager = None
            
            self._initialized = False
            logger.info("Text injector cleaned up")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    async def inject_text(self, text: str) -> bool:
        """
        Inject text using IME framework.
        
        Args:
            text: Text to inject
            
        Returns:
            True if successful, False otherwise
        """
        if not text:
            logger.warning("Empty text, nothing to inject")
            return True
        
        if not self._initialized or not self._ime_manager:
            logger.error("Text injector not initialized")
            return False
        
        self._injection_count += 1
        
        try:
            # Apply injection delay if configured
            if self.config.inject_delay > 0:
                await asyncio.sleep(self.config.inject_delay)
            
            # Inject text through IME
            result: IMEResult = await self._ime_manager.inject_text(text)
            
            if result.success:
                self._success_count += 1
                logger.info(f"Text injected successfully via {result.ime_used}")
                return True
            else:
                logger.error(f"Text injection failed: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"Text injection failed with exception: {e}")
            return False
    
    async def get_ime_status(self) -> Dict[str, Any]:
        """
        Get current IME status.
        
        Returns:
            Dictionary with IME status information
        """
        if not self._initialized or not self._ime_manager:
            return {'status': 'not_initialized'}
        
        try:
            status = await self._ime_manager.get_ime_status()
            manager_status = self._ime_manager.get_manager_status()
            
            return {
                'ime_active': status.is_active,
                'current_ime': status.current_ime,
                'input_language': status.input_language,
                'focus_app': status.focus_app,
                'manager_state': manager_status.state.value,
                'ime_ready': await self._ime_manager.is_ime_ready()
            }
        except Exception as e:
            logger.error(f"Failed to get IME status: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get injection statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_injections': self._injection_count,
            'successful_injections': self._success_count,
            'failed_injections': self._injection_count - self._success_count,
            'success_rate': (self._success_count / self._injection_count * 100) 
                          if self._injection_count > 0 else 0.0,
            'initialized': self._initialized
        }
        
        # Add IME manager statistics if available
        if self._ime_manager:
            ime_stats = self._ime_manager.get_statistics()
            stats.update({'ime_' + k: v for k, v in ime_stats.items()})
        
        return stats
    
    async def test_injection(self) -> bool:
        """
        Test IME text injection with a simple string.
        
        Returns:
            True if test successful, False otherwise
        """
        test_text = "NexTalk IME injection test"
        
        logger.info("Testing IME text injection...")
        success = await self.inject_text(test_text)
        
        if success:
            logger.info("IME text injection test successful")
        else:
            logger.error("IME text injection test failed")
        
        return success
    
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
        Check if IME is ready for injection.
        
        Returns:
            True if IME is ready, False otherwise
        """
        if not self._initialized or not self._ime_manager:
            return False
        
        return self._ime_manager.is_ready
    
    def clear_statistics(self) -> None:
        """
        Clear injection statistics.
        """
        self._injection_count = 0
        self._success_count = 0
        logger.debug("Cleared text injection statistics")
    
    def get_compatibility_report(self) -> Dict[str, Any]:
        """
        Get a compatibility report for debugging.
        
        Returns:
            Dictionary with compatibility information
        """
        report = {
            'platform': 'Linux',  # Only Linux supported
            'initialized': self._initialized,
            'ime_enabled': self.config.use_ime,
            'statistics': self.get_statistics()
        }
        
        # Add IME manager report if available
        if self._ime_manager:
            manager_status = self._ime_manager.get_manager_status()
            report.update({
                'ime_manager_state': manager_status.state.value,
                'ime_adapter_type': manager_status.adapter_type,
                'ime_ready': manager_status.ime_ready
            })
        
        return report
    
    # Legacy compatibility methods (deprecated)
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
            return loop.run_until_complete(self.inject_text(text))
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(self.inject_text(text))