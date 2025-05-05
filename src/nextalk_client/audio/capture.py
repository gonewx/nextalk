"""
音频捕获模块 - 已简化版本。

此模块使用PyAudio库实现实时音频捕获功能，将捕获的音频数据传递给回调函数。
基于FunASR客户端示例简化实现，确保兼容性和稳定性。
"""

import ctypes
import os
import logging
import threading
import time
from typing import Callable, Optional, List

import numpy as np
import pyaudio

from nextalk_shared.constants import (
    AUDIO_CHANNELS,
    AUDIO_SAMPLE_RATE,
    AUDIO_FALLBACK_SAMPLE_RATES,
    AUDIO_FRAME_DURATION_MS,
    FUNASR_DEFAULT_CHUNK_SIZE,
    FUNASR_DEFAULT_CHUNK_INTERVAL,
)


# 抑制ALSA错误信息
# 创建一个错误处理函数来捕获错误信息
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass  # 什么都不做，即忽略错误信息

# 加载ALSA库
try:
    asound = ctypes.cdll.LoadLibrary('libasound.so')
    # 设置错误处理函数
    c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
    asound.snd_lib_error_set_handler(c_error_handler)
except:
    # 如果加载失败，则使用环境变量抑制ALSA错误
    os.environ['ALSA_DEBUG_LEVEL'] = '0'

# 配置日志记录器
logger = logging.getLogger(__name__)

