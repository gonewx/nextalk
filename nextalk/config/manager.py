"""
Configuration manager for NexTalk.

Handles loading, saving, and validation of configuration files.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from .models import NexTalkConfig


logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration-related errors."""
    pass


class ConfigManager:
    """Manages NexTalk configuration loading, saving, and validation."""
    
    DEFAULT_CONFIG_FILENAME = "nextalk.yaml"
    CONFIG_VERSION = "1.0"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Custom path to configuration file. If None, uses default location.
        """
        self.config_path = config_path
        self._config: Optional[NexTalkConfig] = None
        self._config_file_path: Optional[Path] = None
        
    def get_config_file_path(self) -> Path:
        """Get the path to the configuration file."""
        if self._config_file_path is not None:
            return self._config_file_path
            
        if self.config_path:
            self._config_file_path = Path(self.config_path)
        else:
            # Use default location
            temp_config = NexTalkConfig()  # Just to get user_data_dir
            config_dir = Path(temp_config.user_data_dir)
            config_dir.mkdir(parents=True, exist_ok=True)
            self._config_file_path = config_dir / self.DEFAULT_CONFIG_FILENAME
            
        return self._config_file_path
    
    def load_config(self) -> NexTalkConfig:
        """
        Load configuration from file.
        
        Returns:
            NexTalkConfig instance
            
        Raises:
            ConfigError: If configuration loading or validation fails
        """
        config_file = self.get_config_file_path()
        
        if not config_file.exists():
            logger.info(f"Configuration file not found at {config_file}, creating default")
            self._config = NexTalkConfig()
            self.save_config(self._config)
            return self._config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Check config version compatibility
            file_version = data.get('config_version', '1.0')
            if file_version != self.CONFIG_VERSION:
                logger.warning(f"Config version mismatch: file={file_version}, expected={self.CONFIG_VERSION}")
            
            self._config = NexTalkConfig.from_dict(data)
            
            # Validate loaded configuration
            validation_errors = self._config.validate()
            if validation_errors:
                error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
                raise ConfigError(error_msg)
            
            logger.info(f"Configuration loaded successfully from {config_file}")
            return self._config
            
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML configuration: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: Optional[NexTalkConfig] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save. If None, uses current loaded config.
            
        Raises:
            ConfigError: If saving fails
        """
        if config is None:
            if self._config is None:
                raise ConfigError("No configuration to save")
            config = self._config
        else:
            self._config = config
        
        config_file = self.get_config_file_path()
        
        try:
            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if config_file.exists():
                backup_path = config_file.with_suffix('.yaml.bak')
                config_file.replace(backup_path)
                logger.debug(f"Created backup at {backup_path}")
            
            # Save configuration
            data = config.to_dict()
            data['config_version'] = self.CONFIG_VERSION
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"Configuration saved to {config_file}")
            
        except Exception as e:
            raise ConfigError(f"Failed to save configuration: {e}")
    
    def get_config(self) -> NexTalkConfig:
        """
        Get current configuration, loading if necessary.
        
        Returns:
            Current NexTalkConfig instance
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def reload_config(self) -> NexTalkConfig:
        """
        Force reload configuration from file.
        
        Returns:
            Reloaded NexTalkConfig instance
        """
        self._config = None
        return self.load_config()
    
    def create_default_config(self, force: bool = False) -> NexTalkConfig:
        """
        Create default configuration file.
        
        Args:
            force: If True, overwrites existing configuration file
            
        Returns:
            Default NexTalkConfig instance
            
        Raises:
            ConfigError: If file exists and force=False
        """
        config_file = self.get_config_file_path()
        
        if config_file.exists() and not force:
            raise ConfigError(f"Configuration file already exists: {config_file}")
        
        self._config = NexTalkConfig()
        self.save_config(self._config)
        
        logger.info(f"Default configuration created at {config_file}")
        return self._config
    
    def validate_config_file(self) -> List[str]:
        """
        Validate configuration file without loading it as current config.
        
        Returns:
            List of validation errors (empty if valid)
        """
        config_file = self.get_config_file_path()
        
        if not config_file.exists():
            return [f"Configuration file not found: {config_file}"]
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            temp_config = NexTalkConfig.from_dict(data)
            return temp_config.validate()
            
        except yaml.YAMLError as e:
            return [f"YAML parsing error: {e}"]
        except Exception as e:
            return [f"Configuration loading error: {e}"]
    
    def update_config(self, updates: Dict[str, Any], save: bool = True) -> NexTalkConfig:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
            save: Whether to save changes to file
            
        Returns:
            Updated NexTalkConfig instance
        """
        current_config = self.get_config()
        
        # Convert current config to dict
        config_dict = current_config.to_dict()
        
        # Apply updates (supports nested updates)
        self._deep_update(config_dict, updates)
        
        # Create new config from updated dict
        new_config = NexTalkConfig.from_dict(config_dict)
        
        # Validate updated config
        validation_errors = new_config.validate()
        if validation_errors:
            error_msg = "Updated configuration is invalid:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            raise ConfigError(error_msg)
        
        self._config = new_config
        
        if save:
            self.save_config(new_config)
        
        return new_config
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update nested dictionaries."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration for display/debugging.
        
        Returns:
            Dictionary with configuration summary
        """
        if self._config is None:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "config_file": str(self.get_config_file_path()),
            "version": self._config.version,
            "config_version": self._config.config_version,
            "server": f"{self._config.server.host}:{self._config.server.port}",
            "hotkey": self._config.hotkey.trigger_key,
            "audio_device": self._config.audio.device_name or "default",
            "validation_errors": self._config.validate()
        }