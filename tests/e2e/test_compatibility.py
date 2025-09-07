"""
End-to-end compatibility tests for NexTalk.
"""

import unittest
import sys
import platform
import subprocess
from unittest.mock import patch, Mock
from pathlib import Path


class TestPlatformCompatibility(unittest.TestCase):
    """Test compatibility across different platforms."""
    
    def test_windows_compatibility(self):
        """Test Windows platform compatibility."""
        if sys.platform != "win32":
            self.skipTest("Not on Windows")
        
        from nextalk.utils.system import check_platform, setup_windows
        
        # Check platform detection
        self.assertTrue(check_platform())
        
        # Test Windows-specific setup
        with patch('ctypes.windll') as mock_windll:
            setup_windows()
            # Should attempt to set DPI awareness
            mock_windll.shcore.SetProcessDpiAwareness.assert_called()
    
    def test_linux_compatibility(self):
        """Test Linux platform compatibility."""
        if not sys.platform.startswith("linux"):
            self.skipTest("Not on Linux")
        
        from nextalk.utils.system import check_platform, setup_linux
        
        # Check platform detection
        self.assertTrue(check_platform())
        
        # Test Linux-specific setup
        setup_linux()
        # Linux setup is minimal, just ensure no errors
        self.assertTrue(True)
    
    def test_macos_compatibility(self):
        """Test macOS platform compatibility."""
        if sys.platform != "darwin":
            self.skipTest("Not on macOS")
        
        from nextalk.utils.system import check_platform, setup_macos
        
        # Check platform detection
        self.assertTrue(check_platform())
        
        # Test macOS-specific setup
        setup_macos()
        # macOS setup might require permissions
        self.assertTrue(True)
    
    def test_python_version_compatibility(self):
        """Test Python version compatibility."""
        from nextalk.utils.system import check_python_version
        
        # Should pass for Python 3.8+
        if sys.version_info >= (3, 8):
            self.assertTrue(check_python_version())
        else:
            self.assertFalse(check_python_version())
    
    def test_path_handling(self):
        """Test cross-platform path handling."""
        from nextalk.utils.system import get_app_data_dir, get_config_dir
        
        # Get directories
        app_dir = get_app_data_dir()
        config_dir = get_config_dir()
        
        # Should return Path objects
        self.assertIsInstance(app_dir, Path)
        self.assertIsInstance(config_dir, Path)
        
        # Paths should be platform-appropriate
        if sys.platform == "win32":
            self.assertIn("NexTalk", str(app_dir))
        elif sys.platform == "darwin":
            self.assertIn("Library", str(app_dir))
        else:
            self.assertIn(".local", str(app_dir)) or self.assertIn(".config", str(config_dir))


class TestApplicationCompatibility(unittest.TestCase):
    """Test compatibility with different applications."""
    
    def test_text_editor_compatibility(self):
        """Test compatibility with various text editors."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="typing")
        
        # Test with different editor contexts
        editors = ["Notepad", "VSCode", "Sublime Text", "Vim", "Emacs"]
        
        with patch('nextalk.output.text_injector.get_active_application') as mock_get_app:
            with patch('pyautogui.typewrite') as mock_typewrite:
                injector = TextInjector(config)
                
                for editor in editors:
                    mock_get_app.return_value = editor
                    
                    # Should work with all editors
                    result = injector.inject_text(f"Testing in {editor}")
                    self.assertTrue(result)
    
    def test_browser_compatibility(self):
        """Test compatibility with web browsers."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="smart")
        
        browsers = ["Chrome", "Firefox", "Safari", "Edge"]
        
        with patch('nextalk.output.text_injector.get_active_application') as mock_get_app:
            with patch('pyautogui.typewrite') as mock_typewrite:
                with patch('pyperclip.copy') as mock_copy:
                    injector = TextInjector(config)
                    
                    for browser in browsers:
                        mock_get_app.return_value = browser
                        
                        # Should adapt injection method
                        result = injector.inject_text(f"Searching in {browser}")
                        self.assertTrue(result)
    
    def test_office_compatibility(self):
        """Test compatibility with office applications."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="smart")
        
        office_apps = ["Microsoft Word", "Excel", "PowerPoint", "LibreOffice"]
        
        with patch('nextalk.output.text_injector.get_active_application') as mock_get_app:
            with patch('pyautogui.typewrite') as mock_typewrite:
                injector = TextInjector(config)
                
                for app in office_apps:
                    mock_get_app.return_value = app
                    
                    # Should handle office apps
                    result = injector.inject_text(f"Document in {app}")
                    self.assertTrue(result)
    
    def test_terminal_compatibility(self):
        """Test compatibility with terminal applications."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="typing")
        
        terminals = ["cmd.exe", "PowerShell", "Terminal", "iTerm2", "gnome-terminal"]
        
        with patch('nextalk.output.text_injector.get_active_application') as mock_get_app:
            with patch('pyautogui.typewrite') as mock_typewrite:
                injector = TextInjector(config)
                
                for terminal in terminals:
                    mock_get_app.return_value = terminal
                    
                    # Should handle terminal input
                    result = injector.inject_text(f"echo 'Testing {terminal}'")
                    self.assertTrue(result)


