"""
NexTalk shared constants.

This module contains constants used throughout the NexTalk project.
"""

# Server settings
DEFAULT_SERVER_PORT = 8000

# Audio settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_FRAME_DURATION_MS = 30
# Calculate chunk size: sample_rate * (duration_ms / 1000) * channels
AUDIO_CHUNK_SIZE = int(AUDIO_SAMPLE_RATE * (AUDIO_FRAME_DURATION_MS / 1000) * AUDIO_CHANNELS)

# Status strings
STATUS_LISTENING = "listening"
STATUS_PROCESSING = "processing"
STATUS_IDLE = "idle"
STATUS_ERROR = "error"
STATUS_DISCONNECTED = "disconnected"
STATUS_CONNECTED = "connected" 