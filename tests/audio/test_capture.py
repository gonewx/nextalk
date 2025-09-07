"""
Unit tests for audio capture functionality.

Tests AudioCaptureManager and related audio processing functionality.
"""

import pytest
import numpy as np
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from typing import List, Optional

from nextalk.audio.capture import (
    AudioCaptureManager,
    AudioData,
    CaptureState,
    AudioCaptureError
)
from nextalk.audio.device import AudioDevice, AudioDeviceManager
from nextalk.config.models import AudioConfig


class TestAudioData:
    """Test AudioData container class."""
    
    def test_audio_data_creation(self):
        """Test AudioData creation with valid parameters."""
        data = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        audio_data = AudioData(
            data=data,
            sample_rate=16000,
            channels=2,
            timestamp=1234567890.0,
            duration=1.5
        )
        
        assert np.array_equal(audio_data.data, data)
        assert audio_data.sample_rate == 16000
        assert audio_data.channels == 2
        assert audio_data.timestamp == 1234567890.0
        assert audio_data.duration == 1.5
    
    def test_audio_data_to_bytes_float32(self):
        """Test conversion from float32 to bytes."""
        # Create test data in [-1, 1] range
        data = np.array([[-1.0, 0.0], [0.5, 1.0]], dtype=np.float32)
        audio_data = AudioData(
            data=data,
            sample_rate=16000,
            channels=2,
            timestamp=0,
            duration=0
        )
        
        bytes_data = audio_data.to_bytes()
        
        # Convert back to int16 to verify
        int16_data = np.frombuffer(bytes_data, dtype=np.int16).reshape(-1, 2)
        
        # Check expected values (float to int16 conversion)
        assert int16_data[0, 0] == -32767  # -1.0 -> -32767
        assert int16_data[0, 1] == 0       # 0.0 -> 0
        assert int16_data[1, 0] == 16383   # 0.5 -> ~16383
        assert int16_data[1, 1] == 32767   # 1.0 -> 32767
    
    def test_audio_data_to_bytes_int16(self):
        """Test conversion when data is already int16."""
        data = np.array([[1000, -1000], [2000, -2000]], dtype=np.int16)
        audio_data = AudioData(
            data=data,
            sample_rate=16000,
            channels=2,
            timestamp=0,
            duration=0
        )
        
        bytes_data = audio_data.to_bytes()
        
        # Should be direct conversion to bytes
        int16_data = np.frombuffer(bytes_data, dtype=np.int16).reshape(-1, 2)
        assert np.array_equal(int16_data, data)
    
    def test_audio_data_size_bytes(self):
        """Test size calculation in bytes."""
        data = np.array([[1, 2], [3, 4]], dtype=np.int16)  # 4 int16 values = 8 bytes
        audio_data = AudioData(
            data=data,
            sample_rate=16000,
            channels=2,
            timestamp=0,
            duration=0
        )
        
        assert audio_data.size_bytes == 8


