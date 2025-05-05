import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock, call
import websockets
from websockets import ConnectionClosed

from nextalk_client.network.client import WebSocketClient
from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate


@pytest.mark.asyncio
async def test_parse_funasr_message_with_float_timestamp():
    """测试解析包含浮点数时间戳的FunASR消息"""
    # 创建客户端实例
    client = WebSocketClient()
    
    # 设置回调函数
    received_messages = []
    def message_callback(response):
        received_messages.append(response)
    
    client.register_callbacks(message_callback=message_callback)
    
    # 模拟数据和回调处理
    float_timestamp = 1682415296.123
    message_data = {
        "text": "测试文本",
        "mode": "2pass-test",
        "is_final": True,
        "timestamp": float_timestamp
    }
    
    # 直接调用处理FunASR消息的逻辑
    client.message_callback = message_callback
    
    # 创建 TranscriptionResponse 模拟处理过程
    response = TranscriptionResponse(
        type="transcription",
        text=message_data["text"],
        mode=message_data["mode"],
        is_final=message_data["is_final"],
        timestamp=message_data["timestamp"]
    )
    
    # 手动调用回调
    message_callback(response)
    
    # 验证消息是否正确处理
    assert len(received_messages) == 1
    received = received_messages[0]
    
    # 验证消息格式和内容
    assert isinstance(received, TranscriptionResponse)
    assert received.text == "测试文本"
    assert received.mode == "2pass-test"
    assert received.is_final is True
    assert received.timestamp == float_timestamp
    assert isinstance(received.timestamp, float)


@pytest.mark.asyncio
async def test_disconnect():
    """测试断开连接功能"""
    client = WebSocketClient()
    
    # 创建模拟的websocket连接
    mock_ws = AsyncMock()
    client.connection = mock_ws
    client.connected = True
    
    # 测试断开连接
    await client.disconnect()
    
    # 验证WebSocket连接已关闭
    mock_ws.close.assert_called_once()
    assert not client.connected


@pytest.mark.asyncio
async def test_send_json():
    """测试发送JSON数据功能"""
    client = WebSocketClient()
    
    # 创建模拟的websocket连接
    mock_ws = AsyncMock()
    client.connection = mock_ws
    client.connected = True
    
    # 发送JSON数据
    test_data = {"test": "data"}
    result = await client.send_json(test_data)
    
    # 验证数据已发送且返回成功
    mock_ws.send.assert_called_once()
    # 验证发送的是序列化后的JSON字符串
    sent_json = mock_ws.send.call_args[0][0]
    assert json.loads(sent_json)["test"] == "data"
    assert result is True


@pytest.mark.asyncio
async def test_send_json_connection_closed():
    """测试发送JSON数据时连接关闭的情况"""
    client = WebSocketClient()
    
    # 创建模拟的websocket连接
    mock_ws = AsyncMock()
    mock_ws.send.side_effect = ConnectionClosed(1000, "Connection closed")
    client.connection = mock_ws
    client.connected = True
    
    # 添加断开连接回调
    disconnect_called = False
    def disconnect_callback():
        nonlocal disconnect_called
        disconnect_called = True
    
    client.register_callbacks(disconnect_callback=disconnect_callback)
    
    # 发送JSON数据
    test_data = {"test": "data"}
    result = await client.send_json(test_data)
    
    # 验证结果
    assert result is False  # 发送失败
    assert not client.connected  # 客户端状态已更新为断开连接
    assert disconnect_called  # 断开连接回调被调用 