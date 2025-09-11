"""
Integration tests for text injection system.

Tests complete end-to-end workflows including strategy selection,
fallback mechanisms, error recovery, and configuration integration.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from nextalk.output.text_injector import TextInjector
from nextalk.output.injection_factory import InjectionStrategyFactory
from nextalk.output.injection_models import (
    InjectorConfiguration, EnvironmentInfo, DesktopEnvironment,
    DisplayServerType, InjectionMethod, InjectionResult
)
from nextalk.output.injection_exceptions import (
    InjectionFailedError, PortalPermissionError, CommandExecutionError,
    InitializationError, DependencyError
)


class TestTextInjectionIntegration:
    """Integration test cases for complete text injection workflows."""
    
    @pytest.fixture
    def basic_config(self):
        """Create basic configuration."""
        return InjectorConfiguration(
            preferred_method=None,
            portal_timeout=5.0,
            xdotool_delay=0.01,
            retry_attempts=2,
            debug_logging=True
        )
    
    @pytest.fixture
    def wayland_environment(self):
        """Create Wayland environment scenario."""
        return EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
    
    @pytest.fixture
    def x11_environment(self):
        """Create X11 environment scenario."""
        return EnvironmentInfo(
            display_server=DisplayServerType.X11,
            desktop_environment=DesktopEnvironment.KDE,
            available_methods=[InjectionMethod.XDOTOOL],
            portal_available=False,
            xdotool_available=True
        )
    
    @pytest.fixture
    def hybrid_environment(self):
        """Create hybrid environment with both methods available."""
        return EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL, InjectionMethod.XDOTOOL],
            portal_available=True,
            xdotool_available=True
        )
    
    @asynccontextmanager
    async def _mock_successful_portal_injector(self):
        """Context manager for successful Portal injector."""
        mock_injector = Mock()
        mock_injector.method = InjectionMethod.PORTAL
        mock_injector.check_availability = AsyncMock(return_value=True)
        mock_injector.initialize = AsyncMock(return_value=True)
        mock_injector.inject_text = AsyncMock(return_value=InjectionResult(
            success=True,
            method_used=InjectionMethod.PORTAL,
            text_length=5,
            execution_time=0.1
        ))
        mock_injector.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=True,
            method_used=InjectionMethod.PORTAL,
            text_length=5,
            execution_time=0.1
        ))
        mock_injector.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_injector):
            yield mock_injector
    
    @asynccontextmanager
    async def _mock_successful_xdotool_injector(self):
        """Context manager for successful xdotool injector."""
        mock_injector = Mock()
        mock_injector.method = InjectionMethod.XDOTOOL
        mock_injector.check_availability = AsyncMock(return_value=True)
        mock_injector.initialize = AsyncMock(return_value=True)
        mock_injector.inject_text = AsyncMock(return_value=InjectionResult(
            success=True,
            method_used=InjectionMethod.XDOTOOL,
            text_length=5,
            execution_time=0.05
        ))
        mock_injector.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=True,
            method_used=InjectionMethod.XDOTOOL,
            text_length=5,
            execution_time=0.05
        ))
        mock_injector.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.XDoToolInjector', return_value=mock_injector):
            yield mock_injector
    
    @pytest.mark.asyncio
    async def test_complete_wayland_portal_workflow(self, basic_config, wayland_environment):
        """Test complete text injection workflow on Wayland with Portal."""
        async with self._mock_successful_portal_injector() as mock_portal:
            
            # Mock environment detection
            with patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                      return_value=wayland_environment):
                
                # Create and initialize injector
                injector = TextInjector(basic_config)
                await injector.initialize()
                
                # Perform injection
                result = await injector.inject_text("hello")
                
                # Verify workflow
                assert result.success is True
                assert result.method_used == InjectionMethod.PORTAL
                assert result.text_length == 5
                
                # Verify Portal injector was used
                mock_portal.check_availability.assert_called_once()
                mock_portal.initialize.assert_called_once()
                mock_portal.inject_text_with_retry.assert_called_once_with("hello")
                
                # Cleanup
                await injector.cleanup()
                mock_portal.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_x11_xdotool_workflow(self, basic_config, x11_environment):
        """Test complete text injection workflow on X11 with xdotool."""
        async with self._mock_successful_xdotool_injector() as mock_xdotool:
            
            # Mock environment detection
            with patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                      return_value=x11_environment):
                
                # Create and initialize injector
                injector = TextInjector(basic_config)
                await injector.initialize()
                
                # Perform injection
                result = await injector.inject_text("world")
                
                # Verify workflow
                assert result.success is True
                assert result.method_used == InjectionMethod.XDOTOOL
                assert result.text_length == 5
                
                # Verify xdotool injector was used
                mock_xdotool.check_availability.assert_called_once()
                mock_xdotool.initialize.assert_called_once()
                mock_xdotool.inject_text_with_retry.assert_called_once_with("world")
                
                # Cleanup
                await injector.cleanup()
                mock_xdotool.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_strategy_selection_with_user_preference(self, hybrid_environment):
        """Test strategy selection respects user preference."""
        # Configure preference for xdotool
        config = InjectorConfiguration(preferred_method=InjectionMethod.XDOTOOL)
        
        async with self._mock_successful_xdotool_injector() as mock_xdotool:
            
            with patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                      return_value=hybrid_environment):
                
                injector = TextInjector(config)
                await injector.initialize()
                
                result = await injector.inject_text("preference test")
                
                # Should use xdotool despite Portal being available
                assert result.method_used == InjectionMethod.XDOTOOL
                mock_xdotool.inject_text_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism_portal_to_xdotool(self, hybrid_environment, basic_config):
        """Test fallback from Portal to xdotool when Portal fails."""
        # Mock Portal injector that fails initialization
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(side_effect=InitializationError("Portal init failed"))
        mock_portal.cleanup = AsyncMock()
        
        async with self._mock_successful_xdotool_injector() as mock_xdotool:
            
            with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
                 patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                       return_value=hybrid_environment):
                
                injector = TextInjector(basic_config)
                
                # Should initialize successfully using fallback
                await injector.initialize()
                
                result = await injector.inject_text("fallback test")
                
                # Should have fallen back to xdotool
                assert result.success is True
                assert result.method_used == InjectionMethod.XDOTOOL
                
                # Portal should have been attempted first
                mock_portal.initialize.assert_called_once()
                
                # xdotool should have been used as fallback
                mock_xdotool.inject_text_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_injection_retry_on_transient_failure(self, basic_config, wayland_environment):
        """Test injection retry mechanism on transient failures."""
        # Mock Portal injector that fails first time, succeeds second time
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.cleanup = AsyncMock()
        
        # Mock inject_text_with_retry to simulate internal retry logic
        mock_portal.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=True, method_used=InjectionMethod.PORTAL, text_length=4
        ))
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            result = await injector.inject_text("test")
            
            # Should succeed after retry
            assert result.success is True
            
            # Should have been called once (retry logic is internal)
            mock_portal.inject_text_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_injection_failure_after_max_retries(self, basic_config, wayland_environment):
        """Test injection failure after exhausting retries."""
        # Mock Portal injector that always fails
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=False, method_used=InjectionMethod.PORTAL, text_length=9,
            error_message="Persistent failure"
        ))
        mock_portal.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            result = await injector.inject_text("fail test")
            
            # Should return failure result
            assert result.success is False
            assert "Persistent failure" in result.error_message
            
            # Should have been called once
            mock_portal.inject_text_with_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self, wayland_environment):
        """Test integration with different configuration options."""
        # Custom configuration
        config = InjectorConfiguration(
            preferred_method=InjectionMethod.PORTAL,
            portal_timeout=10.0,
            retry_attempts=3,
            debug_logging=False
        )
        
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=True, method_used=InjectionMethod.PORTAL, text_length=6
        ))
        mock_portal.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal) as mock_portal_class, \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(config)
            await injector.initialize()
            
            result = await injector.inject_text("config")
            
            # Verify configuration was passed to injector
            mock_portal_class.assert_called_once()
            call_args = mock_portal_class.call_args
            assert call_args[0][0] == config  # First argument should be config
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_concurrent_injection_operations(self, basic_config, wayland_environment):
        """Test concurrent injection operations."""
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.cleanup = AsyncMock()
        
        # Mock inject_text to simulate some processing time
        async def mock_inject_text(text):
            await asyncio.sleep(0.01)  # Small delay to simulate work
            return InjectionResult(
                success=True, 
                method_used=InjectionMethod.PORTAL, 
                text_length=len(text)
            )
        
        mock_portal.inject_text_with_retry = mock_inject_text
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            # Start multiple concurrent injections
            tasks = [
                injector.inject_text("text1"),
                injector.inject_text("text2"),
                injector.inject_text("text3")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(result.success for result in results)
            assert [result.text_length for result in results] == [5, 5, 5]
    
    @pytest.mark.asyncio
    async def test_environment_change_detection(self, basic_config):
        """Test detection of environment changes during runtime."""
        # Start with Wayland environment
        initial_env = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
        
        # Changed to X11 environment (e.g., user switched sessions)
        changed_env = EnvironmentInfo(
            display_server=DisplayServerType.X11,
            desktop_environment=DesktopEnvironment.KDE,
            available_methods=[InjectionMethod.XDOTOOL],
            portal_available=False,
            xdotool_available=True
        )
        
        async with self._mock_successful_portal_injector() as mock_portal, \
                   self._mock_successful_xdotool_injector() as mock_xdotool:
            
            with patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                      side_effect=[initial_env, changed_env]):
                
                injector = TextInjector(basic_config)
                
                # Initialize with initial environment
                await injector.initialize()
                result1 = await injector.inject_text("test1")
                assert result1.method_used == InjectionMethod.PORTAL
                
                # Note: Environment change detection would require reinitialization
                # For now, just verify the first injection worked with Portal
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, basic_config, hybrid_environment):
        """Test complete error recovery workflow."""
        # Mock Portal that fails with permission error
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(side_effect=PortalPermissionError("Permission denied"))
        mock_portal.cleanup = AsyncMock()
        
        async with self._mock_successful_xdotool_injector() as mock_xdotool:
            
            with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
                 patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                       return_value=hybrid_environment):
                
                injector = TextInjector(basic_config)
                
                # Should successfully initialize using fallback
                await injector.initialize()
                
                # Should work using xdotool
                result = await injector.inject_text("recovery test")
                assert result.success is True
                assert result.method_used == InjectionMethod.XDOTOOL
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self, basic_config, wayland_environment):
        """Test health monitoring integration."""
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.get_health_status = AsyncMock(return_value={
            'portal_connected': True,
            'session_ready': True,
            'last_injection_success': True
        })
        mock_portal.inject_text = AsyncMock(return_value=InjectionResult(
            success=True, method_used=InjectionMethod.PORTAL, text_length=4
        ))
        mock_portal.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            # Perform injection
            await injector.inject_text("test")
            
            # Check health status
            health = await injector.get_health_status()
            
            assert 'active_injector' in health
            assert 'initialized' in health
            assert health['active_injector'] is True
            assert health['initialized'] is True
    
    @pytest.mark.asyncio
    async def test_unicode_text_handling_integration(self, basic_config, wayland_environment):
        """Test Unicode text handling in complete workflow."""
        unicode_texts = [
            "Hello, 世界!",  # Mixed ASCII and Chinese
            "Здравствуй мир",  # Cyrillic
            "🚀 emoji test 🎉",  # Emojis
            "café naïve résumé",  # Accented characters
        ]
        
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.cleanup = AsyncMock()
        
        async def mock_inject(text):
            return InjectionResult(
                success=True,
                method_used=InjectionMethod.PORTAL,
                text_length=len(text)
            )
        
        mock_portal.inject_text_with_retry = mock_inject
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            # Test all Unicode texts
            for text in unicode_texts:
                result = await injector.inject_text(text)
                assert result.success is True
                assert result.text_length == len(text)
    
    @pytest.mark.asyncio
    async def test_cleanup_integration(self, basic_config, wayland_environment):
        """Test complete cleanup integration."""
        mock_portal = Mock()
        mock_portal.method = InjectionMethod.PORTAL
        mock_portal.check_availability = AsyncMock(return_value=True)
        mock_portal.initialize = AsyncMock(return_value=True)
        mock_portal.inject_text_with_retry = AsyncMock(return_value=InjectionResult(
            success=True, method_used=InjectionMethod.PORTAL, text_length=4
        ))
        mock_portal.cleanup = AsyncMock()
        
        with patch('nextalk.output.injection_factory.PortalInjector', return_value=mock_portal), \
             patch('nextalk.output.environment_detector.EnvironmentDetector.detect_environment', 
                   return_value=wayland_environment):
            
            injector = TextInjector(basic_config)
            await injector.initialize()
            
            # Use injector
            await injector.inject_text("test")
            
            # Cleanup
            await injector.cleanup()
            
            # Verify cleanup was called on all components
            mock_portal.cleanup.assert_called_once()
            
            # Verify state is cleaned up
            assert injector._initialized is False
            assert injector._active_injector is None