class TestAudioCaptureManager:
    """Test AudioCaptureManager functionality."""
    
    @pytest.fixture
    def audio_config(self):
        """Create test audio configuration."""
        return AudioConfig(
            sample_rate=16000,
            channels=1,
            input_buffer_size=1024,
            noise_suppression=True,
            auto_gain_control=True
        )
    
    @pytest.fixture
    def mock_device(self):
        """Create mock audio device."""
        return AudioDevice(
            device_id=0,
            device_name="Test Microphone",
            channels=1,
            default_sample_rate=16000.0,
            max_input_channels=1,
            max_output_channels=0,
            is_default=True,
            is_available=True
        )
    
    @pytest.fixture
    def mock_device_manager(self, mock_device):
        """Create mock AudioDeviceManager."""
        device_manager = Mock(spec=AudioDeviceManager)
        device_manager.select_best_device.return_value = mock_device
        device_manager.validate_device_config.return_value = []
        return device_manager
    
    @pytest.fixture
    def capture_manager(self, audio_config, mock_device_manager):
        """Create AudioCaptureManager with mocked dependencies."""
        with patch('nextalk.audio.capture.AudioDeviceManager') as MockDeviceManager:
            MockDeviceManager.return_value = mock_device_manager
            return AudioCaptureManager(audio_config)
    
    def test_capture_manager_initialization(self, capture_manager, audio_config):
        """Test AudioCaptureManager initialization."""
        assert capture_manager.config == audio_config
        assert capture_manager.get_state() == CaptureState.IDLE
        assert capture_manager._current_device is not None
        assert capture_manager._current_device.device_name == "Test Microphone"
    
    def test_set_data_callback(self, capture_manager):
        """Test setting audio data callback."""
        callback = Mock()
        capture_manager.set_data_callback(callback)
        
        assert capture_manager._data_callback == callback
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_start_recording_success(self, mock_stream_class, capture_manager):
        """Test successful recording start."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Start recording
        capture_manager.start_recording()
        
        # Verify state and stream creation
        assert capture_manager.get_state() == CaptureState.RECORDING
        assert capture_manager.is_recording() is True
        
        # Verify stream was configured correctly
        mock_stream_class.assert_called_once()
        call_args = mock_stream_class.call_args
        assert call_args[1]['device'] == 0
        assert call_args[1]['channels'] == 1
        assert call_args[1]['samplerate'] == 16000
        assert call_args[1]['blocksize'] == 1024
        
        # Verify stream was started
        mock_stream.start.assert_called_once()
    
    def test_start_recording_wrong_state_error(self, capture_manager):
        """Test error when starting recording in wrong state."""
        # Manually set state to RECORDING
        capture_manager._state = CaptureState.RECORDING
        
        with pytest.raises(AudioCaptureError, match="Cannot start recording in state"):
            capture_manager.start_recording()
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_start_recording_stream_error(self, mock_stream_class, capture_manager):
        """Test error handling during stream creation."""
        mock_stream_class.side_effect = Exception("Stream creation failed")
        
        with pytest.raises(AudioCaptureError, match="Failed to start recording"):
            capture_manager.start_recording()
        
        # State should be ERROR
        assert capture_manager.get_state() == CaptureState.ERROR
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_stop_recording_success(self, mock_stream_class, capture_manager):
        """Test successful recording stop."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Start then stop recording
        capture_manager.start_recording()
        capture_manager.stop_recording()
        
        # Verify stream was stopped and closed
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
        
        # Verify state
        assert capture_manager.get_state() == CaptureState.IDLE
        assert capture_manager.is_recording() is False
    
    def test_stop_recording_wrong_state(self, capture_manager):
        """Test stop recording when not recording."""
        # Should not raise error, just log warning
        capture_manager.stop_recording()
        assert capture_manager.get_state() == CaptureState.IDLE
    
    def test_audio_callback_recording_state(self, capture_manager):
        """Test audio callback processing in recording state."""
        # Set up callback
        data_callback = Mock()
        capture_manager.set_data_callback(data_callback)
        capture_manager._state = CaptureState.RECORDING
        
        # Create test audio data
        test_data = np.array([[0.1], [0.2], [0.3]], dtype=np.float32)
        
        # Call audio callback
        capture_manager._audio_callback(test_data, 3, None, Mock())
        
        # Verify data was added to buffer
        with capture_manager._buffer_lock:
            assert len(capture_manager._audio_buffer) == 1
            assert np.array_equal(capture_manager._audio_buffer[0], test_data)
        
        assert capture_manager._total_frames == 3
    
    def test_audio_callback_not_recording(self, capture_manager):
        """Test audio callback when not recording."""
        data_callback = Mock()
        capture_manager.set_data_callback(data_callback)
        capture_manager._state = CaptureState.IDLE
        
        test_data = np.array([[0.1], [0.2]], dtype=np.float32)
        
        # Call audio callback - should do nothing
        capture_manager._audio_callback(test_data, 2, None, Mock())
        
        # Buffer should remain empty
        with capture_manager._buffer_lock:
            assert len(capture_manager._audio_buffer) == 0
        assert capture_manager._total_frames == 0
    
    def test_audio_processing_noise_suppression(self, capture_manager):
        """Test audio processing with noise suppression."""
        # Test data with both noise and signal
        test_data = np.array([
            [0.005],   # Below threshold (noise)
            [0.5],     # Above threshold (signal)
            [-0.005],  # Below threshold (noise)
            [0.3]      # Above threshold (signal)
        ], dtype=np.float32)
        
        processed = capture_manager._process_audio(test_data)
        
        # Noise should be suppressed (values below 0.01)
        assert processed[0, 0] == 0.0  # Noise suppressed
        assert processed[1, 0] == 0.5  # Signal preserved
        assert processed[2, 0] == 0.0  # Noise suppressed
        assert processed[3, 0] == 0.3  # Signal preserved
    
    def test_audio_processing_auto_gain_control(self, capture_manager):
        """Test audio processing with auto gain control."""
        # Test data with high amplitude that needs gain reduction
        test_data = np.array([[1.5], [-1.2]], dtype=np.float32)  # Above target
        
        processed = capture_manager._process_audio(test_data)
        
        # Should be scaled down to prevent clipping
        max_amplitude = np.max(np.abs(processed))
        assert max_amplitude <= 0.7  # Target amplitude
        
        # Proportions should be maintained
        ratio = processed[0, 0] / processed[1, 0]
        expected_ratio = test_data[0, 0] / test_data[1, 0]
        assert abs(ratio - expected_ratio) < 0.01
    
    @patch('nextalk.audio.capture.time.sleep')  # Speed up the test
    def test_process_buffer_with_callback(self, mock_sleep, capture_manager):
        """Test buffer processing with data callback."""
        data_callback = Mock()
        capture_manager.set_data_callback(data_callback)
        capture_manager._state = CaptureState.RECORDING
        
        # Add test data to buffer
        test_data1 = np.array([[0.1], [0.2]], dtype=np.float32)
        test_data2 = np.array([[0.3], [0.4]], dtype=np.float32)
        
        with capture_manager._buffer_lock:
            capture_manager._audio_buffer = [test_data1, test_data2]
        
        # Process buffer once
        capture_manager._process_buffer()
        
        # Should have called callback with combined data
        assert data_callback.call_count >= 1
        
        # Verify callback was called with AudioData
        call_args = data_callback.call_args[0]
        audio_data = call_args[0]
        assert isinstance(audio_data, AudioData)
        assert audio_data.sample_rate == 16000
        assert audio_data.channels == 1
        
        # Buffer should be cleared
        with capture_manager._buffer_lock:
            assert len(capture_manager._audio_buffer) == 0
    
    def test_get_recording_stats(self, capture_manager):
        """Test recording statistics."""
        stats = capture_manager.get_recording_stats()
        
        # Initial state
        assert stats['state'] == 'idle'
        assert stats['device'] == 'Test Microphone'
        assert stats['duration'] == 0
        assert stats['total_frames'] == 0
        assert stats['dropped_frames'] == 0
        assert stats['sample_rate'] == 16000
        assert stats['channels'] == 1
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_get_recording_stats_while_recording(self, mock_stream_class, capture_manager):
        """Test recording statistics while recording."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Start recording
        start_time = time.time()
        capture_manager.start_recording()
        
        # Simulate some recording activity
        capture_manager._total_frames = 1000
        capture_manager._dropped_frames = 5
        
        # Small delay to ensure duration > 0
        time.sleep(0.01)
        
        stats = capture_manager.get_recording_stats()
        
        assert stats['state'] == 'recording'
        assert stats['duration'] > 0
        assert stats['total_frames'] == 1000
        assert stats['dropped_frames'] == 5
    
    def test_change_device_while_idle(self, capture_manager, mock_device_manager):
        """Test changing audio device while idle."""
        new_device = AudioDevice(
            device_id=1,
            device_name="New Microphone",
            channels=1,
            default_sample_rate=16000.0,
            max_input_channels=1,
            max_output_channels=0
        )
        mock_device_manager.select_best_device.return_value = new_device
        
        # Change device
        capture_manager.change_device(device_id=1)
        
        # Verify device was changed
        assert capture_manager._current_device.device_name == "New Microphone"
        assert capture_manager.config.device_id == 1
        assert capture_manager.config.device_name is None
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_change_device_while_recording_error(self, mock_stream_class, capture_manager):
        """Test error when changing device while recording."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Start recording
        capture_manager.start_recording()
        
        # Try to change device - should raise error
        with pytest.raises(AudioCaptureError, match="Cannot change device while recording"):
            capture_manager.change_device(device_id=1)
    
    def test_cleanup(self, capture_manager):
        """Test cleanup functionality."""
        # Set some state
        capture_manager._data_callback = Mock()
        
        # Cleanup
        capture_manager.cleanup()
        
        # Verify cleanup
        assert capture_manager._data_callback is None
        assert capture_manager._current_device is None
    
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_cleanup_while_recording(self, mock_stream_class, capture_manager):
        """Test cleanup while recording."""
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Start recording
        capture_manager.start_recording()
        assert capture_manager.is_recording()
        
        # Cleanup should stop recording
        capture_manager.cleanup()
        
        assert not capture_manager.is_recording()
        assert capture_manager._data_callback is None


