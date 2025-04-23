"""
Unit tests for the Voice Activity Detection (VAD) module.

This module tests the VADFilter class functionality with different sensitivity
levels and audio input types.
"""

import pytest
import os
import struct
from pathlib import Path

from nextalk_server.audio.vad import VADFilter
from nextalk_shared.constants import AUDIO_SAMPLE_RATE, AUDIO_FRAME_DURATION_MS

# 计算每帧的样本数
SAMPLES_PER_FRAME = int(AUDIO_SAMPLE_RATE * (AUDIO_FRAME_DURATION_MS / 1000))
# 计算每帧的字节数（16位PCM = 2字节/样本）
BYTES_PER_FRAME = SAMPLES_PER_FRAME * 2


def create_sine_wave_frame(frequency=1000, amplitude=10000):
    """
    创建一个正弦波音频帧，模拟语音信号。
    
    Args:
        frequency: 频率（Hz）
        amplitude: 振幅
        
    Returns:
        bytes: 音频帧数据
    """
    import math
    samples = []
    for i in range(SAMPLES_PER_FRAME):
        # 创建正弦波
        sample = amplitude * math.sin(2 * math.pi * frequency * i / AUDIO_SAMPLE_RATE)
        # 转换为16位整数并限制范围
        sample = max(min(int(sample), 32767), -32768)
        samples.append(sample)
    
    # 将样本转换为字节
    return struct.pack(f"<{SAMPLES_PER_FRAME}h", *samples)


def create_silence_frame():
    """
    创建一个静音帧（全为0的信号）。
    
    Returns:
        bytes: 音频帧数据
    """
    # 创建全为0的数组（表示静音）
    samples = [0] * SAMPLES_PER_FRAME
    # 将样本转换为字节
    return struct.pack(f"<{SAMPLES_PER_FRAME}h", *samples)


def create_low_energy_noise_frame():
    """
    创建一个低能量噪声帧。
    
    Returns:
        bytes: 音频帧数据
    """
    import random
    samples = []
    for _ in range(SAMPLES_PER_FRAME):
        # 创建低能量随机噪声 (-100 到 100)
        sample = random.randint(-100, 100)
        samples.append(sample)
    
    # 将样本转换为字节
    return struct.pack(f"<{SAMPLES_PER_FRAME}h", *samples)


def create_high_energy_noise_frame():
    """
    创建一个高能量噪声帧。
    
    Returns:
        bytes: 音频帧数据
    """
    import random
    samples = []
    for _ in range(SAMPLES_PER_FRAME):
        # 创建高能量随机噪声 (-10000 到 10000)
        sample = random.randint(-10000, 10000)
        samples.append(sample)
    
    # 将样本转换为字节
    return struct.pack(f"<{SAMPLES_PER_FRAME}h", *samples)


def create_invalid_size_frame():
    """
    创建一个无效大小的帧（长度不符合要求）。
    
    Returns:
        bytes: 无效大小的音频帧数据
    """
    return b'\x00' * (BYTES_PER_FRAME - 10)  # 比正确大小小10字节


class TestVADFilter:
    """测试VADFilter类的功能"""
    
    @pytest.fixture
    def speech_frame(self):
        """创建模拟语音的测试帧"""
        return create_sine_wave_frame()
    
    @pytest.fixture
    def silence_frame(self):
        """创建静音测试帧"""
        return create_silence_frame()
    
    @pytest.fixture
    def low_noise_frame(self):
        """创建低噪声测试帧"""
        return create_low_energy_noise_frame()
    
    @pytest.fixture
    def high_noise_frame(self):
        """创建高噪声测试帧"""
        return create_high_energy_noise_frame()
    
    @pytest.fixture
    def invalid_frame(self):
        """创建大小无效的测试帧"""
        return create_invalid_size_frame()

    def test_initialization(self):
        """测试VADFilter初始化"""
        # 测试有效敏感度初始化
        for sensitivity in range(4):  # 0-3都是有效的
            vad_filter = VADFilter(sensitivity=sensitivity)
            assert vad_filter.sensitivity == sensitivity
        
        # 测试无效敏感度初始化
        with pytest.raises(ValueError):
            VADFilter(sensitivity=-1)
        
        with pytest.raises(ValueError):
            VADFilter(sensitivity=4)
    
    def test_sensitivity_update(self):
        """测试敏感度更新功能"""
        vad_filter = VADFilter(sensitivity=0)
        assert vad_filter.sensitivity == 0
        
        # 更新到有效值
        vad_filter.set_sensitivity(3)
        assert vad_filter.sensitivity == 3
        
        # 更新到无效值
        with pytest.raises(ValueError):
            vad_filter.set_sensitivity(5)
    
    def test_is_speech_with_silence(self, silence_frame):
        """测试静音输入的检测结果"""
        # 使用不同敏感度测试静音帧
        for sensitivity in range(4):
            vad_filter = VADFilter(sensitivity=sensitivity)
            result = vad_filter.is_speech(silence_frame)
            # 静音帧应该返回False
            assert result is False, f"敏感度{sensitivity}下静音帧被误判为语音"
    
    def test_is_speech_with_speech(self, speech_frame):
        """测试语音输入的检测结果"""
        # 使用不同敏感度测试语音帧
        # 注意：敏感度为0时可能会将语音判断为非语音，所以从1开始测试
        for sensitivity in range(1, 4):
            vad_filter = VADFilter(sensitivity=sensitivity)
            result = vad_filter.is_speech(speech_frame)
            # 语音帧应该返回True（在敏感度足够高时）
            assert result is True, f"敏感度{sensitivity}下语音帧被误判为非语音"
    
    def test_is_speech_with_low_noise(self, low_noise_frame):
        """测试低噪声输入的检测结果"""
        # 低噪声通常不应被识别为语音，除非敏感度很高
        vad_filter_low = VADFilter(sensitivity=0)
        assert vad_filter_low.is_speech(low_noise_frame) is False
        
        # 敏感度高时，低噪声可能被判断为语音，但结果可能不稳定，所以不做断言
    
    def test_is_speech_with_high_noise(self, high_noise_frame):
        """测试高噪声输入的检测结果"""
        # 高噪声在不同敏感度下的表现，结果可能不稳定，主要测试方法是否正常执行
        for sensitivity in range(4):
            vad_filter = VADFilter(sensitivity=sensitivity)
            # 仅测试方法是否执行，不断言结果
            vad_filter.is_speech(high_noise_frame)
    
    def test_invalid_frame_size(self, invalid_frame):
        """测试无效大小帧的处理"""
        vad_filter = VADFilter()
        # 无效大小帧应该返回False
        assert vad_filter.is_speech(invalid_frame) is False 