class TestAudioDeviceCompatibility(unittest.TestCase):
    """Test compatibility with different audio devices."""
    
    def test_microphone_detection(self):
        """Test microphone device detection."""
        from nextalk.utils.system import get_audio_devices
        
        with patch('pyaudio.PyAudio') as mock_pyaudio_cls:
            mock_pyaudio = Mock()
            mock_pyaudio_cls.return_value = mock_pyaudio
            
            # Mock device info
            mock_pyaudio.get_device_count.return_value = 3
            mock_pyaudio.get_device_info_by_index.side_effect = [
                {"name": "Built-in Microphone", "maxInputChannels": 2, "defaultSampleRate": 44100},
                {"name": "USB Headset", "maxInputChannels": 1, "defaultSampleRate": 16000},
                {"name": "Speakers", "maxInputChannels": 0, "maxOutputChannels": 2, "defaultSampleRate": 48000}
            ]
            
            devices = get_audio_devices()
            
            # Should detect input devices
            self.assertEqual(len(devices["input"]), 2)
            self.assertEqual(devices["input"][0]["name"], "Built-in Microphone")
            self.assertEqual(devices["input"][1]["name"], "USB Headset")
    
    def test_sample_rate_compatibility(self):
        """Test compatibility with different sample rates."""
        from nextalk.audio.capture import AudioCaptureManager
        from nextalk.config.models import AudioConfig
        
        # Test various sample rates
        sample_rates = [8000, 16000, 22050, 44100, 48000]
        
        with patch('pyaudio.PyAudio'):
            for rate in sample_rates:
                config = AudioConfig(sample_rate=rate)
                manager = AudioCaptureManager(config)
                
                # Should accept all standard rates
                self.assertEqual(manager.config.sample_rate, rate)
    
    def test_channel_configuration(self):
        """Test mono and stereo channel configurations."""
        from nextalk.audio.capture import AudioCaptureManager
        from nextalk.config.models import AudioConfig
        
        with patch('pyaudio.PyAudio'):
            # Test mono
            mono_config = AudioConfig(channels=1)
            mono_manager = AudioCaptureManager(mono_config)
            self.assertEqual(mono_manager.config.channels, 1)
            
            # Test stereo
            stereo_config = AudioConfig(channels=2)
            stereo_manager = AudioCaptureManager(stereo_config)
            self.assertEqual(stereo_manager.config.channels, 2)


