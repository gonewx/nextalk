"""
Unit tests for IME Manager functionality.

Tests IME adapter initialization, text injection, and state management.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from nextalk.config.models import IMEConfig
from nextalk.output.ime_manager import IMEManager, IMEManagerFactory, IMEManagerState
from nextalk.output.ime_base import IMEResult, IMEStatus, IMEInfo, IMEFramework, CompositionState
from nextalk.output.ime_linux import LinuxIMEAdapter


class TestIMEConfig:
    """Test IME configuration functionality."""
    
    def test_default_config(self):
        """Test default IME configuration."""
        config = IMEConfig()
        
        assert config.enabled is True
        assert config.preferred_framework is None
        assert config.fallback_timeout == 5.0
        assert config.composition_timeout == 1.0
        assert config.state_monitor_interval == 0.1
        assert config.auto_detect_ime is True
        assert config.linux_ime_frameworks == ['ibus', 'fcitx']
        assert config.dbus_timeout == 2.0
        assert config.debug_mode is False
    
    def test_custom_config(self):
        """Test custom IME configuration."""
        config = IMEConfig(
            enabled=False,
            preferred_framework='ibus',
            debug_mode=True,
            dbus_timeout=5.0
        )
        
        assert config.enabled is False
        assert config.preferred_framework == 'ibus'
        assert config.debug_mode is True
        assert config.dbus_timeout == 5.0


class TestIMEManagerFactory:
    """Test IME Manager factory functionality."""
    
    def test_create_manager(self):
        """Test creating IME manager."""
        config = IMEConfig()
        manager = IMEManagerFactory.create_manager(config)
        
        assert isinstance(manager, IMEManager)
        assert manager.config == config
        assert not manager.is_initialized
    
    def test_create_state_monitor_linux(self):
        """Test creating state monitor for Linux."""
        config = IMEConfig()
        
        with patch('platform.system', return_value='Linux'):
            monitor = IMEManagerFactory.create_state_monitor(config)
            
            # Import should work without error
            from nextalk.output.ime_linux import LinuxIMEStateMonitor
            assert monitor is not None
    
    def test_create_state_monitor_unsupported_platform(self):
        """Test creating state monitor for unsupported platform."""
        config = IMEConfig()
        
        with patch('platform.system', return_value='Windows'):
            monitor = IMEManagerFactory.create_state_monitor(config)
            assert monitor is None


class TestIMEManager:
    """Test IME Manager core functionality."""
    
    @pytest.fixture
    def ime_config(self):
        """Create test IME configuration."""
        return IMEConfig(debug_mode=True, dbus_timeout=1.0)
    
    @pytest.fixture
    def ime_manager(self, ime_config):
        """Create test IME manager."""
        return IMEManager(ime_config)
    
    def test_initialization(self, ime_manager, ime_config):
        """Test IME manager initialization."""
        assert ime_manager.config == ime_config
        assert ime_manager._state == IMEManagerState.UNINITIALIZED
        assert ime_manager._adapter is None
        assert not ime_manager.is_initialized
        assert not ime_manager.is_ready
    
    def test_disabled_manager(self):
        """Test disabled IME manager."""
        config = IMEConfig(enabled=False)
        manager = IMEManager(config)
        
        assert manager.config.enabled is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, ime_manager):
        """Test successful IME manager initialization."""
        # Mock the adapter creation and initialization
        mock_adapter = AsyncMock()
        mock_adapter.initialize.return_value = True
        
        with patch.object(ime_manager, '_select_adapter_class') as mock_select:
            mock_adapter_class = Mock(return_value=mock_adapter)
            mock_select.return_value = mock_adapter_class
            
            result = await ime_manager.initialize()
            
            assert result is True
            assert ime_manager._state == IMEManagerState.READY
            assert ime_manager.is_initialized
            assert ime_manager.is_ready
            mock_adapter.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self):
        """Test initialization of disabled IME manager."""
        config = IMEConfig(enabled=False)
        manager = IMEManager(config)
        
        result = await manager.initialize()
        
        assert result is True
        assert manager._state == IMEManagerState.DISABLED
        assert manager.is_initialized
        assert not manager.is_ready
        assert manager.is_disabled
    
    @pytest.mark.asyncio
    async def test_initialize_adapter_failure(self, ime_manager):
        """Test IME manager initialization with adapter failure."""
        mock_adapter = AsyncMock()
        mock_adapter.initialize.return_value = False
        
        with patch.object(ime_manager, '_select_adapter_class') as mock_select:
            mock_adapter_class = Mock(return_value=mock_adapter)
            mock_select.return_value = mock_adapter_class
            
            result = await ime_manager.initialize()
            
            assert result is False
            assert ime_manager._state == IMEManagerState.ERROR
            assert not ime_manager.is_ready
    
    @pytest.mark.asyncio
    async def test_initialize_no_adapter_available(self, ime_manager):
        """Test initialization when no adapter is available."""
        with patch.object(ime_manager, '_select_adapter_class', return_value=None):
            result = await ime_manager.initialize()
            
            assert result is False
            assert ime_manager._state == IMEManagerState.ERROR
    
    @pytest.mark.asyncio
    async def test_cleanup(self, ime_manager):
        """Test IME manager cleanup."""
        # Setup initialized manager
        mock_adapter = AsyncMock()
        ime_manager._adapter = mock_adapter
        ime_manager._state = IMEManagerState.READY
        
        await ime_manager.cleanup()
        
        mock_adapter.cleanup.assert_called_once()
        assert ime_manager._adapter is None
        assert ime_manager._state == IMEManagerState.UNINITIALIZED
    
    @pytest.mark.asyncio
    async def test_inject_text_success(self, ime_manager):
        """Test successful text injection."""
        # Setup initialized manager with mock adapter
        mock_adapter = AsyncMock()
        mock_ime_info = IMEInfo(
            name='test-ime',
            framework=IMEFramework.IBUS,
            language='zh',
            is_active=True
        )
        mock_adapter.detect_active_ime.return_value = mock_ime_info
        mock_adapter.inject_text.return_value = IMEResult(
            success=True,
            text_injected='测试文本',
            ime_used='ibus',
            injection_time=0.1
        )
        
        ime_manager._adapter = mock_adapter
        ime_manager._state = IMEManagerState.READY
        
        result = await ime_manager.inject_text('测试文本')
        
        assert result.success is True
        assert result.text_injected == '测试文本'
        assert result.ime_used == 'ibus'
        assert ime_manager._injection_count == 1
        assert ime_manager._success_count == 1
        
        mock_adapter.detect_active_ime.assert_called_once()
        mock_adapter.inject_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_inject_text_not_ready(self, ime_manager):
        """Test text injection when manager is not ready."""
        result = await ime_manager.inject_text('test')
        
        assert result.success is False
        assert 'not ready' in result.error
    
    @pytest.mark.asyncio
    async def test_inject_text_disabled(self):
        """Test text injection when manager is disabled."""
        config = IMEConfig(enabled=False)
        manager = IMEManager(config)
        await manager.initialize()  # This should set state to DISABLED
        
        result = await manager.inject_text('test')
        
        assert result.success is False
        assert result.ime_used == 'disabled'
    
    @pytest.mark.asyncio
    async def test_get_ime_status(self, ime_manager):
        """Test getting IME status."""
        # Setup mock adapter
        mock_adapter = AsyncMock()
        mock_status = IMEStatus(
            is_active=True,
            current_ime='ibus',
            composition_state=CompositionState.INACTIVE,
            input_language='zh',
            focus_app='test-app'
        )
        mock_adapter.get_ime_status.return_value = mock_status
        
        ime_manager._adapter = mock_adapter
        ime_manager._state = IMEManagerState.READY
        
        status = await ime_manager.get_ime_status()
        
        assert status.is_active is True
        assert status.current_ime == 'ibus'
        assert status.focus_app == 'test-app'
    
    @pytest.mark.asyncio
    async def test_detect_active_ime(self, ime_manager):
        """Test detecting active IME."""
        # Setup mock adapter
        mock_adapter = AsyncMock()
        mock_ime_info = IMEInfo(
            name='test-ime',
            framework=IMEFramework.IBUS,
            language='zh',
            is_active=True
        )
        mock_adapter.detect_active_ime.return_value = mock_ime_info
        
        ime_manager._adapter = mock_adapter
        ime_manager._state = IMEManagerState.READY
        
        ime_info = await ime_manager.detect_active_ime()
        
        assert ime_info is not None
        assert ime_info.name == 'test-ime'
        assert ime_info.framework == IMEFramework.IBUS
    
    @pytest.mark.asyncio
    async def test_is_ime_ready(self, ime_manager):
        """Test checking if IME is ready."""
        # Setup mock adapter
        mock_adapter = AsyncMock()
        mock_adapter.is_ime_ready.return_value = True
        
        ime_manager._adapter = mock_adapter
        ime_manager._state = IMEManagerState.READY
        
        is_ready = await ime_manager.is_ime_ready()
        assert is_ready is True
        
        # Test when not ready
        ime_manager._state = IMEManagerState.ERROR
        is_ready = await ime_manager.is_ime_ready()
        assert is_ready is False
    
    def test_get_manager_status(self, ime_manager):
        """Test getting manager status."""
        status = ime_manager.get_manager_status()
        
        assert status.state == IMEManagerState.UNINITIALIZED
        assert status.platform == 'linux'  # Assuming Linux platform
        assert status.adapter_type is None
        assert status.ime_ready is False
    
    def test_get_statistics(self, ime_manager):
        """Test getting injection statistics."""
        # Simulate some injections
        ime_manager._injection_count = 10
        ime_manager._success_count = 8
        ime_manager._initialization_time = 1.5
        
        stats = ime_manager.get_statistics()
        
        assert stats['total_injections'] == 10
        assert stats['successful_injections'] == 8
        assert stats['failed_injections'] == 2
        assert stats['success_rate'] == 80.0
        assert stats['initialization_time'] == 1.5
    
    def test_select_adapter_class_linux(self, ime_manager):
        """Test adapter class selection for Linux."""
        with patch('platform.system', return_value='Linux'):
            adapter_class = ime_manager._select_adapter_class()
            assert adapter_class == LinuxIMEAdapter
    
    def test_select_adapter_class_unsupported(self, ime_manager):
        """Test adapter class selection for unsupported platform."""
        with patch('platform.system', return_value='Windows'):
            adapter_class = ime_manager._select_adapter_class()
            assert adapter_class is None
    
    def test_create_adapter_config(self, ime_manager):
        """Test creating adapter configuration."""
        config = ime_manager._create_adapter_config()
        
        assert config['enabled'] is True
        assert config['dbus_timeout'] == 1.0  # From fixture
        assert 'linux_ime_frameworks' in config


@pytest.mark.asyncio
class TestIMEManagerIntegration:
    """Integration tests for IME Manager with real adapters."""
    
    @pytest.fixture
    def real_ime_config(self):
        """Create real IME configuration for integration tests."""
        return IMEConfig(
            enabled=True,
            debug_mode=True,
            dbus_timeout=1.0,
            fallback_timeout=2.0
        )
    
    async def test_linux_ime_integration(self, real_ime_config):
        """Test IME manager integration with Linux adapter."""
        manager = IMEManager(real_ime_config)
        
        # Mock the Linux adapter to avoid actual system calls
        with patch('nextalk.output.ime_linux.LinuxIMEAdapter') as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter.initialize.return_value = True
            mock_adapter_class.return_value = mock_adapter
            
            # Test initialization
            result = await manager.initialize()
            assert result is True
            assert manager.is_ready
            
            # Test cleanup
            await manager.cleanup()
            mock_adapter.cleanup.assert_called_once()
    
    async def test_error_handling_during_injection(self, real_ime_config):
        """Test error handling during text injection."""
        manager = IMEManager(real_ime_config)
        
        # Mock adapter that raises exception during injection
        with patch('nextalk.output.ime_linux.LinuxIMEAdapter') as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter.initialize.return_value = True
            mock_adapter.inject_text.side_effect = Exception("Mock injection error")
            mock_adapter_class.return_value = mock_adapter
            
            await manager.initialize()
            
            result = await manager.inject_text("test text")
            
            assert result.success is False
            assert "Mock injection error" in result.error
            assert manager._error_count == 1