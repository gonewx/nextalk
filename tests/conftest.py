"""
Pytest configuration and shared fixtures for NexTalk tests.

Provides common test fixtures and configuration for the entire test suite.
"""

import pytest
import logging
import tempfile
import shutil
import asyncio
import signal
import sys
import warnings
from pathlib import Path
from unittest.mock import Mock

# 配置警告过滤
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*was never awaited.*")

from nextalk.config.models import (
    AudioConfig, 
    ServerConfig, 
    RecordingConfig,
    UIConfig,
    TextInjectionConfig,
    RecognitionConfig,
    LoggingConfig,
    NexTalkConfig
)


# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy loggers during testing
logging.getLogger('sounddevice').setLevel(logging.WARNING)


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config_dir(temp_dir):
    """Create a temporary configuration directory."""
    config_dir = Path(temp_dir) / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def default_audio_config():
    """Create default audio configuration for testing."""
    return AudioConfig(
        sample_rate=16000,
        channels=1,
        device_id=None,
        device_name=None,
        input_buffer_size=1024,
        noise_suppression=False,
        auto_gain_control=False
    )


@pytest.fixture
def default_server_config():
    """Create default server configuration for testing."""
    return ServerConfig(
        host="localhost",
        port=10095,
        use_ssl=False,  # Simplified for testing
        ssl_verify=False,
        timeout=5.0,
        reconnect_attempts=1,
        reconnect_interval=1.0
    )


@pytest.fixture
def default_hotkey_config():
    """Create default hotkey configuration for testing."""
    return RecordingConfig(
        mode="toggle",
        hotkey="ctrl+alt+space",
        stop_key="ctrl+alt+space",
        conflict_detection=False,  # Simplified for testing
        enable_sound_feedback=False
    )


@pytest.fixture
def default_ui_config():
    """Create default UI configuration for testing."""
    return UIConfig(
        show_tray_icon=False,  # Simplified for testing
        auto_start=False,
        minimize_to_tray=False,
        show_notifications=False,
        notification_duration=1.0,
        tray_icon_theme="auto",
        language="zh_CN"
    )


@pytest.fixture
def default_text_injection_config():
    """Create default text injection configuration for testing."""
    return TextInjectionConfig(
        auto_inject=True,
        fallback_enabled=True,
        inject_delay=0.01,  # Very short for testing
        cursor_positioning="end",
        format_text=False,  # Simplified for testing
        strip_whitespace=True
    )


@pytest.fixture
def default_recognition_config():
    """Create default recognition configuration for testing."""
    return RecognitionConfig(
        mode="2pass",
        use_itn=True,
        use_punctuation=True,
        hotwords=[],
        hotword_file=None,
        words_max_print=1000,
        output_dir=None,
        language_model="zh-cn"
    )


@pytest.fixture
def default_logging_config():
    """Create default logging configuration for testing."""
    return LoggingConfig(
        level="DEBUG",
        file_path=None,
        max_file_size=1024*1024,  # 1MB
        backup_count=1,
        console_output=False,  # Reduce noise in tests
        format="%(name)s - %(levelname)s - %(message)s"
    )


@pytest.fixture
def default_nextalk_config(
    default_audio_config,
    default_server_config, 
    default_hotkey_config,
    default_ui_config,
    default_text_injection_config,
    default_recognition_config,
    default_logging_config,
    test_config_dir
):
    """Create complete default NexTalk configuration for testing."""
    return NexTalkConfig(
        server=default_server_config,
        audio=default_audio_config,
        recording=default_hotkey_config,
        ui=default_ui_config,
        text_injection=default_text_injection_config,
        recognition=default_recognition_config,
        logging=default_logging_config,
        version="0.1.0",
        config_version="1.0",
        user_data_dir=str(test_config_dir)
    )


@pytest.fixture
def mock_audio_device():
    """Create a mock audio device for testing."""
    from nextalk.audio.device import AudioDevice
    return AudioDevice(
        device_id=0,
        device_name="Test Microphone",
        channels=1,
        default_sample_rate=16000.0,
        max_input_channels=1,
        max_output_channels=0,
        is_default=True,
        is_available=True
    )


@pytest.fixture
def mock_audio_devices():
    """Create a list of mock audio devices for testing."""
    from nextalk.audio.device import AudioDevice
    return [
        AudioDevice(
            device_id=0,
            device_name="Built-in Microphone",
            channels=1,
            default_sample_rate=44100.0,
            max_input_channels=1,
            max_output_channels=0,
            is_default=True,
            is_available=True
        ),
        AudioDevice(
            device_id=1,
            device_name="USB Headset Microphone",
            channels=1,
            default_sample_rate=16000.0,
            max_input_channels=1,
            max_output_channels=0,
            is_default=False,
            is_available=True
        ),
        AudioDevice(
            device_id=2,
            device_name="Bluetooth Microphone",
            channels=2,
            default_sample_rate=48000.0,
            max_input_channels=2,
            max_output_channels=0,
            is_default=False,
            is_available=False  # Unavailable device
        )
    ]


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", 
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers",
        "hardware: marks tests that require actual hardware"
    )


