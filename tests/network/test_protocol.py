"""
Unit tests for FunASR protocol handling.

Tests protocol message creation, parsing, and validation.
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any
from unittest.mock import patch, mock_open

from nextalk.network.protocol import (
    FunASRProtocol,
    RecognitionResult,
    MessageType
)
from nextalk.config.models import NexTalkConfig


class TestRecognitionResult:
    """Test RecognitionResult data class."""
    
    def test_recognition_result_creation(self):
        """Test RecognitionResult creation with valid parameters."""
        result = RecognitionResult(
            text="Hello world",
            confidence=0.95,
            is_final=True,
            timestamp=1234567890.0,
            wav_name="test_audio",
            mode="2pass"
        )
        
        assert result.text == "Hello world"
        assert result.confidence == 0.95
        assert result.is_final is True
        assert result.timestamp == 1234567890.0
        assert result.wav_name == "test_audio"
        assert result.mode == "2pass"
    
    def test_recognition_result_str_representation(self):
        """Test string representation of RecognitionResult."""
        result = RecognitionResult(
            text="Test message",
            confidence=0.85,
            is_final=False
        )
        
        str_repr = str(result)
        assert "Partial" in str_repr
        assert "Test message" in str_repr
        assert "0.85" in str_repr
        
        # Test final result
        result.is_final = True
        str_repr = str(result)
        assert "Final" in str_repr


class TestFunASRProtocol:
    """Test FunASR protocol handler."""
    
    @pytest.fixture
    def protocol_config(self, default_nextalk_config):
        """Create protocol configuration for testing."""
        return default_nextalk_config
    
    @pytest.fixture
    def protocol(self, protocol_config):
        """Create FunASRProtocol instance for testing."""
        return FunASRProtocol(protocol_config)
    
    def test_protocol_initialization(self, protocol, protocol_config):
        """Test protocol initialization."""
        assert protocol.server_config == protocol_config.server
        assert protocol.audio_config == protocol_config.audio
        assert protocol.recognition_config == protocol_config.recognition
        assert protocol._is_initialized is False
    
    def test_create_init_message_basic(self, protocol):
        """Test basic initialization message creation."""
        init_msg = protocol.create_init_message("test_session")
        
        # Parse JSON message
        data = json.loads(init_msg)
        
        # Verify required fields
        assert data["mode"] == "2pass"
        assert data["wav_name"] == "test_session"
        assert data["is_speaking"] is True
        assert data["itn"] is True
        assert "chunk_size" in data
        assert "chunk_interval" in data
        assert "encoder_chunk_look_back" in data
        assert "decoder_chunk_look_back" in data
        
        assert protocol._is_initialized is True
    
    def test_create_init_message_with_hotwords(self, protocol):
        """Test initialization message with hotwords."""
        protocol.recognition_config.hotwords = ["测试词汇", "语音识别"]
        
        init_msg = protocol.create_init_message()
        data = json.loads(init_msg)
        
        # Verify hotwords are included
        assert data["hotwords"] != ""
        hotwords = json.loads(data["hotwords"])
        assert "测试词汇" in hotwords
        assert "语音识别" in hotwords
        assert hotwords["测试词汇"] == 20  # Default weight
    
    def test_create_init_message_with_hotword_file(self, protocol):
        """Test initialization message with hotword file."""
        # Create temporary hotword file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("阿里巴巴 25\n")
            f.write("语音识别 30\n")
            f.write("invalid line\n")  # Should be ignored
            f.write("测试 invalid_weight\n")  # Should be ignored
            temp_file = f.name
        
        try:
            protocol.recognition_config.hotword_file = temp_file
            
            init_msg = protocol.create_init_message()
            data = json.loads(init_msg)
            
            # Verify hotwords from file
            hotwords = json.loads(data["hotwords"])
            assert hotwords["阿里巴巴"] == 25
            assert hotwords["语音识别"] == 30
            assert len(hotwords) == 2  # Invalid lines ignored
            
        finally:
            os.unlink(temp_file)
    
    def test_create_init_message_hotword_file_not_found(self, protocol):
        """Test handling of missing hotword file."""
        protocol.recognition_config.hotword_file = "/non/existent/file.txt"
        
        init_msg = protocol.create_init_message()
        data = json.loads(init_msg)
        
        # Should handle gracefully
        assert data["hotwords"] == ""
    
    def test_create_audio_message(self, protocol):
        """Test audio message creation."""
        audio_data = b"audio_bytes_data"
        
        message = protocol.create_audio_message(audio_data)
        
        # Audio message should be direct bytes
        assert message == audio_data
        assert isinstance(message, bytes)
    
    def test_create_end_message(self, protocol):
        """Test end-of-stream message creation."""
        end_msg = protocol.create_end_message()
        data = json.loads(end_msg)
        
        assert data["is_speaking"] is False
        assert data["wav_name"] == "end"
    
    def test_parse_message_json_string(self, protocol):
        """Test parsing JSON string message."""
        message = '{"text": "Hello", "confidence": 0.9}'
        
        parsed = protocol.parse_message(message)
        
        assert parsed["text"] == "Hello"
        assert parsed["confidence"] == 0.9
        assert parsed["message_type"] == MessageType.RESULT.value
    
    def test_parse_message_bytes(self, protocol):
        """Test parsing bytes message."""
        message = b'{"result": "Test result"}'
        
        parsed = protocol.parse_message(message)
        
        assert parsed["result"] == "Test result"
        assert parsed["message_type"] == MessageType.RESULT.value
    
    def test_parse_message_invalid_json(self, protocol):
        """Test handling of invalid JSON message."""
        message = "invalid json {"
        
        parsed = protocol.parse_message(message)
        
        assert parsed["message_type"] == MessageType.ERROR.value
        assert "JSON decode error" in parsed["error"]
        assert parsed["raw_message"] == message
    
    def test_parse_message_error_detection(self, protocol):
        """Test automatic error message detection."""
        error_message = '{"error": "Server error", "code": 500}'
        
        parsed = protocol.parse_message(error_message)
        
        assert parsed["message_type"] == MessageType.ERROR.value
    
    def test_extract_recognition_result_text_field(self, protocol):
        """Test extracting result from text field."""
        message_data = {
            "message_type": MessageType.RESULT.value,
            "text": "Recognized text",
            "confidence": 0.95,
            "is_final": True,
            "wav_name": "test.wav"
        }
        
        result = protocol.extract_recognition_result(message_data)
        
        assert result is not None
        assert result.text == "Recognized text"
        assert result.confidence == 0.95
        assert result.is_final is True
        assert result.wav_name == "test.wav"
    
    def test_extract_recognition_result_result_list(self, protocol):
        """Test extracting result from result list field."""
        message_data = {
            "message_type": MessageType.RESULT.value,
            "result": [{
                "text": "List result",
                "confidence": 0.88,
                "words": [{"word": "List"}, {"word": "result"}]
            }],
            "final": True
        }
        
        result = protocol.extract_recognition_result(message_data)
        
        assert result is not None
        assert result.text == "List result"
        assert result.confidence == 0.88
        assert result.is_final is True
        assert result.words == [{"word": "List"}, {"word": "result"}]
    
    def test_extract_recognition_result_result_string(self, protocol):
        """Test extracting result from result string field."""
        message_data = {
            "message_type": MessageType.RESULT.value,
            "result": "String result"
        }
        
        result = protocol.extract_recognition_result(message_data)
        
        assert result is not None
        assert result.text == "String result"
        assert result.confidence == 0.0  # Default
        assert result.is_final is False  # Default
    
    def test_extract_recognition_result_non_result_message(self, protocol):
        """Test extracting result from non-result message."""
        message_data = {
            "message_type": MessageType.ERROR.value,
            "error": "Some error"
        }
        
        result = protocol.extract_recognition_result(message_data)
        
        assert result is None
    
    def test_extract_recognition_result_invalid_data(self, protocol):
        """Test handling of invalid result data."""
        message_data = {
            "message_type": MessageType.RESULT.value,
            "malformed": "data"
        }
        
        result = protocol.extract_recognition_result(message_data)
        
        # Should return empty result
        assert result is not None
        assert result.text == ""
    
    def test_is_error_message(self, protocol):
        """Test error message detection."""
        # Error message type
        assert protocol.is_error_message({"message_type": MessageType.ERROR.value})
        
        # Error field
        assert protocol.is_error_message({"error": "Some error"})
        
        # Code field
        assert protocol.is_error_message({"code": 500})
        
        # Non-error message
        assert not protocol.is_error_message({"text": "Normal result"})
    
    def test_get_error_info(self, protocol):
        """Test error information extraction."""
        message_data = {
            "code": 404,
            "error": "Not found",
            "message": "Resource not found"
        }
        
        error_code, error_message = protocol.get_error_info(message_data)
        
        assert error_code == "404"
        assert error_message == "Not found"
    
    def test_get_error_info_fallback(self, protocol):
        """Test error info extraction with fallbacks."""
        # No code, use message field
        message_data = {"message": "Error occurred"}
        error_code, error_message = protocol.get_error_info(message_data)
        
        assert error_code == "UNKNOWN"
        assert error_message == "Error occurred"
        
        # No error info at all
        message_data = {"other": "data"}
        error_code, error_message = protocol.get_error_info(message_data)
        
        assert error_code == "UNKNOWN"
        assert error_message == "Unknown error"
    
    def test_validate_config_valid(self, protocol):
        """Test configuration validation with valid config."""
        errors = protocol.validate_config()
        
        # Should be no errors with default config
        assert len(errors) == 0
    
    def test_validate_config_invalid_mode(self, protocol):
        """Test validation with invalid recognition mode."""
        protocol.recognition_config.mode = "invalid_mode"
        
        errors = protocol.validate_config()
        
        assert len(errors) > 0
        assert any("Invalid recognition mode" in error for error in errors)
    
    def test_validate_config_invalid_chunk_size(self, protocol):
        """Test validation with invalid chunk size."""
        protocol.audio_config.chunk_size = [5, 10]  # Missing third value
        
        errors = protocol.validate_config()
        
        assert len(errors) > 0
        assert any("chunk_size must have exactly 3 values" in error for error in errors)
    
    def test_validate_config_invalid_chunk_interval(self, protocol):
        """Test validation with invalid chunk interval."""
        protocol.audio_config.chunk_interval = 0
        
        errors = protocol.validate_config()
        
        assert len(errors) > 0
        assert any("chunk_interval must be positive" in error for error in errors)
    
    def test_validate_config_missing_hotword_file(self, protocol):
        """Test validation with missing hotword file."""
        protocol.recognition_config.hotword_file = "/non/existent/file.txt"
        
        errors = protocol.validate_config()
        
        assert len(errors) > 0
        assert any("Hotword file not found" in error for error in errors)
    
    def test_get_protocol_info(self, protocol):
        """Test protocol information summary."""
        info = protocol.get_protocol_info()
        
        assert info["mode"] == "2pass"
        assert info["chunk_size"] == [5, 10, 5]
        assert info["chunk_interval"] == 10
        assert info["use_itn"] is True
        assert info["hotwords_enabled"] is False
        assert info["initialized"] is False
        
        # Test after initialization
        protocol.create_init_message()
        info = protocol.get_protocol_info()
        assert info["initialized"] is True
    
    def test_get_protocol_info_with_hotwords(self, protocol):
        """Test protocol info with hotwords enabled."""
        protocol.recognition_config.hotwords = ["test"]
        
        info = protocol.get_protocol_info()
        
        assert info["hotwords_enabled"] is True


# Integration-style tests
class TestFunASRProtocolIntegration:
    """Integration tests for FunASR protocol functionality."""
    
    @pytest.fixture
    def full_config(self, default_nextalk_config):
        """Create comprehensive configuration for integration testing."""
        config = default_nextalk_config
        config.recognition_config.hotwords = ["测试", "语音识别"]
        config.recognition_config.mode = "online"
        config.recognition_config.use_itn = False
        return config
    
    def test_full_message_workflow(self, full_config):
        """Test complete message creation and parsing workflow."""
        protocol = FunASRProtocol(full_config)
        
        # Create init message
        init_msg = protocol.create_init_message("integration_test")
        assert isinstance(init_msg, str)
        assert "integration_test" in init_msg
        
        # Create audio message
        audio_data = b"fake_audio_data"
        audio_msg = protocol.create_audio_message(audio_data)
        assert audio_msg == audio_data
        
        # Create end message
        end_msg = protocol.create_end_message()
        assert isinstance(end_msg, str)
        
        # Parse recognition result
        result_message = json.dumps({
            "text": "集成测试结果",
            "confidence": 0.92,
            "is_final": True,
            "timestamp": 1234567890.0
        })
        
        parsed = protocol.parse_message(result_message)
        result = protocol.extract_recognition_result(parsed)
        
        assert result is not None
        assert result.text == "集成测试结果"
        assert result.confidence == 0.92
        assert result.is_final is True
    
    def test_error_handling_workflow(self, full_config):
        """Test error handling in protocol workflow."""
        protocol = FunASRProtocol(full_config)
        
        # Test malformed message handling
        malformed_messages = [
            "not json",
            '{"incomplete": json',
            b'\xff\xfe invalid bytes',
            ""
        ]
        
        for msg in malformed_messages:
            parsed = protocol.parse_message(msg)
            assert parsed["message_type"] == MessageType.ERROR.value
            assert protocol.is_error_message(parsed)
    
    def test_protocol_configuration_edge_cases(self):
        """Test protocol with various configuration edge cases."""
        # Test with minimal config
        config = NexTalkConfig()
        config.audio_config.chunk_size = [1, 2, 3]
        config.audio_config.chunk_interval = 5
        config.recognition_config.mode = "offline"
        
        protocol = FunASRProtocol(config)
        
        # Should handle minimal config
        init_msg = protocol.create_init_message()
        data = json.loads(init_msg)
        
        assert data["mode"] == "offline"
        assert data["chunk_size"] == [1, 2, 3]
        assert data["chunk_interval"] == 5