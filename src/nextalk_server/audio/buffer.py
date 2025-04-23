"""
Audio buffer module for NexTalk.

This module provides a thread-safe buffer for audio frames.
"""

import logging
import queue
import time
from threading import Lock
from typing import Optional, Tuple

import numpy as np

from nextalk_shared.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_FRAME_DURATION_MS,
)

# Configure logger
logger = logging.getLogger(__name__)


class AudioBuffer:
    """
    Thread-safe audio buffer for collecting and retrieving audio frames.
    
    Collects incoming audio frames and allows retrieval of combined segments
    of a minimum specified duration for processing by the ASR system.
    """
    
    def __init__(self, max_size: int = 300):
        """
        Initialize the audio buffer.
        
        Args:
            max_size: Maximum number of frames to store in the buffer.
                     Default is 300 frames (9 seconds at 30ms per frame).
        """
        self.buffer = queue.Queue(maxsize=max_size)
        self.lock = Lock()
        self.max_size = max_size
        self.last_frame_time = 0
        logger.info(f"Audio buffer initialized with max size of {max_size} frames")
    
    def add_frame(self, frame_data: bytes) -> bool:
        """
        Add an audio frame to the buffer.
        
        Args:
            frame_data: Raw PCM audio data as bytes.
            
        Returns:
            bool: True if the frame was added successfully, False otherwise.
        """
        try:
            # Update the timestamp for this frame
            current_time = time.time()
            with self.lock:
                self.last_frame_time = current_time
            
            # Try to add to the queue, but don't block if full
            self.buffer.put_nowait(frame_data)
            return True
        except queue.Full:
            logger.warning("Audio buffer full, dropping oldest frame")
            try:
                # If buffer is full, remove oldest frame and try again
                self.buffer.get_nowait()
                self.buffer.put_nowait(frame_data)
                return True
            except (queue.Empty, queue.Full):
                logger.error("Failed to add frame to buffer")
                return False
    
    def get_segment(self, min_duration_ms: int = 500) -> Optional[Tuple[np.ndarray, int]]:
        """
        Retrieve an audio segment of at least the specified minimum duration.
        
        Args:
            min_duration_ms: Minimum duration of the audio segment in milliseconds.
                            Default is 500ms.
                            
        Returns:
            Tuple containing:
            - numpy.ndarray: Audio data as a float32 numpy array, with values in [-1.0, 1.0]
            - int: Sample rate of the audio data
            
            Returns None if not enough frames are available.
        """
        # Calculate minimum number of frames needed
        min_frames = int(min_duration_ms / AUDIO_FRAME_DURATION_MS)
        
        # Check if we have enough frames
        if self.buffer.qsize() < min_frames:
            return None
        
        frames = []
        frame_count = 0
        
        # Try to collect at least min_frames frames
        with self.lock:
            while frame_count < min_frames and not self.buffer.empty():
                try:
                    frames.append(self.buffer.get_nowait())
                    frame_count += 1
                except queue.Empty:
                    break
        
        if frame_count < min_frames:
            # If we couldn't get enough frames, put back what we got
            for frame in frames:
                try:
                    self.buffer.put_nowait(frame)
                except queue.Full:
                    logger.warning("Buffer full when returning frames, some frames were lost")
            return None
        
        # Convert the frames to a numpy array
        # Assuming 16-bit PCM audio (int16)
        combined_bytes = b''.join(frames)
        audio_array = np.frombuffer(combined_bytes, dtype=np.int16)
        
        # Convert to float32 and normalize to [-1.0, 1.0]
        float_array = audio_array.astype(np.float32) / 32768.0
        
        logger.debug(f"Retrieved audio segment of {frame_count} frames ({frame_count * AUDIO_FRAME_DURATION_MS}ms)")
        return float_array, AUDIO_SAMPLE_RATE
    
    def clear(self) -> None:
        """Clear all frames from the buffer."""
        with self.lock:
            while not self.buffer.empty():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    break
        logger.info("Audio buffer cleared")
    
    def get_buffer_status(self) -> dict:
        """
        Get the current status of the buffer.
        
        Returns:
            dict: A dictionary containing buffer status information:
                - current_size: Current number of frames in the buffer
                - max_size: Maximum capacity of the buffer
                - duration_ms: Approximate duration of audio in the buffer in ms
                - last_frame_age: Time since the last frame was added in seconds
        """
        with self.lock:
            current_size = self.buffer.qsize()
            duration_ms = current_size * AUDIO_FRAME_DURATION_MS
            last_frame_age = time.time() - self.last_frame_time if self.last_frame_time > 0 else 0
            
        return {
            "current_size": current_size,
            "max_size": self.max_size,
            "duration_ms": duration_ms,
            "last_frame_age": last_frame_age
        } 