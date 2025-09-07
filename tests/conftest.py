"""
Pytest configuration and shared fixtures for NexTalk tests.

Provides common test fixtures and configuration for the entire test suite.
"""

import pytest
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from nextalk.config.models import (
    AudioConfig, 
    ServerConfig, 
    HotkeyConfig,
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
    return HotkeyConfig(
        trigger_key="ctrl+alt+space",
        stop_key="ctrl+alt+space",
        modifier_keys=["ctrl", "alt"],
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
        fallback_to_clipboard=True,
        inject_delay=0.01,  # Very short for testing
        cursor_positioning="end",
        format_text=False,  # Simplified for testing
        strip_whitespace=True,
        compatible_apps=[],
        incompatible_apps=[]
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
        hotkey=default_hotkey_config,
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
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()