"""
Audio capture functionality for NexTalk - PyAudio implementation.

Exactly matches funasr_wss_client.py audio handling logic.
"""

import logging
import threading
import time
import numpy as np
import pyaudio
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from ..config.models import AudioConfig

logger = logging.getLogger(__name__)


class CaptureState(Enum):
    """Audio capture states."""
    IDLE = "idle"
    RECORDING = "recording"
    ERROR = "error"


@dataclass
class AudioChunk:
    """Raw audio chunk from PyAudio (matching original client)."""
    data: bytes          # Raw PCM data from PyAudio
    timestamp: float
    chunk_size: int
    
    def __len__(self) -> int:
        return len(self.data)


class AudioCaptureError(Exception):
    """Audio capture related errors."""
    pass


class PyAudioCaptureManager:
    """
    PyAudio-based capture manager matching funasr_wss_client.py exactly.
    
    Key features:
    - PyAudio paInt16 format (16-bit signed integers)
    - 16kHz mono audio (no resampling)
    - Chunk size calculated exactly like original client
    - Direct raw data streaming
    """
    
    def __init__(self, config: AudioConfig):
        """Initialize PyAudio capture (matching original client)."""
        self.config = config
        
        # Audio format matching original funasr_wss_client.py exactly (line 69-75)
        self.FORMAT = pyaudio.paInt16      # 16-bit signed integers
        self.CHANNELS = 1                  # Mono audio
        self.RATE = 16000                 # 16kHz sampling rate
        
        # Calculate chunk size exactly like original client (line 76-79)
        chunk_size_ms = 60 * config.chunk_size[1] / config.chunk_interval
        self.CHUNK = int(self.RATE / 1000 * chunk_size_ms)  # Frames per chunk
        
        logger.info(f"PyAudio config: FORMAT=paInt16, CHANNELS=1, RATE=16000Hz, CHUNK={self.CHUNK} frames")
        logger.info(f"Chunk duration: {self.CHUNK/self.RATE*1000:.1f}ms")
        
        # PyAudio instance
        self._pyaudio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        
        # State management
        self._state = CaptureState.IDLE
        self._data_callback: Optional[Callable[[AudioChunk], None]] = None
        
        # Audio buffer for accumulated recording
        self._accumulated_data: List[bytes] = []
        self._buffer_lock = threading.Lock()
        
        # Statistics
        self._start_time: Optional[float] = None
        self._total_chunks = 0
        
        # Find suitable audio device
        self._setup_device()
    
    def _setup_device(self) -> None:
        """Setup PyAudio device."""
        try:
            # List available devices for debugging
            logger.debug("Available audio devices:")
            for i in range(self._pyaudio.get_device_count()):
                info = self._pyaudio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:  # Input device
                    logger.debug(f"  {i}: {info['name']} - {info['maxInputChannels']} ch @ {info['defaultSampleRate']}Hz")
            
            # Use default input device (matching original client behavior)
            default_device = self._pyaudio.get_default_input_device_info()
            logger.info(f"Using default input device: {default_device['name']}")
            
        except Exception as e:
            logger.error(f"Failed to setup audio device: {e}")
            raise AudioCaptureError(f"Audio device setup failed: {e}")
    
    def set_data_callback(self, callback: Callable[[AudioChunk], None]) -> None:
        """Set callback for audio chunks."""
        self._data_callback = callback
    
    def _audio_callback(self, in_data: bytes, frame_count: int, time_info: dict, status_flags: int) -> tuple:
        """
        PyAudio stream callback (matches original client structure).
        
        Args:
            in_data: Raw audio data from PyAudio (paInt16 format)
            frame_count: Number of audio frames
            time_info: Timing information
            status_flags: Stream status
        """
        if status_flags:
            logger.warning(f"PyAudio stream status: {status_flags}")
        
        if self._state != CaptureState.RECORDING:
            return (in_data, pyaudio.paContinue)
        
        try:
            # Create audio chunk with raw PyAudio data
            chunk = AudioChunk(
                data=in_data,  # Raw paInt16 PCM data 
                timestamp=time.time(),
                chunk_size=frame_count
            )
            
            # Store for batch processing
            with self._buffer_lock:
                self._accumulated_data.append(in_data)
                self._total_chunks += 1
            
            # Send to callback if available
            if self._data_callback:
                try:
                    self._data_callback(chunk)
                except Exception as e:
                    logger.error(f"Error in audio callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
        
        return (in_data, pyaudio.paContinue)
    
    def start_recording(self) -> None:
        """
        Start audio recording with PyAudio stream.
        
        Raises:
            AudioCaptureError: If recording cannot be started
        """
        if self._state == CaptureState.RECORDING:
            logger.warning("Already recording")
            return
            
        try:
            self._state = CaptureState.RECORDING
            logger.info("Starting PyAudio recording...")
            
            # Clear accumulated data
            with self._buffer_lock:
                self._accumulated_data.clear()
            
            self._total_chunks = 0
            self._start_time = time.time()
            
            # Create PyAudio stream exactly matching original client (line 81-88)
            self._stream = self._pyaudio.open(
                format=self.FORMAT,
                channels=self.CHANNELS, 
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self._audio_callback
            )
            
            # Start the stream
            self._stream.start_stream()
            
            logger.info(f"PyAudio recording started: {self.CHANNELS}ch @ {self.RATE}Hz, {self.CHUNK} frames/chunk")
            
        except Exception as e:
            self._state = CaptureState.ERROR
            logger.error(f"Failed to start PyAudio recording: {e}")
            raise AudioCaptureError(f"Recording failed: {e}")
    
    def stop_recording(self) -> bytes:
        """
        Stop recording and return accumulated audio data.
        
        Returns:
            Raw PCM audio data (paInt16 format, ready for FunASR)
        """
        if self._state != CaptureState.RECORDING:
            logger.warning("Not currently recording")
            return b""
        
        try:
            logger.info("Stopping PyAudio recording...")
            
            # Stop and close stream
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            
            # Get accumulated audio data
            with self._buffer_lock:
                audio_data = b"".join(self._accumulated_data)
                self._accumulated_data.clear()
            
            self._state = CaptureState.IDLE
            
            # Log statistics
            if self._start_time:
                duration = time.time() - self._start_time
                logger.info(f"Recording stopped: {len(audio_data)} bytes, "
                          f"{duration:.2f}s, {self._total_chunks} chunks")
            
            return audio_data
            
        except Exception as e:
            self._state = CaptureState.ERROR
            logger.error(f"Error stopping recording: {e}")
            return b""
    
    def is_recording(self) -> bool:
        """Check if currently recording.""" 
        return self._state == CaptureState.RECORDING
    
    def get_state(self) -> CaptureState:
        """Get current capture state."""
        return self._state
    
    def cleanup(self) -> None:
        """Clean up PyAudio resources."""
        if self._state == CaptureState.RECORDING:
            self.stop_recording()
        
        if self._stream:
            self._stream.close()
            self._stream = None
        
        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None
        
        logger.info("PyAudio capture manager cleaned up")


# For backwards compatibility, alias the new implementation
AudioCaptureManager = PyAudioCaptureManager
AudioData = AudioChunk