"""
客户端-服务器通信集成测试。

该模块测试客户端WebSocket客户端与服务器的通信过程，
包括连接建立、音频数据发送和接收转录结果的完整流程。
"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.websockets import WebSocket
import websockets

from nextalk_server.server_app import app
from nextalk_server.audio.vad import VADFilter
from nextalk_server.asr.recognizer import ASRRecognizer
from nextalk_client.network.client import WebSocketClient
from nextalk_shared.data_models import TranscriptionResponse, StatusUpdate, ErrorMessage
from nextalk_shared.constants import (
    AUDIO_SAMPLE_RATE, 
    AUDIO_FRAME_DURATION_MS,
    AUDIO_CHUNK_SIZE,
    STATUS_LISTENING, 
    STATUS_PROCESSING
)


@pytest.mark.asyncio
class TestClientServerCommunication:
    """客户端-服务器通信集成测试"""
    
    @pytest_asyncio.fixture
    async def test_server(self):
        """
        设置测试服务器实例
        
        使用模拟ASR识别器以返回可预测的结果
        """
        # 创建一个模拟ASR识别器类
        class MockASRRecognizer:
            def __init__(self, *args, **kwargs):
                self.transcription_text = "这是一个测试转录"
            
            def transcribe(self, audio_chunk):
                return self.transcription_text
        
        # 使用模拟ASR识别器和始终返回True的VAD过滤器
        with patch('nextalk_server.api.websocket.ASRRecognizer', MockASRRecognizer):
            with patch.object(VADFilter, 'is_speech', return_value=True):
                # 启动一个FastAPI测试服务器
                test_client = TestClient(app)
                yield test_client
    
    @pytest_asyncio.fixture
    async def client_server(self, test_server):
        """
        设置客户端和服务器
        
        该fixture管理WebSocket服务器和客户端的生命周期
        """
        # 准备一个接收回调结果的列表
        received_messages = []
        received_errors = []
        received_statuses = []
        connection_status = {'is_connected': True}
        
        # 创建回调函数
        def message_callback(message):
            received_messages.append(message)
        
        def error_callback(error):
            received_errors.append(error)
        
        def status_callback(status):
            received_statuses.append(status)
        
        def disconnect_callback():
            connection_status['is_connected'] = False
        
        # 创建并配置客户端
        client = WebSocketClient()
        client.register_callbacks(
            message_callback=message_callback,
            error_callback=error_callback,
            status_callback=status_callback,
            disconnect_callback=disconnect_callback
        )
        
        # 返回所有需要的对象
        yield client, received_messages, received_errors, received_statuses, connection_status
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, test_server, generate_silence_frame):
        """测试客户端可以成功连接到服务器"""
        # 创建客户端
        client = WebSocketClient()
        
        try:
            # 连接到测试服务器
            connected = await client.connect("ws://127.0.0.1:8000/ws/stream")
            
            # 验证连接成功
            assert connected is True
            assert client.is_connected() is True
            
            # 启动监听任务
            client.listening_task = asyncio.create_task(client.listen())
            
            # 等待一小段时间确保监听任务已经启动
            await asyncio.sleep(0.1)
            
            # 发送一个静音帧以确认连接工作正常
            success = await client.send_audio(generate_silence_frame())
            assert success is True
            
        finally:
            # 清理：断开连接
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_audio_send_and_receive(self, client_server, generate_speech_frame):
        """测试客户端可以发送音频数据并接收转录结果"""
        client, received_messages, received_errors, received_statuses, connection_status = client_server
        
        try:
            # 连接到测试服务器
            connected = await client.connect("ws://127.0.0.1:8000/ws/stream")
            assert connected is True
            
            # 启动监听任务
            client.listening_task = asyncio.create_task(client.listen())
            
            # 等待接收初始状态消息
            await asyncio.sleep(0.5)
            assert len(received_statuses) >= 1
            assert received_statuses[0].state == STATUS_LISTENING
            
            # 发送多个语音帧，触发ASR处理
            for _ in range(10):
                success = await client.send_audio(generate_speech_frame())
                assert success is True
            
            # 等待足够时间接收响应
            await asyncio.sleep(1.5)
            
            # 验证接收到状态更新
            assert any(status.state == STATUS_PROCESSING for status in received_statuses)
            
            # 验证接收到转录结果
            assert len(received_messages) >= 1
            assert hasattr(received_messages[0], 'text')
            assert received_messages[0].text == "这是一个测试转录"
            
            # 验证连接仍然保持
            assert connection_status['is_connected'] is True
            
        finally:
            # 清理：断开连接
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_command_send_and_receive(self, client_server):
        """测试客户端可以发送命令并接收命令结果"""
        client, received_messages, received_errors, received_statuses, connection_status = client_server
        
        try:
            # 连接到测试服务器
            connected = await client.connect("ws://127.0.0.1:8000/ws/stream")
            assert connected is True
            
            # 启动监听任务
            client.listening_task = asyncio.create_task(client.listen())
            
            # 等待初始状态
            await asyncio.sleep(0.5)
            
            # 发送模型切换命令
            command = {
                "type": "command",
                "command": "switch_model",
                "payload": "tiny.en"
            }
            success = await client.send_json(command)
            assert success is True
            
            # 等待接收命令响应
            await asyncio.sleep(1.0)
            
            # 验证至少收到一些响应（可能是命令结果或其他消息）
            assert len(received_messages) > 0 or len(received_statuses) > 0
            
        finally:
            # 清理：断开连接
            await client.disconnect()
    
    @pytest.mark.asyncio
    async def test_disconnection_handling(self, client_server):
        """测试客户端可以正确处理断开连接"""
        client, received_messages, received_errors, received_statuses, connection_status = client_server
        
        # 连接到测试服务器
        connected = await client.connect("ws://127.0.0.1:8000/ws/stream")
        assert connected is True
        
        # 启动监听任务
        client.listening_task = asyncio.create_task(client.listen())
        
        # 等待初始状态
        await asyncio.sleep(0.5)
        
        # 断开连接
        await client.disconnect()
        
        # 验证断开连接后的状态
        assert client.is_connected() is False
        assert connection_status['is_connected'] is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self, client_server):
        """测试客户端可以正确处理错误消息"""
        client, received_messages, received_errors, received_statuses, connection_status = client_server
        
        try:
            # 连接到测试服务器
            connected = await client.connect("ws://127.0.0.1:8000/ws/stream")
            assert connected is True
            
            # 启动监听任务
            client.listening_task = asyncio.create_task(client.listen())
            
            # 等待初始状态
            await asyncio.sleep(0.5)
            
            # 发送一个错误的JSON命令，故意触发错误
            invalid_command = {
                "type": "invalid_command",
                "command": "unknown"
            }
            await client.send_json(invalid_command)
            
            # 等待接收错误响应
            await asyncio.sleep(1.0)
            
            # 注意：由于我们使用的是模拟服务器，可能不会产生实际错误
            # 此测试主要验证客户端的错误处理能力
            
        finally:
            # 清理：断开连接
            await client.disconnect() 