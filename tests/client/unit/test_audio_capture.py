"""
音频捕获器单元测试。

本模块测试nextalk_client.audio.capture模块的AudioCapturer类的功能。
使用mock库模拟PyAudio，避免对实际硬件的依赖。
"""

import pytest
from unittest import mock
import pyaudio
import threading
import time

from nextalk_client.audio.capture import AudioCapturer
from nextalk_shared.constants import (
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SIZE,
    AUDIO_SAMPLE_RATE,
)


@pytest.fixture
def mock_pyaudio():
    """创建一个模拟的PyAudio对象。"""
    with mock.patch("pyaudio.PyAudio") as mock_pa:
        # 模拟PyAudio实例
        mock_pa_instance = mock.MagicMock()
        mock_pa.return_value = mock_pa_instance

        # 模拟流对象
        mock_stream = mock.MagicMock()
        # 设置open方法返回模拟的流
        mock_pa_instance.open.return_value = mock_stream

        # 配置设备信息方法
        mock_pa_instance.get_device_count.return_value = 2

        def get_device_info_side_effect(index):
            if index == 0:
                return {"maxInputChannels": 2, "name": "Default Input Device"}
            else:
                return {"maxInputChannels": 0, "name": "Output Only Device"}

        mock_pa_instance.get_device_info_by_index.side_effect = get_device_info_side_effect

        yield mock_pa


@pytest.fixture
def audio_capturer():
    """创建AudioCapturer实例。"""
    with mock.patch("pyaudio.PyAudio"):  # 防止实际创建PyAudio实例
        capturer = AudioCapturer()
        yield capturer
        # 测试后清理
        capturer._cleanup()


def test_initialization(audio_capturer):
    """测试AudioCapturer初始化。"""
    assert audio_capturer._py_audio is None
    assert audio_capturer._stream is None
    assert audio_capturer._is_capturing is False
    assert audio_capturer._callback_fn is None
    assert audio_capturer._device_index is None


def test_list_devices(audio_capturer, mock_pyaudio):
    """测试列出设备功能。"""
    devices = audio_capturer.list_devices()

    # 验证PyAudio被正确初始化
    assert mock_pyaudio.called
    # 验证获取设备数量被调用
    assert mock_pyaudio.return_value.get_device_count.called
    # 验证返回的设备列表
    assert len(devices) == 1  # 只有一个输入设备
    assert devices[0]["index"] == 0
    assert devices[0]["name"] == "Default Input Device"


def test_select_device_success(audio_capturer, mock_pyaudio):
    """测试成功选择设备。"""
    result = audio_capturer.select_device(0)

    assert result is True
    assert audio_capturer._device_index == 0
    assert mock_pyaudio.return_value.get_device_info_by_index.called_with(0)


def test_select_device_failure(audio_capturer, mock_pyaudio):
    """测试选择无效设备。"""
    result = audio_capturer.select_device(1)  # 这是一个输出设备

    assert result is False
    assert audio_capturer._device_index is None


def test_start_stream(audio_capturer, mock_pyaudio):
    """测试启动音频流。"""
    callback_mock = mock.Mock()

    result = audio_capturer.start_stream(callback_mock)

    assert result is True
    assert audio_capturer._is_capturing is True
    assert audio_capturer._callback_fn == callback_mock

    # 验证PyAudio方法被正确调用
    mock_pa_instance = mock_pyaudio.return_value
    assert mock_pa_instance.open.called

    # 验证open方法的参数
    args, kwargs = mock_pa_instance.open.call_args
    assert kwargs["format"] == pyaudio.paInt16
    assert kwargs["channels"] == AUDIO_CHANNELS
    assert kwargs["rate"] == AUDIO_SAMPLE_RATE
    assert kwargs["input"] is True
    assert kwargs["frames_per_buffer"] == AUDIO_CHUNK_SIZE
    assert "stream_callback" in kwargs

    # 验证流启动
    mock_stream = mock_pa_instance.open.return_value
    assert mock_stream.start_stream.called


def test_start_stream_already_running(audio_capturer):
    """测试在流已经运行时启动流。"""
    # 设置状态为已经在捕获
    audio_capturer._is_capturing = True

    result = audio_capturer.start_stream(mock.Mock())

    assert result is False  # 启动应当失败


