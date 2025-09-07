"""
Audio processing package for NexTalk.

Provides audio device management and high-quality audio capture functionality.
"""

from .device import AudioDeviceManager, AudioDevice
from .capture import AudioCaptureManager, AudioCaptureError

__all__ = ["AudioDeviceManager", "AudioDevice", "AudioCaptureManager", "AudioCaptureError"]