# Integration tests
class TestAudioCaptureIntegration:
    """Integration tests for audio capture functionality."""
    
    @pytest.fixture
    def integration_config(self):
        """Configuration for integration testing."""
        return AudioConfig(
            sample_rate=16000,
            channels=1,
            input_buffer_size=512,
            noise_suppression=False,  # Disable for predictable testing
            auto_gain_control=False
        )
    
    @patch('nextalk.audio.capture.AudioDeviceManager')
    @patch('nextalk.audio.capture.sd.InputStream')
    def test_full_recording_workflow(self, mock_stream_class, mock_device_manager_class, integration_config):
        """Test complete recording workflow with simulated audio data."""
        # Setup mocks
        mock_device = AudioDevice(
            device_id=0,
            device_name="Test Device",
            channels=1,
            default_sample_rate=16000.0,
            max_input_channels=1,
            max_output_channels=0
        )
        
        mock_device_manager = Mock()
        mock_device_manager.select_best_device.return_value = mock_device
        mock_device_manager.validate_device_config.return_value = []
        mock_device_manager_class.return_value = mock_device_manager
        
        mock_stream = Mock()
        mock_stream_class.return_value = mock_stream
        
        # Create capture manager
        capture_manager = AudioCaptureManager(integration_config)
        
        # Set up callback to collect data
        received_data = []
        def data_callback(audio_data: AudioData):
            received_data.append(audio_data)
        
        capture_manager.set_data_callback(data_callback)
        
        # Start recording
        capture_manager.start_recording()
        assert capture_manager.is_recording()
        
        # Simulate audio callback with test data
        test_audio = np.array([[0.1], [0.2], [0.3], [0.4]], dtype=np.float32)
        capture_manager._audio_callback(test_audio, 4, None, Mock())
        
        # Process buffer (simulate one cycle)
        with patch('time.sleep'):  # Skip sleep in test
            capture_manager._state = CaptureState.IDLE  # Stop processing loop
            capture_manager._process_buffer()
        
        # Stop recording
        capture_manager.stop_recording()
        assert not capture_manager.is_recording()
        
        # Verify we received audio data
        assert len(received_data) >= 1
        audio_data = received_data[0]
        assert isinstance(audio_data, AudioData)
        assert audio_data.sample_rate == 16000
        assert audio_data.channels == 1
        assert len(audio_data.data) > 0