def test_stop_stream(audio_capturer, mock_pyaudio):
    """测试停止音频流。"""
    # 设置初始状态
    mock_stream = mock_pyaudio.return_value.open.return_value
    mock_stream.is_active.return_value = True

    # 先启动流
    audio_capturer.start_stream(mock.Mock())

    # 现在停止流
    result = audio_capturer.stop_stream()

    assert result is True
    assert audio_capturer._is_capturing is False
    assert audio_capturer._stream is None
    assert audio_capturer._py_audio is None

    # 验证流被正确停止和关闭
    assert mock_stream.stop_stream.called
    assert mock_stream.close.called
    assert mock_pyaudio.return_value.terminate.called


def test_stop_stream_not_running(audio_capturer):
    """测试在流未运行时停止流。"""
    # 初始状态：未捕获
    assert audio_capturer._is_capturing is False

    result = audio_capturer.stop_stream()

    assert result is False  # 停止应当失败


def test_audio_callback(audio_capturer):
    """测试音频回调函数。"""
    # 模拟回调函数
    callback_mock = mock.Mock()
    audio_capturer._callback_fn = callback_mock
    audio_capturer._is_capturing = True

    # 模拟音频数据
    test_data = b"test_audio_data"
    frame_count = 1024
    time_info = {}
    status = 0

    # 调用回调函数
    result = audio_capturer._audio_callback(test_data, frame_count, time_info, status)

    # 验证用户回调被调用，且参数正确
    callback_mock.assert_called_once_with(test_data)
    # 验证返回值正确
    assert result == (None, pyaudio.paContinue)


def test_audio_callback_exception(audio_capturer):
    """测试音频回调函数发生异常的情况。"""
    # 模拟会抛出异常的回调函数
    callback_mock = mock.Mock(side_effect=Exception("测试异常"))
    audio_capturer._callback_fn = callback_mock
    audio_capturer._is_capturing = True

    # 调用回调函数
    result = audio_capturer._audio_callback(b"test", 1024, {}, 0)

    # 即使发生异常，回调也应继续
    assert result == (None, pyaudio.paContinue)


def test_stream_callback_integration(audio_capturer, mock_pyaudio):
    """测试流回调的集成。"""
    # 模拟回调函数
    callback_mock = mock.Mock()

    # 启动流
    audio_capturer.start_stream(callback_mock)

    # 获取传递给PyAudio.open的回调函数
    stream_callback = mock_pyaudio.return_value.open.call_args[1]["stream_callback"]

    # 模拟PyAudio调用回调函数
    test_data = b"test_audio_data"
    stream_callback(test_data, 1024, {}, 0)

    # 验证用户回调被调用
    callback_mock.assert_called_once_with(test_data)


def test_is_capturing(audio_capturer):
    """测试is_capturing方法。"""
    assert audio_capturer.is_capturing() is False

    audio_capturer._is_capturing = True
    assert audio_capturer.is_capturing() is True


def test_cleanup(audio_capturer, mock_pyaudio):
    """测试资源清理。"""
    # 设置初始状态
    mock_stream = mock_pyaudio.return_value.open.return_value
    mock_stream.is_active.return_value = True

    # 先启动流
    audio_capturer.start_stream(mock.Mock())

    # 手动调用清理
    audio_capturer._cleanup()

    assert audio_capturer._is_capturing is False
    assert audio_capturer._stream is None
    assert audio_capturer._py_audio is None

    # 验证资源被正确释放
    assert mock_stream.stop_stream.called
    assert mock_stream.close.called
    assert mock_pyaudio.return_value.terminate.called


def test_cleanup_exception_handling(audio_capturer, mock_pyaudio):
    """测试清理过程中的异常处理。"""
    # 设置初始状态
    mock_stream = mock_pyaudio.return_value.open.return_value
    mock_stream.is_active.return_value = True
    # 让stop_stream抛出异常
    mock_stream.stop_stream.side_effect = Exception("测试异常")

    # 启动流
    audio_capturer.start_stream(mock.Mock())

    # 即使抛出异常，清理也应正常完成
    audio_capturer._cleanup()

    assert audio_capturer._is_capturing is False
    assert audio_capturer._stream is None
    assert audio_capturer._py_audio is None
