"""
Audio device management for NexTalk.

Handles audio device detection, selection, and information management.
"""

import logging
import sounddevice as sd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from ..config.models import AudioConfig


logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    device_id: int
    device_name: str
    channels: int
    default_sample_rate: float
    max_input_channels: int
    max_output_channels: int
    is_default: bool = False
    is_available: bool = True
    
    def __str__(self) -> str:
        status = "✓" if self.is_available else "✗"
        default_mark = " (默认)" if self.is_default else ""
        return f"[{self.device_id}] {status} {self.device_name}{default_mark} - {self.max_input_channels}通道 @{self.default_sample_rate}Hz"


class AudioDeviceError(Exception):
    """Audio device related errors."""
    pass


class AudioDeviceManager:
    """Manages audio input devices for NexTalk."""
    
    def __init__(self):
        """Initialize audio device manager."""
        self._devices: List[AudioDevice] = []
        self._default_device_id: Optional[int] = None
        self._refresh_devices()
    
    def _refresh_devices(self) -> None:
        """Refresh the list of available audio devices."""
        self._devices.clear()
        
        try:
            # Get device information from sounddevice
            devices_info = sd.query_devices()
            default_input = sd.default.device[0] if sd.default.device[0] is not None else None
            
            if isinstance(devices_info, dict):
                # Single device
                devices_info = [devices_info]
            
            for idx, device_info in enumerate(devices_info):
                # Only include devices with input channels
                if device_info.get('max_input_channels', 0) > 0:
                    device = AudioDevice(
                        device_id=idx,
                        device_name=device_info['name'],
                        channels=min(device_info.get('max_input_channels', 1), 2),  # Limit to stereo
                        default_sample_rate=device_info.get('default_samplerate', 44100),
                        max_input_channels=device_info.get('max_input_channels', 0),
                        max_output_channels=device_info.get('max_output_channels', 0),
                        is_default=(idx == default_input)
                    )
                    
                    # Test device availability
                    device.is_available = self._test_device_availability(device)
                    
                    self._devices.append(device)
                    
                    if device.is_default:
                        self._default_device_id = idx
            
            logger.info(f"Found {len(self._devices)} audio input devices")
            
        except Exception as e:
            logger.error(f"Failed to refresh audio devices: {e}")
            raise AudioDeviceError(f"Failed to enumerate audio devices: {e}")
    
    def _test_device_availability(self, device: AudioDevice) -> bool:
        """Test if an audio device is actually available for recording."""
        try:
            # Try to open the device briefly to test availability
            with sd.InputStream(
                device=device.device_id,
                channels=1,
                samplerate=16000,
                blocksize=1024,
                dtype=np.float32
            ):
                pass
            return True
        except Exception as e:
            logger.debug(f"Device {device.device_name} not available: {e}")
            return False
    
    def get_devices(self, refresh: bool = False) -> List[AudioDevice]:
        """
        Get list of available audio input devices.
        
        Args:
            refresh: Whether to refresh device list before returning
            
        Returns:
            List of AudioDevice objects
        """
        if refresh:
            self._refresh_devices()
        return self._devices.copy()
    
    def get_available_devices(self, refresh: bool = False) -> List[AudioDevice]:
        """Get list of available and working audio input devices."""
        devices = self.get_devices(refresh=refresh)
        return [device for device in devices if device.is_available]
    
    def get_default_device(self) -> Optional[AudioDevice]:
        """Get the default audio input device."""
        for device in self._devices:
            if device.is_default and device.is_available:
                return device
        
        # If no default device found, return first available
        available_devices = self.get_available_devices()
        return available_devices[0] if available_devices else None
    
    def get_device_by_id(self, device_id: int) -> Optional[AudioDevice]:
        """Get device by ID."""
        for device in self._devices:
            if device.device_id == device_id:
                return device
        return None
    
    def get_device_by_name(self, device_name: str) -> Optional[AudioDevice]:
        """Get device by name (case insensitive partial match)."""
        device_name_lower = device_name.lower()
        for device in self._devices:
            if device_name_lower in device.device_name.lower():
                return device
        return None
    
    def select_best_device(self, config: AudioConfig) -> AudioDevice:
        """
        Select the best audio device based on configuration preferences.
        
        Args:
            config: Audio configuration with device preferences
            
        Returns:
            Selected AudioDevice
            
        Raises:
            AudioDeviceError: If no suitable device found
        """
        available_devices = self.get_available_devices(refresh=True)
        
        if not available_devices:
            raise AudioDeviceError("No available audio input devices found")
        
        # Try to find device by explicit ID first
        if config.device_id is not None:
            device = self.get_device_by_id(config.device_id)
            if device and device.is_available:
                logger.info(f"Selected device by ID: {device}")
                return device
            else:
                logger.warning(f"Configured device ID {config.device_id} not available")
        
        # Try to find device by name
        if config.device_name:
            device = self.get_device_by_name(config.device_name)
            if device and device.is_available:
                logger.info(f"Selected device by name: {device}")
                return device
            else:
                logger.warning(f"Configured device name '{config.device_name}' not found")
        
        # Use default device
        default_device = self.get_default_device()
        if default_device:
            logger.info(f"Selected default device: {default_device}")
            return default_device
        
        # Fallback to first available device
        device = available_devices[0]
        logger.info(f"Selected first available device: {device}")
        return device
    
    def validate_device_config(self, device: AudioDevice, config: AudioConfig) -> List[str]:
        """
        Validate if device supports the requested configuration.
        
        Args:
            device: Audio device to validate
            config: Audio configuration to validate against
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check channel count
        if config.channels > device.max_input_channels:
            issues.append(
                f"Requested {config.channels} channels, but device only supports {device.max_input_channels}"
            )
        
        # Check sample rate compatibility
        try:
            # Test if the sample rate is supported
            with sd.InputStream(
                device=device.device_id,
                channels=min(config.channels, device.max_input_channels),
                samplerate=config.sample_rate,
                blocksize=1024,
                dtype=np.float32
            ):
                pass
        except Exception as e:
            issues.append(f"Sample rate {config.sample_rate}Hz not supported: {e}")
        
        return issues
    
    def get_device_info_summary(self) -> Dict[str, Any]:
        """Get summary information about audio devices."""
        available = self.get_available_devices()
        default = self.get_default_device()
        
        return {
            "total_devices": len(self._devices),
            "available_devices": len(available),
            "default_device": default.device_name if default else None,
            "devices": [
                {
                    "id": device.device_id,
                    "name": device.device_name,
                    "channels": device.max_input_channels,
                    "sample_rate": device.default_sample_rate,
                    "is_default": device.is_default,
                    "available": device.is_available
                }
                for device in self._devices
            ]
        }
    
    def print_device_list(self) -> None:
        """Print formatted list of audio devices to console."""
        devices = self.get_devices(refresh=True)
        
        if not devices:
            print("没有找到音频输入设备")
            return
        
        print("可用的音频输入设备:")
        print("-" * 60)
        
        for device in devices:
            print(device)
        
        print("-" * 60)
        print(f"共找到 {len(devices)} 个设备，其中 {len([d for d in devices if d.is_available])} 个可用")