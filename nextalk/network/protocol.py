"""
FunASR WebSocket protocol implementation.

Handles message formatting, parsing, and protocol-specific logic based on funasr_wss_client.py.
"""

import json
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types for FunASR protocol."""
    INIT = "init"           # Initial configuration message
    AUDIO = "audio"         # Audio data message
    END = "end"            # End of audio stream
    RESULT = "result"      # Recognition result from server
    ERROR = "error"        # Error message
    STATUS = "status"      # Status update


@dataclass
class RecognitionResult:
    """Container for speech recognition results."""
    text: str
    confidence: float = 0.0
    is_final: bool = False
    timestamp: float = 0.0
    words: Optional[List[Dict[str, Any]]] = None
    wav_name: str = ""
    mode: str = ""
    
    def __str__(self) -> str:
        status = "Final" if self.is_final else "Partial"
        return f"[{status}] {self.text} (confidence: {self.confidence:.2f})"


class FunASRProtocol:
    """
    FunASR WebSocket protocol handler.
    
    Based on funasr_wss_client.py protocol implementation with enhancements.
    """
    
    def __init__(self, config):
        """
        Initialize protocol handler.
        
        Args:
            config: Server and recognition configuration
        """
        self.server_config = config.server
        self.audio_config = config.audio
        self.recognition_config = config.recognition
        
        # Protocol state
        self._session_id: Optional[str] = None
        self._is_initialized = False
        
    def create_init_message(self, wav_name: str = "nextalk_session", audio_fs: int = None, wav_format: str = None) -> str:
        """
        Create initialization message for FunASR server.
        
        Based on funasr_wss_client.py initialization logic.
        
        Args:
            wav_name: Name identifier for this audio session
            audio_fs: Audio sample rate (for file mode)
            wav_format: Audio format (for file mode, e.g., 'pcm', 'wav')
            
        Returns:
            JSON-encoded initialization message
        """
        # Process hotwords
        hotword_msg = ""
        if self.recognition_config.hotwords:
            # Convert list of hotwords to FunASR format
            if isinstance(self.recognition_config.hotwords, list):
                # Simple hotword list - assign default weight
                fst_dict = {word: 20 for word in self.recognition_config.hotwords}
                hotword_msg = json.dumps(fst_dict)
            else:
                hotword_msg = str(self.recognition_config.hotwords)
        elif self.recognition_config.hotword_file:
            # Load from file (similar to funasr_wss_client.py)
            try:
                fst_dict = {}
                with open(self.recognition_config.hotword_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            try:
                                word = " ".join(parts[:-1])
                                weight = int(parts[-1])
                                fst_dict[word] = weight
                            except ValueError:
                                logger.warning(f"Invalid hotword format: {line.strip()}")
                hotword_msg = json.dumps(fst_dict) if fst_dict else ""
            except Exception as e:
                logger.error(f"Failed to load hotwords from file: {e}")
                hotword_msg = ""
        
        # Create initialization message (matches funasr_wss_client.py format)
        message = {
            "mode": self.recognition_config.mode,
            "chunk_size": self.audio_config.chunk_size,
            "chunk_interval": self.audio_config.chunk_interval,
            "encoder_chunk_look_back": self.audio_config.encoder_chunk_look_back,
            "decoder_chunk_look_back": self.audio_config.decoder_chunk_look_back,
            "wav_name": wav_name,
            "is_speaking": True,
            "hotwords": hotword_msg,
            "itn": self.recognition_config.use_itn,
        }
        
        # Follow original funasr_wss_client.py exactly:
        # Microphone mode (real-time): NO audio_fs/wav_format fields
        # File mode: ALWAYS includes audio_fs and wav_format
        
        if wav_name == "microphone":
            # Real-time microphone mode - no additional fields needed
            logger.debug("Creating microphone mode init message (no audio_fs/wav_format)")
        else:
            # File mode - add audio format fields
            if audio_fs is not None:
                message["audio_fs"] = audio_fs
            if wav_format is not None:
                message["wav_format"] = wav_format
        
        init_msg = json.dumps(message, ensure_ascii=False)
        logger.info(f"Created FunASR init message: {init_msg}")
        
        self._is_initialized = True
        return init_msg
    
    def create_audio_message(self, audio_data: bytes) -> bytes:
        """
        Create audio data message.
        
        Args:
            audio_data: Raw audio bytes (PCM format)
            
        Returns:
            Audio data as bytes (direct transmission)
        """
        # Audio data is sent directly as bytes (matches funasr_wss_client.py)
        return audio_data
    
    def create_end_message(self) -> str:
        """
        Create end-of-stream message (exactly matches funasr_wss_client.py format).
        
        Returns:
            JSON-encoded end message
        """
        end_msg = json.dumps({
            "is_speaking": False
        }, ensure_ascii=False)
        
        logger.debug("Created end message")
        return end_msg
    
    def parse_message(self, message: Union[str, bytes]) -> Dict[str, Any]:
        """
        Parse incoming message from FunASR server.
        
        Args:
            message: Raw message from server
            
        Returns:
            Parsed message dictionary
        """
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            
            # Parse JSON message
            data = json.loads(message)
            
            # Add message type detection based on FunASR protocol
            if "text" in data and data["text"]:  # Non-empty text indicates result
                data["message_type"] = MessageType.RESULT.value
                logger.debug(f"Detected result message with text: '{data['text']}'")
            elif "text" in data:  # Empty text but has text field
                data["message_type"] = MessageType.RESULT.value
                logger.debug("Detected result message with empty text")
            elif "error" in data or "code" in data:
                data["message_type"] = MessageType.ERROR.value
            elif "status" in data:
                data["message_type"] = MessageType.STATUS.value
            else:
                # Default to result for FunASR messages
                data["message_type"] = MessageType.RESULT.value
                logger.debug(f"Defaulting to result message type for: {data}")
                
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON message: {e}")
            return {
                "message_type": MessageType.ERROR.value,
                "error": f"JSON decode error: {e}",
                "raw_message": message
            }
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return {
                "message_type": MessageType.ERROR.value,
                "error": f"Parse error: {e}",
                "raw_message": message
            }
    
    def extract_recognition_result(self, message_data: Dict[str, Any]) -> Optional[RecognitionResult]:
        """
        Extract recognition result from parsed message.
        
        Args:
            message_data: Parsed message data
            
        Returns:
            RecognitionResult object or None if not a result message
        """
        if message_data.get("message_type") != MessageType.RESULT.value:
            return None
        
        try:
            # Handle different result formats from FunASR
            text = ""
            confidence = 0.0
            is_final = False
            wav_name = message_data.get("wav_name", "")
            mode = message_data.get("mode", "")
            words = None
            
            # Extract text from FunASR message format (matches original client processing)
            if "text" in message_data:
                text = message_data["text"]
                logger.debug(f"Extracted text from 'text' field: '{text}'")
            elif "result" in message_data:
                if isinstance(message_data["result"], list) and message_data["result"]:
                    # Handle result list format
                    result_item = message_data["result"][0]
                    if isinstance(result_item, dict):
                        text = result_item.get("text", "")
                        confidence = result_item.get("confidence", 0.0)
                        words = result_item.get("words", None)
                    else:
                        text = str(result_item)
                elif isinstance(message_data["result"], str):
                    text = message_data["result"]
                logger.debug(f"Extracted text from 'result' field: '{text}'")
            
            # Process all messages including empty ones for 2pass mode
            # Empty messages are part of the normal 2pass flow
            # Don't filter any messages - let the application layer decide
            if text == "" and mode:
                logger.debug(f"Processing empty text message from mode: {mode}")
            
            # Determine if result is final
            is_final = message_data.get("is_final", False) or message_data.get("final", False)
            
            # Extract confidence if available
            if "confidence" in message_data:
                confidence = float(message_data["confidence"])
            
            # Extract timestamp
            timestamp = message_data.get("timestamp", 0.0)
            
            result = RecognitionResult(
                text=text.strip() if text else "",
                confidence=confidence,
                is_final=is_final,
                timestamp=timestamp,
                words=words,
                wav_name=wav_name,
                mode=mode
            )
            
            logger.debug(f"Extracted recognition result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract recognition result: {e}")
            return None
    
    def is_error_message(self, message_data: Dict[str, Any]) -> bool:
        """Check if message indicates an error."""
        return (
            message_data.get("message_type") == MessageType.ERROR.value or
            "error" in message_data or
            "code" in message_data
        )
    
    def get_error_info(self, message_data: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract error information from message.
        
        Returns:
            Tuple of (error_code, error_message)
        """
        error_code = str(message_data.get("code", "UNKNOWN"))
        error_message = message_data.get("error", message_data.get("message", "Unknown error"))
        
        return error_code, error_message
    
    def validate_config(self) -> List[str]:
        """
        Validate protocol configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate mode
        valid_modes = ["offline", "online", "2pass"]
        if self.recognition_config.mode not in valid_modes:
            errors.append(f"Invalid recognition mode: {self.recognition_config.mode}")
        
        # Validate chunk size
        if len(self.audio_config.chunk_size) != 3:
            errors.append("chunk_size must have exactly 3 values")
        
        # Validate chunk interval
        if self.audio_config.chunk_interval <= 0:
            errors.append("chunk_interval must be positive")
        
        # Validate hotword file if specified
        if self.recognition_config.hotword_file:
            import os
            if not os.path.exists(self.recognition_config.hotword_file):
                errors.append(f"Hotword file not found: {self.recognition_config.hotword_file}")
        
        return errors
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol configuration summary."""
        return {
            "mode": self.recognition_config.mode,
            "chunk_size": self.audio_config.chunk_size,
            "chunk_interval": self.audio_config.chunk_interval,
            "use_itn": self.recognition_config.use_itn,
            "hotwords_enabled": bool(self.recognition_config.hotwords or self.recognition_config.hotword_file),
            "initialized": self._is_initialized
        }