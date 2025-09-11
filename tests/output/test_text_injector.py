"""
Unit tests for modern TextInjector implementation.

Tests the TextInjector class that uses InjectionStrategyFactory.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from nextalk.output.text_injector import TextInjector
from nextalk.output.injection_models import InjectorConfiguration, InjectionMethod, InjectionResult
from nextalk.output.injection_exceptions import InjectionFailedError


class TestTextInjector:
    """Test cases for modern TextInjector."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return InjectorConfiguration(
            preferred_method=InjectionMethod.AUTO,
            retry_attempts=2,
            debug_logging=True
        )
    
    @pytest.fixture
    def injector(self, config):
        """Create TextInjector instance."""
        return TextInjector(config)
    
    def test_initialization(self, injector, config):
        """Test injector initialization."""
        assert injector._injector_config == config
        assert injector._factory is None  # Only created in initialize()
        assert injector._active_injector is None
        assert not injector._initialized
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, injector):
        """Test successful initialization."""
        # Mock the factory's create_injector method
        mock_result = Mock()
        mock_result.injector = AsyncMock()
        mock_result.method = InjectionMethod.PORTAL
        
        with patch('nextalk.output.text_injector.InjectionStrategyFactory') as mock_factory_class:
            mock_factory = AsyncMock()
            mock_factory.create_injector.return_value = mock_result
            mock_factory_class.return_value = mock_factory
            
            success = await injector.initialize()
            
            assert success is True
            assert injector._initialized is True
            assert injector._active_injector == mock_result.injector
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, injector):
        """Test initialization failure."""
        with patch('nextalk.output.text_injector.InjectionStrategyFactory') as mock_factory_class:
            mock_factory = AsyncMock()
            mock_factory.create_injector.side_effect = Exception("Factory error")
            mock_factory_class.return_value = mock_factory
            
            success = await injector.initialize()
            
            assert success is False
            assert injector._initialized is False
            assert injector._active_injector is None
    
    @pytest.mark.asyncio
    async def test_inject_text_success(self, injector):
        """Test successful text injection."""
        # Set up initialized state with mock injector
        mock_injector = AsyncMock()
        mock_result = InjectionResult(
            success=True,
            method_used=InjectionMethod.PORTAL,
            text_length=5,
            error_message=None
        )
        mock_injector.inject_text_with_retry.return_value = mock_result
        
        injector._initialized = True
        injector._active_injector = mock_injector
        
        result = await injector.inject_text("hello")
        
        assert result.success is True
        assert result.text_length == 5
        mock_injector.inject_text_with_retry.assert_called_once_with("hello")
    
    @pytest.mark.asyncio
    async def test_inject_text_empty(self, injector):
        """Test injection with empty text."""
        # Set up initialized state
        injector._initialized = True
        injector._active_injector = AsyncMock()
        
        result = await injector.inject_text("")
        
        assert result.success is True
        assert result.text_length == 0
        assert "Empty text" in result.error_message
        # Injector should not be called for empty text
        injector._active_injector.inject_text_with_retry.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_inject_text_not_initialized(self, injector):
        """Test injection fails when not initialized."""
        result = await injector.inject_text("test")
        
        assert result.success is False
        assert "not initialized" in result.error_message
    
    @pytest.mark.asyncio
    async def test_inject_text_with_fallback(self, injector):
        """Test injection handles error and returns failure result."""
        # Set up initialized state
        mock_injector = AsyncMock()
        mock_injector.inject_text_with_retry.side_effect = InjectionFailedError("Injection failed")
        
        injector._initialized = True
        injector._active_injector = mock_injector
        
        result = await injector.inject_text("test")
        
        # TextInjector should handle the exception and return failure result
        assert result.success is False
        assert "Injection failed" in result.error_message
        mock_injector.inject_text_with_retry.assert_called_once_with("test")
    
    @pytest.mark.asyncio
    async def test_cleanup(self, injector):
        """Test cleanup."""
        # Set up some state to clean up
        mock_injector = AsyncMock()
        injector._active_injector = mock_injector
        injector._initialized = True
        
        await injector.cleanup()
        
        mock_injector.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_switch_method(self, injector):
        """Test switching injection method."""
        # First initialize the injector so _factory exists
        with patch('nextalk.output.text_injector.InjectionStrategyFactory') as mock_factory_class:
            # Set up mock factory instance
            mock_factory = AsyncMock()
            mock_factory_class.return_value = mock_factory
            
            # Mock initial injector for initialization
            init_result = Mock()
            init_result.injector = AsyncMock()
            init_result.method = InjectionMethod.PORTAL
            
            # Mock switch injector  
            switch_injector = AsyncMock()
            switch_injector.cleanup = AsyncMock()
            
            # Mock for initialization
            mock_factory.create_injector.return_value = init_result
            mock_factory.create_specific_injector.return_value = switch_injector
            
            await injector.initialize()  # This creates the _factory
            
            success = await injector.switch_method(InjectionMethod.XDOTOOL)
            
            assert success is True
            assert injector._active_injector == switch_injector
            # create_injector called once for init, create_specific_injector called once for switch
            assert mock_factory.create_injector.call_count == 1
            mock_factory.create_specific_injector.assert_called_once_with(InjectionMethod.XDOTOOL)
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, injector):
        """Test health status reporting."""
        # Set up initialized state
        mock_injector = AsyncMock()
        mock_injector.get_health_status.return_value = {"injector_status": "healthy"}
        
        injector._initialized = True
        injector._active_injector = mock_injector
        injector._injection_count = 10
        injector._success_count = 8
        
        status = await injector.get_health_status()
        
        assert "initialized" in status
        assert status["initialized"] is True
        assert "active_injector" in status 
        assert status["active_injector"] is True
        assert "status" in status
        assert status["status"] == "healthy"
        assert "total_injections" in status
        assert status["total_injections"] == 10
        assert "success_rate" in status
        assert status["success_rate"] == 80.0
        
        mock_injector.get_health_status.assert_called_once()
    
    def test_inject_text_sync_deprecated(self, injector):
        """Test deprecated synchronous injection method."""
        # Mock inject_text to return successful result
        from nextalk.output.injection_models import InjectionResult, InjectionMethod
        mock_result = InjectionResult(
            success=True, 
            method_used=InjectionMethod.PORTAL,
            text_length=4
        )
        
        with patch.object(injector, 'inject_text', new_callable=AsyncMock, return_value=mock_result):
            result = injector.inject_text_sync("test")
            
            # inject_text_sync now returns boolean based on result.success
            assert result is True