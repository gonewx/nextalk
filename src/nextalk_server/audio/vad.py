"""
Voice Activity Detection module for NexTalk.

This module provides a filter to detect speech in audio frames using WebRTC VAD.
"""

import logging
from typing import Optional

import webrtcvad

from nextalk_shared.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_FRAME_DURATION_MS,
)

# Configure logger
logger = logging.getLogger(__name__)


class VADFilter:
    """
    Voice Activity Detection filter using WebRTC VAD.
    
    Detects whether audio frames contain speech or not based on the specified
    sensitivity level.
    """
    
    def __init__(self, sensitivity: int = 2):
        """
        Initialize the VAD filter with the given sensitivity.
        
        Args:
            sensitivity: Integer between 0-3, where 0 is the least sensitive
                         and 3 is the most sensitive to detecting speech.
                         Default is 2 (medium sensitivity).
        """
        if sensitivity not in (0, 1, 2, 3):
            raise ValueError("Sensitivity must be an integer between 0 and 3")
        
        self.sensitivity = sensitivity
        self.vad_instance = webrtcvad.Vad(sensitivity)
        logger.info(f"VAD filter initialized with sensitivity level {sensitivity}")
        
    def is_speech(self, frame_data: bytes) -> bool:
        """
        Determine if the given audio frame contains speech.
        
        Args:
            frame_data: Raw PCM audio data as bytes. The frame must be either
                       10, 20, or 30ms in duration for WebRTC VAD.
        
        Returns:
            bool: True if speech is detected, False otherwise.
        """
        # Calculate frame length based on the project's constants
        # WebRTC VAD requires frames to be exactly 10, 20, or 30ms
        expected_frame_size = int(AUDIO_SAMPLE_RATE * (AUDIO_FRAME_DURATION_MS / 1000))
        
        if len(frame_data) != expected_frame_size * 2:  # *2 because 16-bit PCM (2 bytes per sample)
            logger.warning(
                f"Incorrect frame size: {len(frame_data)} bytes. "
                f"Expected {expected_frame_size * 2} bytes for {AUDIO_FRAME_DURATION_MS}ms "
                f"at {AUDIO_SAMPLE_RATE}Hz."
            )
            return False
        
        try:
            result = self.vad_instance.is_speech(frame_data, AUDIO_SAMPLE_RATE)
            return result
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return False
    
    def set_sensitivity(self, sensitivity: int) -> None:
        """
        Update the VAD sensitivity level.
        
        Args:
            sensitivity: Integer between 0-3, where 0 is the least sensitive
                         and 3 is the most sensitive to detecting speech.
        """
        if sensitivity not in (0, 1, 2, 3):
            raise ValueError("Sensitivity must be an integer between 0 and 3")
        
        self.sensitivity = sensitivity
        self.vad_instance = webrtcvad.Vad(sensitivity)
        logger.info(f"VAD sensitivity updated to level {sensitivity}") 