#!/usr/bin/env python3
"""
generate_speech_wav.py - 生成用于测试的语音WAV文件

此脚本创建一个包含合成语音信号的WAV音频文件。
- 采样率: 16kHz (16000Hz)
- 通道数: 单声道 (Mono)
- 位深度: 16位 PCM
- 持续时间: 1.5秒
- 使用正弦波叠加模拟语音信号
"""

import wave
import numpy as np
import pathlib

# 音频参数
SAMPLE_RATE = 16000  # 采样率 16kHz
DURATION_SEC = 1.5   # 音频长度 1.5秒
CHANNELS = 1         # 单声道
SAMPLE_WIDTH = 2     # 2字节 = 16位

def generate_speech_signal(duration_sec, sample_rate):
    """生成模拟语音信号（使用多个频率的正弦波混合）"""
    # 创建时间轴
    t = np.linspace(0, duration_sec, int(duration_sec * sample_rate), endpoint=False)
    
    # 创建基本语音信号 - 使用多个频率模拟人声特征
    # 人声的基频通常在85-255Hz之间
    f0 = 120.0  # 基频 (Hz)
    
    # 创建基本信号
    signal = 0.5 * np.sin(2 * np.pi * f0 * t)
    
    # 添加谐波以模拟真实语音
    signal += 0.3 * np.sin(2 * np.pi * (2*f0) * t)  # 第一谐波
    signal += 0.15 * np.sin(2 * np.pi * (3*f0) * t) # 第二谐波
    signal += 0.05 * np.sin(2 * np.pi * (4*f0) * t) # 第三谐波
    
    # 添加振幅调制以模拟语音的音节节奏
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)  # 3Hz的振幅调制
    signal = signal * am
    
    # 应用渐入渐出效果
    fade_samples = int(0.05 * sample_rate)  # 50ms的淡入淡出
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    
    signal[:fade_samples] *= fade_in
    signal[-fade_samples:] *= fade_out
    
    # 归一化到 16 位整数范围 (-32768 到 32767)
    signal = signal / np.max(np.abs(signal)) * 0.9  # 留一些余量防止削波
    signal = (signal * 32767).astype(np.int16)
    
    return signal

def save_wav(signal, filename, sample_rate, channels, sample_width):
    """将信号保存为WAV文件"""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(signal.tobytes())

def main():
    # 生成语音信号
    speech_signal = generate_speech_signal(DURATION_SEC, SAMPLE_RATE)
    
    # 保存路径
    output_path = pathlib.Path(__file__).parent / "speech.wav"
    
    # 保存为WAV文件
    save_wav(speech_signal, str(output_path), SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH)
    
    # 计算文件大小和样本数
    num_samples = len(speech_signal)
    file_size = output_path.stat().st_size
    
    print(f"已生成语音音频文件: {output_path}")
    print(f"文件规格:")
    print(f"- 采样率: {SAMPLE_RATE} Hz")
    print(f"- 通道数: {CHANNELS} (单声道)")
    print(f"- 位深度: {SAMPLE_WIDTH*8} 位")
    print(f"- 持续时间: {DURATION_SEC} 秒")
    print(f"- 样本数: {num_samples}")
    print(f"- 文件大小: {file_size} 字节")

if __name__ == "__main__":
    main() 