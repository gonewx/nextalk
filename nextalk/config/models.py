"""
Configuration data models for NexTalk.

Based on funasr_wss_client.py parameter structure with extensions for NexTalk features.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import os
from pathlib import Path


@dataclass
class ServerConfig:
    """FunASR WebSocket server configuration."""
    host: str = "localhost"
    port: int = 10095
    use_ssl: bool = True
    ssl_verify: bool = False
    timeout: float = 30.0
    reconnect_attempts: int = 3
    reconnect_interval: float = 2.0


@dataclass 
class AudioConfig:
    """Audio capture and processing configuration."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: List[int] = field(default_factory=lambda: [5, 10, 5])
    encoder_chunk_look_back: int = 4
    decoder_chunk_look_back: int = 0
    chunk_interval: int = 10
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    input_buffer_size: int = 4096
    noise_suppression: bool = True
    auto_gain_control: bool = True


@dataclass
class RecordingConfig:
    """Recording control configuration."""
    mode: str = "toggle"  # "toggle", "hold", "continuous", "once"
    hotkey: str = "ctrl+shift+space"
    stop_key: str = ""  # Empty means use same hotkey
    conflict_detection: bool = True
    enable_sound_feedback: bool = True


@dataclass
class UIConfig:
    """User interface configuration."""
    show_tray_icon: bool = True
    auto_start: bool = False
    minimize_to_tray: bool = True
    show_notifications: bool = True
    notification_duration: float = 3.0
    tray_icon_theme: str = "auto"  # auto, light, dark
    language: str = "zh_CN"


@dataclass
class IMEConfig:
    """Input Method Editor (IME) configuration."""
    enabled: bool = True
    preferred_framework: Optional[str] = None  # ibus, fcitx5, fcitx, auto
    fallback_timeout: float = 5.0
    composition_timeout: float = 1.0
    state_monitor_interval: float = 0.1
    auto_detect_ime: bool = True
    linux_ime_frameworks: List[str] = field(default_factory=lambda: ["fcitx5", "ibus", "fcitx"])
    dbus_timeout: float = 2.0
    debug_mode: bool = False


@dataclass
class TextInjectionConfig:
    """Text injection configuration - Pure IME experience."""
    # IME-based injection (primary method)
    use_ime: bool = True
    ime_config: IMEConfig = field(default_factory=IMEConfig)
    
    # Core injection settings
    auto_inject: bool = True
    fallback_to_clipboard: bool = False  # Disabled for pure IME experience
    inject_delay: float = 0.1
    
    # IME framework configuration
    ime_frameworks: List[str] = field(default_factory=lambda: ["fcitx5", "ibus", "fcitx"])
    ime_debug: bool = False
    
    # Text formatting options
    cursor_positioning: str = "end"  # end, start, select
    format_text: bool = True
    strip_whitespace: bool = True
    
    # App compatibility (legacy - less relevant with IME approach)
    compatible_apps: List[str] = field(default_factory=list)
    incompatible_apps: List[str] = field(default_factory=list)


@dataclass
class RecognitionConfig:
    """Speech recognition configuration."""
    mode: str = "2pass"  # offline, online, 2pass
    use_itn: bool = True
    use_punctuation: bool = True
    hotwords: List[str] = field(default_factory=list)
    hotword_file: Optional[str] = None
    words_max_print: int = 10000
    output_dir: Optional[str] = None
    language_model: str = "zh-cn"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class NexTalkConfig:
    """Main configuration class for NexTalk application."""
    server: ServerConfig = field(default_factory=ServerConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    text_injection: TextInjectionConfig = field(default_factory=TextInjectionConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Application metadata
    version: str = "0.1.0"
    config_version: str = "1.0"
    user_data_dir: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.user_data_dir is None:
            self.user_data_dir = self._get_default_user_data_dir()
            
        # Ensure user data directory exists
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_default_user_data_dir(self) -> str:
        """Get default user data directory based on OS."""
        if os.name == "nt":  # Windows
            base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
            return os.path.join(base_dir, "NexTalk")
        else:  # Unix-like (Linux, macOS)
            base_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
            return os.path.join(base_dir, "nextalk")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for YAML serialization."""
        result = {}
        for field_name, field_def in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            if hasattr(value, '__dataclass_fields__'):
                # Nested dataclass - handle recursively
                nested_dict = {}
                for sub_field in value.__dataclass_fields__.keys():
                    sub_value = getattr(value, sub_field)
                    if hasattr(sub_value, '__dataclass_fields__'):
                        # Double nested (like ime_config in text_injection)
                        nested_dict[sub_field] = {
                            sub_sub_field: getattr(sub_value, sub_sub_field)
                            for sub_sub_field in sub_value.__dataclass_fields__.keys()
                        }
                    else:
                        nested_dict[sub_field] = sub_value
                result[field_name] = nested_dict
            else:
                result[field_name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NexTalkConfig':
        """Create config instance from dictionary."""
        # Extract nested configs
        server_data = data.pop('server', {})
        audio_data = data.pop('audio', {})
        recording_data = data.pop('recording', {})
        ui_data = data.pop('ui', {})
        text_injection_data = data.pop('text_injection', {})
        recognition_data = data.pop('recognition', {})
        logging_data = data.pop('logging', {})
        
        # Handle IME config nested in text_injection
        ime_data = text_injection_data.pop('ime_config', {})
        ime_config = IMEConfig(**ime_data)
        
        return cls(
            server=ServerConfig(**server_data),
            audio=AudioConfig(**audio_data),
            recording=RecordingConfig(**recording_data),
            ui=UIConfig(**ui_data),
            text_injection=TextInjectionConfig(ime_config=ime_config, **text_injection_data),
            recognition=RecognitionConfig(**recognition_data),
            logging=LoggingConfig(**logging_data),
            **data
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate server config
        if not (1 <= self.server.port <= 65535):
            errors.append(f"Invalid server port: {self.server.port}")
        
        if self.server.reconnect_attempts < 0:
            errors.append("Reconnect attempts must be non-negative")
            
        # Validate audio config
        if self.audio.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append(f"Unsupported sample rate: {self.audio.sample_rate}")
            
        if self.audio.channels not in [1, 2]:
            errors.append(f"Invalid audio channels: {self.audio.channels}")
        
        # Basic hotkey format validation
        if self.recording.hotkey and not self.recording.hotkey.strip():
            errors.append("Recording hotkey cannot be empty")
        if self.recording.hotkey and "+" not in self.recording.hotkey:
            errors.append("Recording hotkey should contain modifier keys (e.g., 'ctrl+shift+space')")
        
        # Validate recognition config
        if self.recognition.mode not in ["offline", "online", "2pass"]:
            errors.append(f"Invalid recognition mode: {self.recognition.mode}")
            
        # Validate recording config
        if self.recording.mode not in ["toggle", "hold", "continuous", "once"]:
            errors.append(f"Invalid recording mode: {self.recording.mode}")
            
        # Validate logging config
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_levels:
            errors.append(f"Invalid logging level: {self.logging.level}")
        
        return errors