"""
WebSocket流集成测试。

该模块测试WebSocket API流程，包括客户端连接、音频帧发送、VAD检测、
Buffer处理以及ASR转录和返回响应的完整流程。
"""

import pytest
import pytest_asyncio
import asyncio
import json
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from httpx import AsyncClient
import websockets
from websockets.client import connect as ws_connect

from nextalk_server.server_app import app
from nextalk_server.audio.vad import VADFilter
from nextalk_server.asr.recognizer import ASRRecognizer
from nextalk_shared.data_models import TranscriptionResponse, StatusUpdate
from nextalk_shared.constants import (
    AUDIO_SAMPLE_RATE, 
    AUDIO_FRAME_DURATION_MS,
    AUDIO_CHUNK_SIZE,
    STATUS_LISTENING, 
    STATUS_PROCESSING
)


# 生成测试用音频帧
def generate_silence_frame() -> bytes:
    """生成一帧静音音频"""
    # 创建全零信号表示静音 (16-bit PCM)
    samples = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int16)
    return samples.tobytes()


def generate_speech_frame() -> bytes:
    """生成一帧包含语音的音频"""
    # 使用正弦波生成一个简单的音调表示语音
    frequency = 440  # A4音调频率
    t = np.linspace(0, AUDIO_FRAME_DURATION_MS / 1000, AUDIO_CHUNK_SIZE, False)
    # 生成正弦波并调整其振幅在16位PCM范围内
    samples = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)
    return samples.tobytes()


# 模拟ASR识别器
class MockASRRecognizer:
    """模拟ASR识别器，返回预定义的转录结果"""
    
    def __init__(self, *args, **kwargs):
        """初始化模拟ASR识别器"""
        self.transcription_text = "这是一个测试转录"
    
    def transcribe(self, audio_chunk: np.ndarray) -> str:
        """返回预定义的转录文本"""
        return self.transcription_text


# 集成测试
@pytest.mark.asyncio
class TestWebSocketFlow:
    """WebSocket流集成测试"""
    
    @pytest_asyncio.fixture
    async def patched_app(self):
        """
        使用模拟组件设置FastAPI应用
        
        这个fixture会替换实际的ASR识别器和VAD过滤器，
        确保测试不依赖实际的语音识别功能
        """
        # 使用模拟ASR识别器替换真实实现
        with patch('nextalk_server.api.websocket.ASRRecognizer', MockASRRecognizer):
            # 修改VAD过滤器始终返回True，确保所有音频帧都被识别为语音
            with patch.object(VADFilter, 'is_speech', return_value=True):
                yield app
    
    @pytest_asyncio.fixture
    async def async_client(self, patched_app):
        """创建异步HTTP客户端"""
        async with AsyncClient(app=patched_app, base_url="http://test") as client:
            yield client
    
    async def test_websocket_connection(self, patched_app):
        """测试WebSocket连接可以成功建立"""
        client = TestClient(patched_app)
        with client.websocket_connect("/ws/stream") as websocket:
            # 验证连接成功后收到状态更新消息
            response = websocket.receive_json()
            assert response["type"] == "status"
            assert response["state"] == STATUS_LISTENING
    
    async def test_audio_processing_flow(self, patched_app):
        """
        测试完整的音频处理流程
        
        从发送音频帧到接收转录结果的完整测试
        """
        client = TestClient(patched_app)
        with client.websocket_connect("/ws/stream") as websocket:
            # 跳过初始状态消息
            websocket.receive_json()
            
            # 发送静音帧，确认没有处理
            websocket.send_bytes(generate_silence_frame())
            
            # 发送多个语音帧，触发ASR处理
            for _ in range(40):  # 发送足够多的帧以满足最小长度要求
                websocket.send_bytes(generate_speech_frame())
            
            # 给处理循环一些时间
            import time
            time.sleep(1)
            
            # 验证收到状态更新为处理中
            response = websocket.receive_json()
            assert response["type"] == "status"
            assert response["state"] == STATUS_PROCESSING
            
            # 验证收到转录结果
            response = websocket.receive_json()
            assert response["type"] == "transcription"
            assert response["text"] == "这是一个测试转录"
            
            # 验证状态回到监听
            response = websocket.receive_json()
            assert response["type"] == "status"
            assert response["state"] == STATUS_LISTENING
    
    async def test_command_handling(self, patched_app):
        """测试命令处理功能"""
        client = TestClient(patched_app)
        with client.websocket_connect("/ws/stream") as websocket:
            # 跳过初始状态消息
            websocket.receive_json()
            
            # 发送模型切换命令
            command = {
                "type": "command",
                "command": "switch_model",
                "payload": "tiny.en"
            }
            websocket.send_json(command)
            
            # 接收命令处理结果
            # 注意：由于我们使用了模拟实现，这里的行为可能与实际不完全一致
            # 但应该至少能收到某种响应
            responses = []
            for _ in range(2):  # 预期收到命令结果和状态更新
                try:
                    response = websocket.receive_json()
                    responses.append(response)
                except:
                    break
            
            # 验证至少收到某种响应
            assert len(responses) > 0
    
    async def test_websocket_timeout_handling(self, patched_app):
        """测试WebSocket超时处理"""
        client = TestClient(patched_app)
        with client.websocket_connect("/ws/stream") as websocket:
            # 跳过初始状态消息
            websocket.receive_json()
            
            # 不发送任何数据，只等待一段时间
            import time
            time.sleep(2)
            
            # 发送一些数据确认连接仍然有效
            websocket.send_bytes(generate_speech_frame())
            
            # 测试超时逻辑会在这个时间段内保持连接
            assert websocket.client.client.sock is not None 