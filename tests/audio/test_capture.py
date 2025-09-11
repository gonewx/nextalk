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
    PyAudioCaptureManager as AudioCaptureManager,
    AudioChunk,
    CaptureState,
    AudioCaptureError
)
from nextalk.audio.device import AudioDevice, AudioDeviceManager
from nextalk.config.models import AudioConfig


class TestAudioChunk:
    """Test AudioChunk container class."""
    
    def test_audio_chunk_creation(self):
        """Test AudioChunk creation with valid parameters."""
        data = b'\x00\x01\x02\x03'  # Raw PCM bytes
        audio_chunk = AudioChunk(
            data=data,
            timestamp=1234567890.0,
            chunk_size=4
        )
        
        assert audio_chunk.data == data
        assert audio_chunk.timestamp == 1234567890.0
        assert audio_chunk.chunk_size == 4
        assert len(audio_chunk) == 4
    
    def test_audio_chunk_len_method(self):
        """Test AudioChunk __len__ method."""
        data = b'\x00\x01\x02\x03\x04\x05'  # 6 bytes
        audio_chunk = AudioChunk(
            data=data,
            timestamp=1234567890.0,
            chunk_size=6
        )
        
        assert len(audio_chunk) == 6
        assert audio_chunk.chunk_size == 6


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
        with patch('nextalk.audio.capture.pyaudio.PyAudio') as MockPyAudio:
            # Mock PyAudio instance
            mock_pyaudio_instance = MagicMock()
            mock_pyaudio_instance.get_device_count.return_value = 1
            mock_pyaudio_instance.get_device_info_by_index.return_value = {
                'name': 'Test Microphone',
                'maxInputChannels': 2,
                'defaultSampleRate': 16000
            }
            mock_pyaudio_instance.get_default_input_device_info.return_value = {
                'name': 'Test Microphone',
                'index': 0
            }
            MockPyAudio.return_value = mock_pyaudio_instance
            return AudioCaptureManager(audio_config)
    
    def test_capture_manager_initialization(self, capture_manager, audio_config):
        """Test AudioCaptureManager initialization."""
        assert capture_manager.config == audio_config
        assert capture_manager._state == CaptureState.IDLE
        assert capture_manager._pyaudio is not None
        assert capture_manager.RATE == 16000
        assert capture_manager.CHANNELS == 1
    
    def test_set_data_callback(self, capture_manager):
        """Test setting audio data callback."""
        callback = Mock()
        capture_manager.set_data_callback(callback)
        
        assert capture_manager._data_callback == callback
    
    def test_start_recording_success(self, capture_manager):
        """Test successful recording start."""
        # Mock PyAudio stream
        mock_stream = MagicMock()
        capture_manager._pyaudio.open = MagicMock(return_value=mock_stream)
        
        # Start recording
        capture_manager.start_recording()
        
        # Verify state change
        assert capture_manager.get_state() == CaptureState.RECORDING
        
        # Verify PyAudio stream was opened with correct parameters
        capture_manager._pyaudio.open.assert_called_once()
        call_args = capture_manager._pyaudio.open.call_args[1]
        assert call_args['format'] == capture_manager.FORMAT
        assert call_args['channels'] == capture_manager.CHANNELS
        assert call_args['rate'] == capture_manager.RATE
        assert call_args['input'] == True
        assert call_args['frames_per_buffer'] == capture_manager.CHUNK
        
        # Verify stream was started
        mock_stream.start_stream.assert_called_once()
    
    def test_start_recording_already_recording(self, capture_manager):
        """Test starting recording when already recording."""
        # Manually set state to RECORDING
        capture_manager._state = CaptureState.RECORDING
        
        # Should not raise error, just log warning and return
        capture_manager.start_recording()
        
        # State should remain RECORDING
        assert capture_manager.get_state() == CaptureState.RECORDING
    
    def test_start_recording_stream_error(self, capture_manager):
        """Test error handling during stream creation."""
        capture_manager._pyaudio.open = MagicMock(side_effect=Exception("Stream creation failed"))
        
        with pytest.raises(AudioCaptureError, match="Recording failed"):
            capture_manager.start_recording()
        
        # State should be ERROR
        assert capture_manager.get_state() == CaptureState.ERROR
    
    def test_stop_recording_success(self, capture_manager):
        """Test successful recording stop."""
        # Mock the stream
        mock_stream = Mock()
        capture_manager._pyaudio.open = MagicMock(return_value=mock_stream)
        
        # Start recording first (this clears accumulated data)
        capture_manager.start_recording()
        
        # Add some test data after starting
        test_data = [b"chunk1", b"chunk2", b"chunk3"]
        capture_manager._accumulated_data = test_data.copy()
        
        # Stop recording
        result = capture_manager.stop_recording()
        
        # Verify stream was stopped and closed
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        
        # Verify state
        assert capture_manager.get_state() == CaptureState.IDLE
        
        # Verify data was returned and cleared
        assert result == b"chunk1chunk2chunk3"
        assert len(capture_manager._accumulated_data) == 0
    
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
        
        # Create test audio data (raw bytes like PyAudio provides)
        test_data = b'\x00\x01\x02\x03\x04\x05'  # 6 bytes of test data
        
        # Call audio callback
        capture_manager._audio_callback(test_data, 3, {}, 0)
        
        # Verify data was added to accumulated_data
        with capture_manager._buffer_lock:
            assert len(capture_manager._accumulated_data) == 1
            assert capture_manager._accumulated_data[0] == test_data
        
        assert capture_manager._total_chunks == 1
        
        # Verify callback was called with AudioChunk
        data_callback.assert_called_once()
        chunk = data_callback.call_args[0][0]
        assert isinstance(chunk, AudioChunk)
        assert chunk.data == test_data
        assert chunk.chunk_size == 3
    
    def test_audio_callback_not_recording(self, capture_manager):
        """Test audio callback when not recording."""
        data_callback = Mock()
        capture_manager.set_data_callback(data_callback)
        capture_manager._state = CaptureState.IDLE
        
        test_data = b'\x00\x01\x02\x03'  # 4 bytes of test data
        
        # Call audio callback - should do nothing when not recording
        capture_manager._audio_callback(test_data, 2, {}, 0)
        
        # Buffer should remain empty
        with capture_manager._buffer_lock:
            assert len(capture_manager._accumulated_data) == 0
        assert capture_manager._total_chunks == 0
        
        # Callback should not be called
        data_callback.assert_not_called()
    
    @pytest.mark.skip(reason="Audio processing features not implemented in current PyAudio design")
    def test_audio_processing_noise_suppression(self, capture_manager):
        """Test audio processing with noise suppression."""
        # This test is skipped because the current PyAudioCaptureManager
        # is designed for raw audio transmission to FunASR without local processing
        pass
    
    @pytest.mark.skip(reason="Audio processing features not implemented in current PyAudio design")
    def test_audio_processing_auto_gain_control(self, capture_manager):
        """Test audio processing with auto gain control."""
        # This test is skipped because the current PyAudioCaptureManager
        # is designed for raw audio transmission to FunASR without local processing
        pass
    
    @pytest.mark.skip(reason="Buffer processing not implemented in current PyAudio streaming design")
    def test_process_buffer_with_callback(self, capture_manager):
        """Test buffer processing with data callback."""
        # This test is skipped because the current PyAudioCaptureManager
        # uses real-time streaming with immediate callback processing
        pass
    
    @pytest.mark.skip(reason="Recording statistics not implemented in current PyAudio design")
    def test_get_recording_stats(self, capture_manager):
        """Test recording statistics."""
        # This test is skipped because the current PyAudioCaptureManager
        # doesn't implement statistics collection
        pass
    
    @pytest.mark.skip(reason="Recording statistics not implemented in current PyAudio design")
    def test_get_recording_stats_while_recording(self, capture_manager):
        """Test recording statistics while recording."""
        # This test is skipped because the current PyAudioCaptureManager
        # doesn't implement statistics collection
        pass
    
    @pytest.mark.skip(reason="Dynamic device switching not implemented in current PyAudio design")
    def test_change_device_while_idle(self, capture_manager, mock_device_manager):
        """Test changing audio device while idle."""
        # This test is skipped because the current PyAudioCaptureManager
        # doesn't support dynamic device switching
        pass
    
    @pytest.mark.skip(reason="Dynamic device switching not implemented in current PyAudio design")
    def test_change_device_while_recording_error(self, capture_manager):
        """Test error when changing device while recording."""
        # This test is skipped because the current PyAudioCaptureManager
        # doesn't support dynamic device switching
        pass
    
    def test_cleanup(self, capture_manager):
        """Test cleanup functionality."""
        # Create a mock stream
        mock_stream = Mock()
        capture_manager._stream = mock_stream
        
        # Cleanup
        capture_manager.cleanup()
        
        # Verify PyAudio resources were cleaned up
        mock_stream.close.assert_called_once()
        assert capture_manager._stream is None
        assert capture_manager._pyaudio is None
    
    def test_cleanup_while_recording(self, capture_manager):
        """Test cleanup while recording."""
        # Mock the stream
        mock_stream = Mock()
        capture_manager._pyaudio.open = MagicMock(return_value=mock_stream)
        
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
    
    @patch('nextalk.audio.device.AudioDeviceManager')
    def test_full_recording_workflow(self, mock_device_manager_class, integration_config):
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
        
        # Create capture manager
        capture_manager = AudioCaptureManager(integration_config)
        
        # Mock the PyAudio stream
        mock_stream = Mock()
        capture_manager._pyaudio.open = MagicMock(return_value=mock_stream)
        
        # Set up callback to collect data
        received_chunks = []
        def data_callback(audio_chunk: AudioChunk):
            received_chunks.append(audio_chunk)
        
        capture_manager.set_data_callback(data_callback)
        
        # Start recording
        capture_manager.start_recording()
        assert capture_manager.is_recording()
        
        # Simulate audio callback with test data
        test_audio_bytes = b'\x00\x01\x02\x03\x04\x05\x06\x07'  # 8 bytes
        capture_manager._audio_callback(test_audio_bytes, 4, {}, 0)
        
        # Stop recording
        result = capture_manager.stop_recording()
        assert not capture_manager.is_recording()
        
        # Verify we collected audio data
        assert len(result) > 0
        assert isinstance(result, bytes)