class AudioCapturer:
    """
    音频捕获器，负责从麦克风捕获音频数据并通过回调函数传递。
    
    基于FunASR客户端示例进行简化实现，更直接地处理音频数据。
    """

    def __init__(self):
        """初始化音频捕获器。"""
        self.logger = logging.getLogger(__name__)
        self._py_audio = None
        self._stream = None
        self._is_capturing = False
        self._lock = threading.Lock()
        self._callback_fn = None
        self._device_index = None
        self._frame_counter = 0
        
        # FunASR兼容配置
        self.chunk_size = FUNASR_DEFAULT_CHUNK_SIZE  # [5, 10, 5] 对应600ms
        self.chunk_interval = FUNASR_DEFAULT_CHUNK_INTERVAL  # 默认为10，即60ms一块
        
        self.logger.info("音频捕获器已初始化，使用默认设置")

    def list_devices(self) -> list[dict]:
        """
        列出可用的音频输入设备。

        Returns:
            list[dict]: 可用音频设备列表，包含设备索引和名称。
        """
        if self._py_audio is None:
            self._py_audio = pyaudio.PyAudio()

        devices = []
        for i in range(self._py_audio.get_device_count()):
            device_info = self._py_audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                devices.append({
                    'index': i,
                    'name': device_info.get('name', f'设备 {i}'),
                })
        
        return devices

    def select_device(self, device_index: int) -> bool:
        """
        选择要使用的音频输入设备。

        Args:
            device_index: 设备索引。

        Returns:
            bool: 设备选择是否成功。
        """
        global AUDIO_SAMPLE_RATE  # 提前声明全局变量
        
        if self._is_capturing:
            self.logger.warning("无法在捕获过程中更改设备，请先停止捕获")
            return False

        if self._py_audio is None:
            self._py_audio = pyaudio.PyAudio()

        try:
            device_info = self._py_audio.get_device_info_by_index(device_index)
            if device_info.get('maxInputChannels') <= 0:
                self.logger.error(f"设备 {device_index} 不支持音频输入")
                return False
            
            self._device_index = device_index
            
            # 获取设备支持的采样率
            supported_rates = self.get_supported_sample_rates(device_index)
            
            # 检查当前采样率是否被支持
            original_rate = AUDIO_SAMPLE_RATE
            
            if original_rate not in supported_rates:
                # 找到最接近的支持采样率
                closest_rate = min(supported_rates, key=lambda x: abs(x - original_rate))
                self.logger.warning(f"采样率 {original_rate} 不支持，自动切换到 {closest_rate}")
                AUDIO_SAMPLE_RATE = closest_rate
            
            self.logger.info(f"已选择音频设备: {device_info.get('name')}")
            return True
        except Exception as e:
            self.logger.error(f"选择音频设备失败: {e}")
            return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio回调函数，简化版
        
        Args:
            in_data: 输入音频数据
            frame_count: 帧数
            time_info: 时间信息
            status: 状态
            
        Returns:
            音频数据和状态
        """
        # 增加帧计数
        self._frame_counter += 1
        
        # 检查输入数据是否存在及不为空
        if in_data is None or len(in_data) == 0:
            self.logger.warning("收到空音频数据，跳过处理")
            return None, pyaudio.paContinue
            
        # 如果设置了回调函数，调用回调处理
        try:
            if self._callback_fn:
                self._callback_fn(in_data)
        except Exception as e:
            self.logger.error(f"音频回调处理时出错: {str(e)}")
            
        return in_data, pyaudio.paContinue

    def configure_funasr_params(self, chunk_size: List[int] = None, chunk_interval: int = None):
        """
        配置FunASR相关参数。
        
        Args:
            chunk_size: 分块大小，如 [5, 10, 5] 对应600ms
            chunk_interval: 分块间隔
        """
        if chunk_size:
            self.chunk_size = chunk_size
            self.logger.info(f"已设置FunASR分块大小: {chunk_size}")
        
        if chunk_interval:
            self.chunk_interval = chunk_interval
            self.logger.info(f"已设置FunASR分块间隔: {chunk_interval}")

    def start_stream(self, callback: Callable[[bytes], None]) -> bool:
        """
        开始音频捕获流 - 使用FunASR兼容配置。

        Args:
            callback: 回调函数，当有新的音频数据时调用，参数为音频数据字节。

        Returns:
            bool: 是否成功启动流。
        """
        with self._lock:
            if self._is_capturing:
                self.logger.warning("音频流已经在运行中")
                return False

            self._callback_fn = callback
            self._frame_counter = 0

            try:
                if self._py_audio is None:
                    self._py_audio = pyaudio.PyAudio()
                
                # 根据FunASR参数计算帧大小
                # 参考funasr_wss_client.py的实现
                global AUDIO_SAMPLE_RATE  # 提前声明全局变量
                chunk_ms = 60 * self.chunk_size[1] / self.chunk_interval
                frames_per_buffer = int(AUDIO_SAMPLE_RATE / 1000 * chunk_ms)
                
                self.logger.info(f"帧大小: {frames_per_buffer}样本, 对应约{chunk_ms}ms")
                
                # 打开音频流 - 添加错误处理和重试
                max_retries = 3
                retry_count = 0
                last_error = None
                
                while retry_count < max_retries:
                    try:
                        # 尝试打开音频流
                        self._stream = self._py_audio.open(
                            format=pyaudio.paInt16,
                            channels=AUDIO_CHANNELS,
                            rate=AUDIO_SAMPLE_RATE,
                            input=True,
                            frames_per_buffer=frames_per_buffer,
                            input_device_index=self._device_index,
                            stream_callback=self._audio_callback
                        )
                        
                        # 启动流
                        self._stream.start_stream()
                        self._is_capturing = True
                        self.logger.info("音频流已启动")
                        return True
                    
                    except ValueError as e:
                        # 处理采样率错误
                        if "Invalid sample rate" in str(e) and retry_count < max_retries - 1:
                            # 尝试使用标准采样率
                            standard_rates = AUDIO_FALLBACK_SAMPLE_RATES
                            
                            # 找到最接近的支持采样率
                            closest_rate = min(standard_rates, key=lambda x: abs(x - AUDIO_SAMPLE_RATE))
                            self.logger.warning(f"采样率 {AUDIO_SAMPLE_RATE} 不支持，尝试使用 {closest_rate}")
                            
                            # 临时替换采样率
                            AUDIO_SAMPLE_RATE = closest_rate
                            
                            # 重新计算帧大小
                            frames_per_buffer = int(AUDIO_SAMPLE_RATE / 1000 * chunk_ms)
                            
                            retry_count += 1
                            last_error = e
                        else:
                            raise e
                    
                    except Exception as e:
                        retry_count += 1
                        last_error = e
                        self.logger.warning(f"尝试启动音频流失败 (尝试 {retry_count}/{max_retries}): {e}")
                        
                        if retry_count >= max_retries:
                            break
                        
                        # 等待一小段时间再重试
                        time.sleep(0.5)
                
                # 所有重试都失败
                if last_error:
                    self.logger.error(f"启动音频流失败: {last_error}")
                self._cleanup()
                return False
                
            except Exception as e:
                self.logger.error(f"启动音频流失败: {e}")
                self._cleanup()
                return False

    def stop_stream(self) -> bool:
        """
        停止音频捕获流。

        Returns:
            bool: 是否成功停止流。
        """
        with self._lock:
            if not self._is_capturing:
                self.logger.warning("音频流未运行")
                return True  # 返回True因为没有正在运行的流，已经是期望的停止状态

            try:
                # 标记当前正在停止中
                self._stopping_stream = True
                
                # 增加停止前的状态记录
                if self._stream:
                    is_active = self._stream.is_active()
                    self.logger.info(f"开始停止音频流，当前状态: 活动={is_active}")
                else:
                    self.logger.info("开始停止音频流，但流对象不存在")
                    self._is_capturing = False
                    return True
                    
                # 先停止回调
                self._callback_fn = None
                
                # 停止并关闭流
                if self._stream:
                    if self._stream.is_active():
                        self.logger.debug("正在停止活动的音频流")
                        self._stream.stop_stream()
                    
                    self.logger.debug("正在关闭音频流")
                    self._stream.close()
                    self._stream = None
                
                # 重置标志
                self._is_capturing = False
                self._stopping_stream = False
                
                self.logger.info("音频流已停止")
                return True
                
            except Exception as e:
                self.logger.error(f"停止音频流失败: {e}")
                
                # 发生异常时尝试进行彻底清理
                try:
                    # 强制清理，即使出错也确保资源被释放
                    self._is_capturing = False
                    self._stopping_stream = False
                    self._cleanup()
                    self.logger.info("尽管出错，已强制清理音频资源")
                except Exception as cleanup_e:
                    self.logger.error(f"清理音频资源时再次出错: {cleanup_e}")
                    
                return False
            finally:
                # 确保在任何情况下都进行清理
                self._cleanup()

    def _cleanup(self):
        """清理资源，确保无论发生什么情况，资源都能被释放"""
        try:
            # 检查是否有流实例并且是否活动
            if self._stream:
                try:
                    if self._stream.is_active():
                        self.logger.debug("清理过程中停止活动的音频流")
                        self._stream.stop_stream()
                    self.logger.debug("清理过程中关闭音频流")
                    self._stream.close()
                except Exception as e:
                    self.logger.error(f"清理音频流时出错: {e}")
                finally:
                    self._stream = None
                    
            # 检查PyAudio实例是否存在
            if self._py_audio:
                try:
                    self.logger.debug("终止PyAudio实例")
                    self._py_audio.terminate()
                except Exception as e:
                    self.logger.error(f"终止PyAudio实例时出错: {e}")
                finally:
                    self._py_audio = None
                    
            # 重置捕获状态和回调
            was_capturing = self._is_capturing
            self._is_capturing = False
            self._callback_fn = None
            if hasattr(self, '_stopping_stream'):
                self._stopping_stream = False
            
            if was_capturing:
                self.logger.info("音频资源已完全清理，捕获状态重置")
            else:
                self.logger.debug("音频资源已清理")
            
        except Exception as e:
            self.logger.error(f"清理音频资源时出错: {e}")
            # 确保即使在错误情况下也会重置状态
            self._is_capturing = False
            self._stream = None
            self._py_audio = None
            self._callback_fn = None
            if hasattr(self, '_stopping_stream'):
                self._stopping_stream = False

    def is_capturing(self) -> bool:
        """
        检查是否正在捕获音频。

        Returns:
            bool: 如果正在捕获则返回True，否则返回False。
        """
        return self._is_capturing

    def __del__(self):
        """析构函数，确保资源被释放"""
        self._cleanup()

    def get_supported_sample_rates(self, device_index: int) -> List[int]:
        """
        获取特定设备支持的采样率。
        
        Args:
            device_index: 设备索引
            
        Returns:
            支持的采样率列表，如果获取失败则返回备用采样率列表
        """
        if self._py_audio is None:
            self._py_audio = pyaudio.PyAudio()
            
        try:
            # 获取设备信息
            device_info = self._py_audio.get_device_info_by_index(device_index)
            
            # 尝试获取支持的采样率
            supported_rates = []
            for rate in AUDIO_FALLBACK_SAMPLE_RATES:
                try:
                    if self._py_audio.is_format_supported(
                        rate,
                        input_device=device_index,
                        input_channels=AUDIO_CHANNELS,
                        input_format=pyaudio.paInt16
                    ):
                        supported_rates.append(rate)
                except:
                    # 如果不支持，忽略错误
                    pass
                    
            if supported_rates:
                self.logger.info(f"设备 {device_index} 支持的采样率: {supported_rates}")
                return supported_rates
            else:
                self.logger.warning(f"无法确定设备 {device_index} 支持的采样率，使用备用列表")
                return AUDIO_FALLBACK_SAMPLE_RATES
                
        except Exception as e:
            self.logger.error(f"获取设备支持的采样率时出错: {e}")
            return AUDIO_FALLBACK_SAMPLE_RATES 