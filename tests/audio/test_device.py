"""
Unit tests for audio device management.

Tests AudioDevice and AudioDeviceManager functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

from nextalk.audio.device import (
    AudioDevice, 
    AudioDeviceManager, 
    AudioDeviceError
)
from nextalk.config.models import AudioConfig


class TestAudioDevice:
    """Test AudioDevice data class."""
    
    def test_audio_device_creation(self):
        """Test AudioDevice creation with valid parameters."""
        device = AudioDevice(
            device_id=0,
            device_name="Test Microphone",
            channels=2,
            default_sample_rate=44100.0,
            max_input_channels=2,
            max_output_channels=0,
            is_default=True,
            is_available=True
        )
        
        assert device.device_id == 0
        assert device.device_name == "Test Microphone"
        assert device.channels == 2
        assert device.default_sample_rate == 44100.0
        assert device.is_default is True
        assert device.is_available is True
    
    def test_audio_device_str_representation(self):
        """Test string representation of AudioDevice."""
        device = AudioDevice(
            device_id=1,
            device_name="USB Microphone",
            channels=1,
            default_sample_rate=16000.0,
            max_input_channels=1,
            max_output_channels=0,
            is_default=False,
            is_available=True
        )
        
        str_repr = str(device)
        assert "[1]" in str_repr
        assert "USB Microphone" in str_repr
        assert "✓" in str_repr  # Available marker
        assert "1通道" in str_repr
        assert "16000.0Hz" in str_repr
    
    def test_audio_device_unavailable_representation(self):
        """Test string representation of unavailable device."""
        device = AudioDevice(
            device_id=2,
            device_name="Broken Mic",
            channels=1,
            default_sample_rate=44100.0,
            max_input_channels=1,
            max_output_channels=0,
            is_default=False,
            is_available=False
        )
        
        str_repr = str(device)
        assert "✗" in str_repr  # Unavailable marker


class TestAudioDeviceManager:
    """Test AudioDeviceManager functionality."""
    
    @pytest.fixture
    def mock_sounddevice(self):
        """Mock sounddevice module."""
        with patch('nextalk.audio.device.sd') as mock_sd:
            # Mock device query results
            mock_sd.query_devices.return_value = [
                {
                    'name': 'Default Microphone',
                    'max_input_channels': 2,
                    'max_output_channels': 0,
                    'default_samplerate': 44100.0
                },
                {
                    'name': 'USB Microphone', 
                    'max_input_channels': 1,
                    'max_output_channels': 0,
                    'default_samplerate': 16000.0
                },
                {
                    'name': 'Speakers',  # Output only device
                    'max_input_channels': 0,
                    'max_output_channels': 2,
                    'default_samplerate': 44100.0
                }
            ]
            mock_sd.default.device = [0, None]  # Default input device ID 0
            yield mock_sd
    
    @pytest.fixture
    def device_manager(self, mock_sounddevice):
        """Create AudioDeviceManager instance with mocked sounddevice."""
        with patch.object(AudioDeviceManager, '_test_device_availability', return_value=True):
            return AudioDeviceManager()
    
    def test_device_manager_initialization(self, device_manager):
        """Test AudioDeviceManager initialization."""
        devices = device_manager.get_devices()
        
        # Should find 2 input devices (excluding output-only device)
        assert len(devices) == 2
        
        # Check first device (default)
        default_device = devices[0]
        assert default_device.device_name == 'Default Microphone'
        assert default_device.is_default is True
        assert default_device.max_input_channels == 2
        
        # Check second device
        usb_device = devices[1]
        assert usb_device.device_name == 'USB Microphone'
        assert usb_device.is_default is False
        assert usb_device.max_input_channels == 1
    
    def test_get_available_devices(self, device_manager):
        """Test getting only available devices."""
        available = device_manager.get_available_devices()
        
        # All mocked devices are available
        assert len(available) == 2
        for device in available:
            assert device.is_available is True
    
    def test_get_default_device(self, device_manager):
        """Test getting default audio device."""
        default = device_manager.get_default_device()
        
        assert default is not None
        assert default.device_name == 'Default Microphone'
        assert default.is_default is True
    
    def test_get_device_by_id(self, device_manager):
        """Test finding device by ID."""
        device = device_manager.get_device_by_id(1)
        
        assert device is not None
        assert device.device_id == 1
        assert device.device_name == 'USB Microphone'
        
        # Test non-existent ID
        assert device_manager.get_device_by_id(999) is None
    
    def test_get_device_by_name(self, device_manager):
        """Test finding device by name."""
        # Exact name match
        device = device_manager.get_device_by_name('USB Microphone')
        assert device is not None
        assert device.device_name == 'USB Microphone'
        
        # Partial name match (case insensitive)
        device = device_manager.get_device_by_name('usb')
        assert device is not None
        assert device.device_name == 'USB Microphone'
        
        # Non-existent name
        assert device_manager.get_device_by_name('NonExistent') is None
    
    def test_select_best_device_by_id(self, device_manager):
        """Test device selection by ID preference."""
        config = AudioConfig(
            device_id=1,
            sample_rate=16000,
            channels=1
        )
        
        device = device_manager.select_best_device(config)
        assert device.device_id == 1
        assert device.device_name == 'USB Microphone'
    
    def test_select_best_device_by_name(self, device_manager):
        """Test device selection by name preference."""
        config = AudioConfig(
            device_name='USB Microphone',
            sample_rate=16000,
            channels=1
        )
        
        device = device_manager.select_best_device(config)
        assert device.device_name == 'USB Microphone'
    
    def test_select_best_device_fallback_to_default(self, device_manager):
        """Test device selection fallback to default."""
        config = AudioConfig(
            device_id=999,  # Non-existent ID
            device_name='NonExistent',  # Non-existent name
            sample_rate=16000,
            channels=1
        )
        
        device = device_manager.select_best_device(config)
        assert device.is_default is True
        assert device.device_name == 'Default Microphone'
    
    def test_select_best_device_no_devices_error(self, mock_sounddevice):
        """Test error when no devices available."""
        # Mock no input devices
        mock_sounddevice.query_devices.return_value = []
        
        with patch.object(AudioDeviceManager, '_test_device_availability', return_value=False):
            device_manager = AudioDeviceManager()
            config = AudioConfig()
            
            with pytest.raises(AudioDeviceError, match="No available audio input devices"):
                device_manager.select_best_device(config)
    
    def test_validate_device_config_channel_mismatch(self, device_manager):
        """Test device validation with channel mismatch."""
        device = device_manager.get_device_by_id(1)  # USB mic with 1 channel
        config = AudioConfig(channels=2)  # Requesting 2 channels
        
        issues = device_manager.validate_device_config(device, config)
        assert len(issues) >= 1
        assert "channels" in issues[0]
    
    @patch('nextalk.audio.device.sd.InputStream')
    def test_validate_device_config_sample_rate(self, mock_stream, device_manager):
        """Test device validation with sample rate issues."""
        device = device_manager.get_device_by_id(0)
        config = AudioConfig(sample_rate=192000)  # Very high sample rate
        
        # Mock sample rate test failure
        mock_stream.side_effect = Exception("Sample rate not supported")
        
        issues = device_manager.validate_device_config(device, config)
        assert len(issues) >= 1
        assert "Sample rate" in issues[0]
    
    def test_get_device_info_summary(self, device_manager):
        """Test device information summary."""
        summary = device_manager.get_device_info_summary()
        
        assert summary['total_devices'] == 2
        assert summary['available_devices'] == 2
        assert summary['default_device'] == 'Default Microphone'
        assert len(summary['devices']) == 2
        
        # Check device details
        device_info = summary['devices'][0]
        assert 'id' in device_info
        assert 'name' in device_info
        assert 'channels' in device_info
        assert 'available' in device_info
    
    def test_refresh_devices(self, mock_sounddevice):
        """Test device list refresh."""
        device_manager = AudioDeviceManager()
        
        # Change mock to return different devices
        mock_sounddevice.query_devices.return_value = [
            {
                'name': 'New Microphone',
                'max_input_channels': 1,
                'max_output_channels': 0,
                'default_samplerate': 48000.0
            }
        ]
        
        with patch.object(device_manager, '_test_device_availability', return_value=True):
            devices = device_manager.get_devices(refresh=True)
        
        assert len(devices) == 1
        assert devices[0].device_name == 'New Microphone'
    
    def test_device_availability_test_failure(self, mock_sounddevice):
        """Test handling of device availability test failures."""
        with patch('nextalk.audio.device.sd.InputStream') as mock_stream:
            mock_stream.side_effect = Exception("Device busy")
            
            device_manager = AudioDeviceManager()
            devices = device_manager.get_devices()
            
            # Devices should be marked as unavailable
            for device in devices:
                assert device.is_available is False
    
    def test_print_device_list(self, device_manager, capsys):
        """Test device list printing."""
        device_manager.print_device_list()
        
        captured = capsys.readouterr()
        assert "可用的音频输入设备" in captured.out
        assert "Default Microphone" in captured.out
        assert "USB Microphone" in captured.out
    
    def test_sounddevice_error_handling(self, mock_sounddevice):
        """Test error handling when sounddevice fails."""
        mock_sounddevice.query_devices.side_effect = Exception("Audio system error")
        
        with pytest.raises(AudioDeviceError, match="Failed to enumerate audio devices"):
            AudioDeviceManager()


# Integration-style tests
class TestAudioDeviceIntegration:
    """Integration tests for audio device functionality."""
    
    @pytest.fixture
    def audio_config(self):
        """Create test audio configuration."""
        return AudioConfig(
            sample_rate=16000,
            channels=1,
            device_id=None,
            device_name=None
        )
    
    @patch('nextalk.audio.device.sd')
    def test_full_device_selection_workflow(self, mock_sd, audio_config):
        """Test complete device selection workflow."""
        # Mock realistic device scenario
        mock_sd.query_devices.return_value = [
            {
                'name': 'Built-in Microphone',
                'max_input_channels': 1,
                'max_output_channels': 0,
                'default_samplerate': 44100.0
            },
            {
                'name': 'Blue Yeti USB Microphone',
                'max_input_channels': 2,
                'max_output_channels': 0,
                'default_samplerate': 48000.0
            }
        ]
        mock_sd.default.device = [1, None]  # Blue Yeti is default
        
        with patch.object(AudioDeviceManager, '_test_device_availability', return_value=True):
            device_manager = AudioDeviceManager()
        
        # Test device selection
        selected_device = device_manager.select_best_device(audio_config)
        
        # Should select default device (Blue Yeti)
        assert selected_device.device_name == 'Blue Yeti USB Microphone'
        assert selected_device.is_default is True
        
        # Validate configuration
        issues = device_manager.validate_device_config(selected_device, audio_config)
        # Should have no issues for this configuration
        assert len(issues) == 0 or all('Sample rate' not in issue for issue in issues)