# Pytest options
def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )
    parser.addoption(
        "--run-hardware",
        action="store_true", 
        default=False,
        help="run tests that require hardware"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
    
    if not config.getoption("--run-hardware"):
        skip_hardware = pytest.mark.skip(reason="need --run-hardware option to run")
        for item in items:
            if "hardware" in item.keywords:
                item.add_marker(skip_hardware)


# Async test support
@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for async tests with enhanced cleanup."""
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        yield loop
    finally:
        # 强化的异步任务清理
        try:
            # 获取所有未完成的任务
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.debug(f"清理 {len(pending)} 个未完成的异步任务")
                
                # 取消所有任务
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                # 等待任务完成（有超时保护）
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=3.0
                        )
                    )
                except asyncio.TimeoutError:
                    logger.warning("异步任务清理超时，强制继续")
                except Exception as e:
                    logger.debug(f"任务清理过程中的异常: {e}")
        except Exception as e:
            logger.debug(f"事件循环清理异常: {e}")
        finally:
            # 确保循环被关闭
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception as e:
                logger.debug(f"关闭事件循环异常: {e}")

# 测试钩子 - 防止测试僵死
def pytest_configure(config):
    """配置 pytest 运行时设置."""
    # 设置严格的信号处理
    import signal
    import sys
    import os
    import threading
    
    # 全局超时保护（15分钟）
    global_timeout = 900  # 15分钟
    
    def global_timeout_handler():
        print(f"\\n💀 全局测试超时 ({global_timeout}秒)，强制终止进程", file=sys.stderr)
        os._exit(124)  # 强制退出，不触发清理
    
    global_timer = threading.Timer(global_timeout, global_timeout_handler)
    global_timer.daemon = True
    global_timer.start()
    
    def timeout_handler(signum, frame):
        print("\\n⚠️ 测试进程超时，强制退出", file=sys.stderr)
        # 尝试清理当前事件循环
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                if not task.done():
                    task.cancel()
        except Exception:
            pass
        sys.exit(124)
    
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)


def pytest_runtest_setup(item):
    """测试设置阶段的钩子."""
    import signal
    import threading
    import sys
    import os
    
    # 为每个测试设置超时保护
    if hasattr(item, "get_closest_marker"):
        timeout_marker = item.get_closest_marker("timeout")
        if timeout_marker:
            timeout = timeout_marker.args[0] if timeout_marker.args else 30
        else:
            timeout = 20  # 增加默认超时到20秒
    else:
        timeout = 20
    
    # 使用线程定时器作为备用超时机制
    def thread_timeout_handler():
        print(f"\\n💀 测试 {item.name} 线程超时 ({timeout}秒)，强制退出", file=sys.stderr)
        os._exit(125)  # 使用不同的退出码
    
    timer = threading.Timer(timeout + 5, thread_timeout_handler)  # 比信号超时稍长
    timer.daemon = True
    timer.start()
    
    # 存储定时器引用以便清理
    item._timeout_timer = timer
    
    # 信号超时
    if hasattr(signal, 'SIGALRM'):
        signal.alarm(timeout)


def pytest_runtest_teardown(item):
    """测试清理阶段的钩子."""
    import signal
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 取消信号超时
    if hasattr(signal, 'SIGALRM'):
        signal.alarm(0)
    
    # 取消线程定时器
    if hasattr(item, '_timeout_timer'):
        item._timeout_timer.cancel()
    
    # 强化的异步资源清理
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            # 获取所有任务
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.debug(f"测试 {item.name} 清理 {len(pending)} 个异步任务")
                
                # 取消所有任务
                for task in pending:
                    if not task.done():
                        task.cancel()
                
                # 强制完成清理（短超时）
                try:
                    if loop.is_running():
                        # 如果循环还在运行，我们不能在这里等待
                        pass
                    else:
                        loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending, return_exceptions=True),
                                timeout=1.0
                            )
                        )
                except Exception as e:
                    logger.debug(f"异步清理异常: {e}")
    except Exception as e:
        logger.debug(f"事件循环清理异常: {e}")


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束的钩子."""
    import signal
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("测试会话结束，最终清理")
    
    # 确保取消所有超时
    if hasattr(signal, 'SIGALRM'):
        signal.alarm(0)

