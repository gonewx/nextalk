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
class HotkeyConfig:
    """Global hotkey configuration."""
    trigger_key: str = "ctrl+alt+space"
    stop_key: str = "ctrl+alt+space"  # Same key toggles
    modifier_keys: List[str] = field(default_factory=lambda: ["ctrl", "alt"])
    conflict_detection: bool = True
    enable_sound_feedback: bool = True
    mode: str = "press_and_hold"  # "toggle" or "press_and_hold"


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
class TextInjectionConfig:
    """Text injection and output configuration."""
    auto_inject: bool = True
    fallback_to_clipboard: bool = True
    inject_delay: float = 0.1
    cursor_positioning: str = "end"  # end, start, select
    format_text: bool = True
    strip_whitespace: bool = True
    compatible_apps: List[str] = field(default_factory=list)
    incompatible_apps: List[str] = field(default_factory=list)


@dataclass
class RecognitionConfig:
    """Speech recognition configuration."""
    mode: str = "2pass"  # offline, online, 2pass
    capture_mode: str = "hotkey"  # hotkey, auto_start, continuous
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
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
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
                # Nested dataclass
                result[field_name] = {
                    sub_field: getattr(value, sub_field)
                    for sub_field in value.__dataclass_fields__.keys()
                }
            else:
                result[field_name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NexTalkConfig':
        """Create config instance from dictionary."""
        # Extract nested configs
        server_data = data.pop('server', {})
        audio_data = data.pop('audio', {})
        hotkey_data = data.pop('hotkey', {})
        ui_data = data.pop('ui', {})
        text_injection_data = data.pop('text_injection', {})
        recognition_data = data.pop('recognition', {})
        logging_data = data.pop('logging', {})
        
        return cls(
            server=ServerConfig(**server_data),
            audio=AudioConfig(**audio_data),
            hotkey=HotkeyConfig(**hotkey_data),
            ui=UIConfig(**ui_data),
            text_injection=TextInjectionConfig(**text_injection_data),
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
        
        # Validate hotkey config
        valid_modifiers = ["ctrl", "alt", "shift", "cmd", "meta"]
        for modifier in self.hotkey.modifier_keys:
            if modifier.lower() not in valid_modifiers:
                errors.append(f"Invalid modifier key: {modifier}")
        
        # Validate recognition config
        if self.recognition.mode not in ["offline", "online", "2pass"]:
            errors.append(f"Invalid recognition mode: {self.recognition.mode}")
            
        if self.recognition.capture_mode not in ["hotkey", "auto_start", "continuous"]:
            errors.append(f"Invalid capture mode: {self.recognition.capture_mode}")
            
        # Validate logging config
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.logging.level.upper() not in valid_levels:
            errors.append(f"Invalid logging level: {self.logging.level}")
        
        return errors