class TestHotkeyCompatibility(unittest.TestCase):
    """Test hotkey compatibility across systems."""
    
    def test_modifier_keys(self):
        """Test different modifier key combinations."""
        from nextalk.input.hotkey import HotkeyManager
        from nextalk.config.models import HotkeyConfig
        
        # Test various hotkey combinations
        hotkeys = [
            "ctrl+space",
            "alt+space",
            "cmd+space",  # macOS
            "ctrl+alt+space",
            "ctrl+shift+r",
            "f1",  # Function keys
            "ctrl+alt+shift+s"  # Complex combination
        ]
        
        with patch('pynput.keyboard.GlobalHotKeys'):
            for hotkey in hotkeys:
                config = HotkeyConfig(trigger_key=hotkey)
                manager = HotkeyManager(config)
                
                # Should parse all hotkey formats
                self.assertIsNotNone(manager)
    
    def test_international_keyboards(self):
        """Test compatibility with international keyboard layouts."""
        from nextalk.input.hotkey import HotkeyManager
        from nextalk.config.models import HotkeyConfig
        
        # Test with different keyboard layouts
        with patch('pynput.keyboard.GlobalHotKeys'):
            config = HotkeyConfig(
                trigger_key="ctrl+alt+space",
                cancel_key="escape"
            )
            manager = HotkeyManager(config)
            
            # Should work regardless of keyboard layout
            self.assertIsNotNone(manager)


class TestNetworkCompatibility(unittest.TestCase):
    """Test network compatibility."""
    
    def test_websocket_protocols(self):
        """Test WebSocket protocol compatibility."""
        from nextalk.network.ws_client import FunASRWebSocketClient
        from nextalk.config.models import NexTalkConfig
        
        # Test different WebSocket URLs
        urls = [
            "ws://localhost:10095",
            "wss://secure.server.com:443",
            "ws://192.168.1.100:8080",
            "ws://[::1]:10095"  # IPv6
        ]
        
        with patch('websockets.connect'):
            for url in urls:
                config = NexTalkConfig()
                config.network.server_url = url
                
                client = FunASRWebSocketClient(config)
                
                # Should accept all URL formats
                self.assertEqual(client.config.network.server_url, url)
    
    def test_network_error_handling(self):
        """Test handling of network errors."""
        from nextalk.network.ws_client import FunASRWebSocketClient
        from nextalk.config.models import NexTalkConfig
        
        config = NexTalkConfig()
        
        with patch('websockets.connect') as mock_connect:
            # Simulate connection errors
            mock_connect.side_effect = [
                ConnectionRefusedError("Connection refused"),
                TimeoutError("Connection timeout"),
                None  # Success on third attempt
            ]
            
            client = FunASRWebSocketClient(config)
            
            # Should handle errors gracefully
            self.assertIsNotNone(client)


class TestLocalizationCompatibility(unittest.TestCase):
    """Test compatibility with different languages and locales."""
    
    def test_unicode_text_injection(self):
        """Test injecting Unicode text."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="typing")
        
        # Test various Unicode texts
        unicode_texts = [
            "Hello World",  # English
            "你好世界",  # Chinese
            "こんにちは世界",  # Japanese
            "Привет мир",  # Russian
            "مرحبا بالعالم",  # Arabic
            "🌍🌎🌏",  # Emoji
            "Café résumé naïve",  # Accented characters
        ]
        
        with patch('pyautogui.typewrite') as mock_typewrite:
            injector = TextInjector(config)
            
            for text in unicode_texts:
                result = injector.inject_text(text)
                self.assertTrue(result)
    
    def test_rtl_language_support(self):
        """Test right-to-left language support."""
        from nextalk.output.text_injector import TextInjector
        from nextalk.config.models import TextInjectionConfig
        
        config = TextInjectionConfig(method="clipboard")
        
        # Test RTL languages
        rtl_texts = [
            "שלום עולם",  # Hebrew
            "مرحبا بالعالم",  # Arabic
            "سلام دنیا"  # Persian
        ]
        
        with patch('pyperclip.copy') as mock_copy:
            with patch('pyautogui.hotkey'):
                injector = TextInjector(config)
                
                for text in rtl_texts:
                    result = injector.inject_text(text)
                    self.assertTrue(result)
                    mock_copy.assert_called_with(text)


if __name__ == '__main__':
    unittest.main()