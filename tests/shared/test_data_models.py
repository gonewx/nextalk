"""
共享数据模型的单元测试。

该模块测试nextalk_shared.data_models中定义的Pydantic模型的
实例化、序列化和验证错误处理功能。
"""

import pytest
from pydantic import ValidationError

from nextalk_shared.data_models import (
    TranscriptionResponse,
    ErrorMessage,
    StatusUpdate,
    CommandMessage
)


class TestTranscriptionResponse:
    """测试TranscriptionResponse模型功能"""
    
    def test_instantiation_with_valid_data(self):
        """测试使用有效数据实例化模型"""
        # 使用仅文本参数实例化
        response = TranscriptionResponse(text="测试转录文本")
        
        # 验证默认类型值和提供的文本值
        assert response.type == "transcription"
        assert response.text == "测试转录文本"
        
        # 同时指定两个参数
        response = TranscriptionResponse(type="transcription", text="另一个测试")
        assert response.type == "transcription"
        assert response.text == "另一个测试"
    
    def test_serialization(self):
        """测试模型序列化为字典"""
        response = TranscriptionResponse(text="序列化测试")
        
        # 使用.dict()序列化为字典
        serialized = response.dict()
        assert isinstance(serialized, dict)
        assert serialized["type"] == "transcription"
        assert serialized["text"] == "序列化测试"
    
    def test_validation_errors(self):
        """测试验证错误处理"""
        # 缺少必需的text字段
        with pytest.raises(ValidationError):
            TranscriptionResponse()
        
        # 尝试使用非字符串类型的text
        with pytest.raises(ValidationError):
            TranscriptionResponse(text=123)
        
        # 尝试使用非字符串类型的type
        with pytest.raises(ValidationError):
            TranscriptionResponse(type=123, text="测试")
            
    def test_timestamp_validation(self):
        """测试timestamp字段接受字符串和浮点数类型"""
        # 测试字符串类型时间戳
        response1 = TranscriptionResponse(text="字符串时间戳", timestamp="2023-04-25T12:34:56")
        assert response1.timestamp == "2023-04-25T12:34:56"
        
        # 测试浮点数类型时间戳
        float_timestamp = 1682415296.123
        response2 = TranscriptionResponse(text="浮点数时间戳", timestamp=float_timestamp)
        assert response2.timestamp == float_timestamp
        
        # 测试序列化
        serialized1 = response1.dict()
        serialized2 = response2.dict()
        assert isinstance(serialized1["timestamp"], str)
        assert isinstance(serialized2["timestamp"], float)


class TestErrorMessage:
    """测试ErrorMessage模型功能"""
    
    def test_instantiation_with_valid_data(self):
        """测试使用有效数据实例化模型"""
        # 使用仅message参数实例化
        error = ErrorMessage(message="测试错误消息")
        
        # 验证默认类型值和提供的消息值
        assert error.type == "error"
        assert error.message == "测试错误消息"
        
        # 同时指定两个参数
        error = ErrorMessage(type="error", message="另一个错误")
        assert error.type == "error"
        assert error.message == "另一个错误"
    
    def test_serialization(self):
        """测试模型序列化为字典"""
        error = ErrorMessage(message="序列化错误测试")
        
        # 使用.dict()序列化为字典
        serialized = error.dict()
        assert isinstance(serialized, dict)
        assert serialized["type"] == "error"
        assert serialized["message"] == "序列化错误测试"
    
    def test_validation_errors(self):
        """测试验证错误处理"""
        # 缺少必需的message字段
        with pytest.raises(ValidationError):
            ErrorMessage()
        
        # 尝试使用非字符串类型的message
        with pytest.raises(ValidationError):
            ErrorMessage(message=123)


class TestStatusUpdate:
    """测试StatusUpdate模型功能"""
    
    def test_instantiation_with_valid_data(self):
        """测试使用有效数据实例化模型"""
        # 使用仅state参数实例化
        status = StatusUpdate(state="listening")
        
        # 验证默认类型值和提供的状态值
        assert status.type == "status"
        assert status.state == "listening"
        
        # 同时指定两个参数
        status = StatusUpdate(type="status", state="processing")
        assert status.type == "status"
        assert status.state == "processing"
    
    def test_serialization(self):
        """测试模型序列化为字典"""
        status = StatusUpdate(state="idle")
        
        # 使用.dict()序列化为字典
        serialized = status.dict()
        assert isinstance(serialized, dict)
        assert serialized["type"] == "status"
        assert serialized["state"] == "idle"
    
    def test_validation_errors(self):
        """测试验证错误处理"""
        # 缺少必需的state字段
        with pytest.raises(ValidationError):
            StatusUpdate()
        
        # 尝试使用非字符串类型的state
        with pytest.raises(ValidationError):
            StatusUpdate(state=123)


class TestCommandMessage:
    """测试CommandMessage模型功能"""
    
    def test_instantiation_with_valid_data(self):
        """测试使用有效数据实例化模型"""
        # 使用仅command参数实例化
        command = CommandMessage(command="switch_model")
        
        # 验证默认类型值、命令值和默认载荷值
        assert command.type == "command"
        assert command.command == "switch_model"
        assert command.payload == ""
        
        # 同时指定所有参数
        command = CommandMessage(
            type="command", 
            command="switch_model", 
            payload="base.en"
        )
        assert command.type == "command"
        assert command.command == "switch_model"
        assert command.payload == "base.en"
    
    def test_serialization(self):
        """测试模型序列化为字典"""
        command = CommandMessage(command="restart", payload="server")
        
        # 使用.dict()序列化为字典
        serialized = command.dict()
        assert isinstance(serialized, dict)
        assert serialized["type"] == "command"
        assert serialized["command"] == "restart"
        assert serialized["payload"] == "server"
    
    def test_validation_errors(self):
        """测试验证错误处理"""
        # 缺少必需的command字段
        with pytest.raises(ValidationError):
            CommandMessage()
        
        # 尝试使用非字符串类型的command
        with pytest.raises(ValidationError):
            CommandMessage(command=123)
        
        # 尝试使用非字符串类型的payload
        with pytest.raises(ValidationError):
            CommandMessage(command="test", payload=123) 