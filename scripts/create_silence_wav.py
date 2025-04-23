#!/usr/bin/env python3
"""
生成静音WAV音频文件用于测试

该脚本创建一个16kHz采样率、单声道、16位PCM格式的静音WAV文件，
用于NexTalk项目的测试。
"""

import os
import wave
import numpy as np
from pathlib import Path

# 音频参数
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1         # 单声道
SAMPLE_WIDTH = 2     # 16位 (2字节)
DURATION_SEC = 1.0   # 1秒

# 计算样本数
num_samples = int(SAMPLE_RATE * DURATION_SEC)

# 创建静音数据 (全零)
silence = np.zeros(num_samples, dtype=np.int16)

# 目标文件路径
fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
file_path = fixtures_dir / "silence.wav"

# 确保目录存在
fixtures_dir.mkdir(parents=True, exist_ok=True)

# 创建WAV文件
with wave.open(str(file_path), 'wb') as wav_file:
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)
    wav_file.writeframes(silence.tobytes())

print(f"已创建静音音频文件: {file_path}")
print(f"文件大小: {file_path.stat().st_size} 字节")
print(f"音频格式: {SAMPLE_RATE}Hz, {CHANNELS}声道, {SAMPLE_WIDTH*8}位PCM")
print(f"音频长度: {DURATION_SEC}秒 ({num_samples}个样本)") 