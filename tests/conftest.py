"""
Pytest配置和通用测试夹具（fixtures）

该模块定义全局pytest配置和可重用的测试夹具（fixtures），
用于整个NexTalk项目的测试。
"""

import os
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock
import wave

from nextalk_shared.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_FRAME_DURATION_MS,
    AUDIO_CHUNK_SIZE,
)
from nextalk_server.asr.recognizer import ASRRecognizer


# 路径常量
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def audio_fixtures_path():
    """返回测试音频文件目录的路径"""
    return FIXTURES_DIR


@pytest.fixture
def silence_wav_path(audio_fixtures_path):
    """返回静音WAV文件的路径"""
    return audio_fixtures_path / "silence.wav"


@pytest.fixture
def speech_wav_path(audio_fixtures_path):
    """返回语音WAV文件的路径"""
    return audio_fixtures_path / "speech.wav"


@pytest.fixture
def load_wav_file():
    """
    返回一个用于加载WAV文件并返回音频数据和参数的函数
    
    Returns:
        函数，接受文件路径参数，返回元组 (音频数据, 采样率, 通道数, 帧数)
    """
    def _load_wav(file_path):
        with wave.open(str(file_path), 'rb') as wav_file:
            # 获取WAV文件参数
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            
            # 读取音频数据
            audio_data = wav_file.readframes(n_frames)
            
            # 转换为numpy数组
            if sample_width == 2:  # 16-bit PCM
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
            elif sample_width == 4:  # 32-bit PCM
                audio_array = np.frombuffer(audio_data, dtype=np.int32)
            elif sample_width == 1:  # 8-bit PCM
                audio_array = np.frombuffer(audio_data, dtype=np.uint8)
            else:
                raise ValueError(f"不支持的样本宽度: {sample_width}")
            
            return audio_array, sample_rate, channels, n_frames
    
    return _load_wav


@pytest.fixture
def wav_to_frames():
    """
    返回一个用于将WAV文件转换为固定大小帧的函数
    
    将WAV文件数据分割成NexTalk项目使用的标准帧大小
    """
    def _wav_to_frames(audio_array, frame_size=AUDIO_CHUNK_SIZE):
        # 确保音频数据长度是帧大小的整数倍
        full_frames_count = len(audio_array) // frame_size
        
        # 分割成帧
        frames = []
        for i in range(full_frames_count):
            frame = audio_array[i * frame_size: (i + 1) * frame_size]
            frames.append(frame.tobytes())
        
        return frames
    
    return _wav_to_frames


@pytest.fixture
def generate_silence_frame():
    """生成一帧静音音频"""
    def _generate():
        # 创建全零信号表示静音 (16-bit PCM)
        samples = np.zeros(AUDIO_CHUNK_SIZE, dtype=np.int16)
        return samples.tobytes()
    
    return _generate


@pytest.fixture
def generate_speech_frame():
    """生成一帧包含语音的音频"""
    def _generate(frequency=440):
        # 使用正弦波生成一个简单的音调表示语音
        t = np.linspace(0, AUDIO_FRAME_DURATION_MS / 1000, AUDIO_CHUNK_SIZE, False)
        # 生成正弦波并调整其振幅在16位PCM范围内
        samples = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16)
        return samples.tobytes()
    
    return _generate


@pytest.fixture
def mock_asr_recognizer():
    """提供一个模拟的ASR识别器，返回预定义的转录结果"""
    class MockASRRecognizer:
        def __init__(self, model_size=None, model_path=None, device=None, compute_type=None):
            self.transcription_text = "这是一个测试转录"
            self.model_size = model_size
            self.model_path = model_path
            self.device = device
            self.compute_type = compute_type
        
        def transcribe(self, audio_chunk):
            return self.transcription_text
    
    return MockASRRecognizer


@pytest.fixture
def patched_asr_recognizer():
    """
    临时替换真实的ASR识别器为模拟版本
    
    使用该fixture将自动在测试中用模拟版本替换真实实现，
    并在测试结束后恢复。
    """
    mock_recognizer = MagicMock()
    mock_recognizer.return_value.transcribe.return_value = "这是一个测试转录"
    
    with patch('nextalk_server.asr.recognizer.ASRRecognizer', mock_recognizer):
        yield mock_recognizer


@pytest.fixture
def config_file_path():
    """返回配置文件的默认路径"""
    return Path.home() / ".config" / "nextalk" / "config.ini" 