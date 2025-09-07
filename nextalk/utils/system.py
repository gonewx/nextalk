"""
System utilities for NexTalk.

Provides system checking and environment setup.
"""

import sys
import os
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


def check_system_requirements() -> bool:
    """
    Check if system meets requirements.
    
    Returns:
        True if all requirements met
    """
    checks = {
        "Python version": check_python_version(),
        "Platform": check_platform(),
        "Audio support": check_audio_support(),
    }
    
    failed = [name for name, result in checks.items() if not result]
    
    if failed:
        logger.error(f"System requirements not met: {', '.join(failed)}")
        return False
    
    logger.info("System requirements check passed")
    return True


def check_python_version() -> bool:
    """
    Check Python version requirement.
    
    Returns:
        True if Python version is sufficient
    """
    min_version = (3, 8)
    current_version = sys.version_info[:2]
    
    if current_version < min_version:
        logger.error(f"Python {min_version[0]}.{min_version[1]}+ required, "
                    f"got {current_version[0]}.{current_version[1]}")
        return False
    
    return True


def check_platform() -> bool:
    """
    Check if platform is supported.
    
    Returns:
        True if platform is supported
    """
    supported_platforms = ["win32", "linux", "darwin"]
    current_platform = sys.platform
    
    if current_platform not in supported_platforms:
        logger.error(f"Platform {current_platform} not supported")
        return False
    
    return True


def check_audio_support() -> bool:
    """
    Check if audio support is available.
    
    Returns:
        True if audio is available
    """
    # Try PyAudio first
    try:
        import pyaudio
        
        # Try to create PyAudio instance
        p = pyaudio.PyAudio()
        
        # Check for input devices
        input_devices = 0
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices += 1
        
        p.terminate()
        
        if input_devices == 0:
            logger.error("No audio input devices found")
            return False
        
        logger.info("Audio support available via PyAudio")
        return True
        
    except ImportError:
        logger.warning("PyAudio not installed, trying sounddevice...")
        
        # Fall back to sounddevice
        try:
            import sounddevice as sd
            
            # Get input devices
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if not input_devices:
                logger.error("No audio input devices found")
                return False
            
            logger.info("Audio support available via sounddevice")
            return True
            
        except ImportError:
            logger.error("Neither PyAudio nor sounddevice installed")
            return False
        except Exception as e:
            logger.error(f"sounddevice check failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Audio check failed: {e}")
        return False


def setup_environment() -> None:
    """Setup application environment."""
    # Create necessary directories
    create_app_directories()
    
    # Setup platform specific settings
    setup_platform_specific()
    
    # Configure environment variables
    configure_environment()
    
    logger.info("Environment setup complete")


def create_app_directories() -> None:
    """Create application directories."""
    # Get app data directory
    app_dir = get_app_data_dir()
    
    # Create subdirectories
    directories = [
        app_dir / "logs",
        app_dir / "cache",
        app_dir / "sessions",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created directory: {directory}")


def get_app_data_dir() -> Path:
    """
    Get application data directory.
    
    Returns:
        Path to app data directory
    """
    if sys.platform == "win32":
        # Windows: %APPDATA%/NexTalk
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        app_dir = Path(base) / "NexTalk"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/NexTalk
        app_dir = Path.home() / "Library" / "Application Support" / "NexTalk"
    else:
        # Linux: ~/.local/share/nextalk
        data_home = os.environ.get("XDG_DATA_HOME", 
                                  os.path.expanduser("~/.local/share"))
        app_dir = Path(data_home) / "nextalk"
    
    return app_dir


def get_config_dir() -> Path:
    """
    Get configuration directory.
    
    Returns:
        Path to config directory
    """
    if sys.platform == "win32":
        # Windows: same as app data
        config_dir = get_app_data_dir()
    elif sys.platform == "darwin":
        # macOS: ~/Library/Preferences/NexTalk
        config_dir = Path.home() / "Library" / "Preferences" / "NexTalk"
    else:
        # Linux: ~/.config/nextalk
        config_home = os.environ.get("XDG_CONFIG_HOME",
                                    os.path.expanduser("~/.config"))
        config_dir = Path(config_home) / "nextalk"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def setup_platform_specific() -> None:
    """Setup platform specific settings."""
    if sys.platform == "win32":
        setup_windows()
    elif sys.platform == "darwin":
        setup_macos()
    else:
        setup_linux()


def setup_windows() -> None:
    """Setup Windows specific settings."""
    # Set DPI awareness for better UI scaling
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    # Enable ANSI color support in terminal
    try:
        from ctypes import windll
        kernel32 = windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass


def setup_macos() -> None:
    """Setup macOS specific settings."""
    # Request accessibility permissions if needed
    # This would require PyObjC or similar
    pass


def setup_linux() -> None:
    """Setup Linux specific settings."""
    # Check for required system libraries
    pass


def configure_environment() -> None:
    """Configure environment variables."""
    # Set default encoding
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    
    # Disable buffering for real-time output
    os.environ.setdefault("PYTHONUNBUFFERED", "1")


def get_system_info() -> Dict[str, Any]:
    """
    Get system information.
    
    Returns:
        Dictionary with system info
    """
    return {
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "platform_machine": platform.machine(),
        "platform_processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def get_audio_devices() -> Dict[str, Any]:
    """
    Get available audio devices.
    
    Returns:
        Dictionary with audio device info
    """
    devices = {
        "input": [],
        "output": []
    }
    
    # Try PyAudio first
    try:
        import pyaudio
        
        p = pyaudio.PyAudio()
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            
            device_info = {
                "index": i,
                "name": info["name"],
                "channels": info["maxInputChannels"],
                "sample_rate": int(info["defaultSampleRate"])
            }
            
            if info["maxInputChannels"] > 0:
                devices["input"].append(device_info)
            
            if info["maxOutputChannels"] > 0:
                device_info["channels"] = info["maxOutputChannels"]
                devices["output"].append(device_info)
        
        p.terminate()
        
    except ImportError:
        # Fall back to sounddevice
        try:
            import sounddevice as sd
            
            for i, device in enumerate(sd.query_devices()):
                device_info = {
                    "index": i,
                    "name": device["name"],
                    "channels": device["max_input_channels"],
                    "sample_rate": int(device["default_samplerate"])
                }
                
                if device["max_input_channels"] > 0:
                    devices["input"].append(device_info)
                
                if device["max_output_channels"] > 0:
                    device_info["channels"] = device["max_output_channels"]
                    devices["output"].append(device_info)
                    
        except Exception as e:
            logger.error(f"Failed to get audio devices via sounddevice: {e}")
            
    except Exception as e:
        logger.error(f"Failed to get audio devices: {e}")
    
    return devices


def is_admin() -> bool:
    """
    Check if running with administrator privileges.
    
    Returns:
        True if running as admin
    """
    try:
        if sys.platform == "win32":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.getuid() == 0
    except:
        return False


def request_admin() -> bool:
    """
    Request administrator privileges.
    
    Returns:
        True if admin privileges obtained
    """
    if is_admin():
        return True
    
    if sys.platform == "win32":
        try:
            import ctypes
            import sys
            
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            return True
        except:
            return False
    else:
        logger.warning("Admin privileges required. Please run with sudo.")
        return False