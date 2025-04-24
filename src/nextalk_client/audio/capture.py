"""
音频捕获模块。

此模块使用PyAudio库实现实时音频捕获功能，将捕获的音频数据传递给回调函数。
"""

import logging
import threading
import time
import os
from typing import Callable, Optional

import numpy as np
import pyaudio

from nextalk_shared.constants import (
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SIZE,
    AUDIO_SAMPLE_RATE,
    AUDIO_FRAME_DURATION_MS,
)


class AudioCapturer:
    """音频捕获器，负责从麦克风捕获音频数据并通过回调函数传递。"""

    def __init__(self, audio_backend: str = None):
        """初始化音频捕获器。
        
        Args:
            audio_backend: 音频后端('alsa', 'pulse', 'oss')，如为None则使用系统默认值
        """
        self.logger = logging.getLogger(__name__)
        self._py_audio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_capturing = False
        self._lock = threading.Lock()
        self._callback_fn = None
        self._device_index = None
        
        # 设置音频后端
        self._set_audio_backend(audio_backend)

    def _set_audio_backend(self, backend: str = None):
        """设置PyAudio使用的音频后端。
        
        Args:
            backend: 音频后端名称，可选值为'alsa', 'pulse', 'oss'等
        """
        if backend:
            # 设置环境变量以影响PyAudio的行为
            backend = backend.lower()
            self.logger.info(f"设置音频后端为: {backend}")
            if backend == 'pulse':
                # 修改PulseAudio环境变量，使用系统默认音频设备
                # 注意: PULSE_SOURCE应该设置为实际存在的音频输入设备
                os.environ['PULSE_SINK'] = 'auto_null'
                os.environ['PULSE_SOURCE'] = 'alsa_input.usb-Web_Camera_Web_Camera_202404120005-02.mono-fallback'
                # 记录设置的环境变量，便于调试
                self.logger.debug(f"PulseAudio设置 - PULSE_SOURCE: {os.environ['PULSE_SOURCE']}")
            elif backend == 'alsa':
                os.environ['ALSA_PCM_CARD'] = 'default'
            elif backend == 'oss':
                os.environ['OSS_AUDIODEV'] = '/dev/dsp'
            
            # 通过设置索引排序方式来确定优先使用的音频后端
            backend_order = ""
            if backend == 'pulse':
                backend_order = 'pulse,alsa,oss,jack,coreaudio,mme,directsound,wdmks,wasapi'
            elif backend == 'alsa':
                backend_order = 'alsa,pulse,oss,jack,coreaudio,mme,directsound,wdmks,wasapi'
            elif backend == 'oss':
                backend_order = 'oss,pulse,alsa,jack,coreaudio,mme,directsound,wdmks,wasapi'
            
            if backend_order:
                os.environ['PYAUDIO_BACKEND_ORDER'] = backend_order

    def list_devices(self) -> list[dict]:
        """列出可用的音频输入设备。

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
        """选择要使用的音频输入设备。

        Args:
            device_index: 设备索引。

        Returns:
            bool: 设备选择是否成功。
        """
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
            self.logger.info(f"已选择音频设备: {device_info.get('name')}")
            return True
        except Exception as e:
            self.logger.error(f"选择音频设备失败: {e}")
            return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio回调函数，当有新的音频数据可用时调用。

        注意：这个方法由PyAudio内部线程调用，不应该包含阻塞操作。

        Args:
            in_data: 输入音频数据。
            frame_count: 帧数。
            time_info: 时间信息。
            status: 状态标志。

        Returns:
            tuple: (None, pyaudio.paContinue) 表示继续流。
        """
        if status:
            self.logger.debug(f"PyAudio状态: {status}")

        if self._is_capturing and self._callback_fn:
            try:
                # 将数据传递给用户回调函数
                self._callback_fn(in_data)
            except Exception as e:
                self.logger.error(f"音频回调处理出错: {e}")

        return None, pyaudio.paContinue

    def start_stream(self, callback: Callable[[bytes], None]) -> bool:
        """开始音频捕获流。

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

            try:
                if self._py_audio is None:
                    self._py_audio = pyaudio.PyAudio()

                self._stream = self._py_audio.open(
                    format=pyaudio.paInt16,
                    channels=AUDIO_CHANNELS,
                    rate=AUDIO_SAMPLE_RATE,
                    input=True,
                    output=False,
                    frames_per_buffer=AUDIO_CHUNK_SIZE,
                    stream_callback=self._audio_callback,
                    input_device_index=self._device_index,
                )

                self._stream.start_stream()
                self._is_capturing = True
                self.logger.info(
                    f"音频捕获已启动: 采样率={AUDIO_SAMPLE_RATE}Hz, "
                    f"通道数={AUDIO_CHANNELS}, 帧大小={AUDIO_CHUNK_SIZE}, "
                    f"帧时长={AUDIO_FRAME_DURATION_MS}ms"
                )
                return True
            except Exception as e:
                self.logger.error(f"启动音频流失败: {e}")
                self._cleanup()
                return False

    def stop_stream(self) -> bool:
        """停止音频捕获流。

        Returns:
            bool: 是否成功停止流。
        """
        with self._lock:
            if not self._is_capturing:
                self.logger.warning("音频流未在运行")
                return False

            try:
                self._cleanup()
                self.logger.info("音频捕获已停止")
                return True
            except Exception as e:
                self.logger.error(f"停止音频流失败: {e}")
                return False

    def _cleanup(self):
        """清理资源。"""
        self._is_capturing = False
        
        if self._stream is not None:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                self.logger.error(f"关闭音频流时出错: {e}")
            finally:
                self._stream = None

        if self._py_audio is not None:
            try:
                self._py_audio.terminate()
            except Exception as e:
                self.logger.error(f"终止PyAudio时出错: {e}")
            finally:
                self._py_audio = None

    def is_capturing(self) -> bool:
        """检查是否正在捕获音频。

        Returns:
            bool: 是否正在捕获音频。
        """
        return self._is_capturing

    def __del__(self):
        """析构函数，确保资源被释放。"""
        self._cleanup() 