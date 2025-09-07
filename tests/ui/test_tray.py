"""
Unit tests for system tray manager.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time
from PIL import Image
import io

from nextalk.ui.tray import SystemTrayManager, TrayStatus
from nextalk.ui.menu import TrayMenu, MenuItem, MenuAction
from nextalk.config.models import UIConfig


class TestSystemTrayManager(unittest.TestCase):
    """Test SystemTrayManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = UIConfig(
            show_tray_icon=True,
            show_notifications=True,
            tray_icon_theme="auto"
        )
        
    def tearDown(self):
        """Clean up after tests."""
        pass
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_init(self, mock_icon_manager, mock_pystray):
        """Test tray manager initialization."""
        manager = SystemTrayManager(self.config)
        
        self.assertEqual(manager.config, self.config)
        self.assertIsNone(manager._icon)
        self.assertIsInstance(manager._menu, TrayMenu)
        self.assertEqual(manager._status, TrayStatus.IDLE)
        self.assertFalse(manager._running)
        self.assertIsNone(manager._thread)
        
        # Check callbacks are initialized
        self.assertIsNone(manager._on_quit)
        self.assertIsNone(manager._on_toggle)
        self.assertIsNone(manager._on_settings)
        self.assertIsNone(manager._on_about)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_start(self, mock_icon_manager, mock_pystray):
        """Test starting the system tray."""
        manager = SystemTrayManager(self.config)
        
        with patch.object(manager, '_create_icon') as mock_create:
            with patch('threading.Thread') as mock_thread:
                thread_instance = Mock()
                mock_thread.return_value = thread_instance
                
                manager.start()
                
                # Check that icon was created
                mock_create.assert_called_once()
                
                # Check that thread was started
                mock_thread.assert_called_once()
                thread_instance.start.assert_called_once()
                
                self.assertTrue(manager._running)
                self.assertEqual(manager._thread, thread_instance)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_start_already_running(self, mock_icon_manager, mock_pystray):
        """Test starting when already running."""
        manager = SystemTrayManager(self.config)
        manager._running = True
        
        with patch.object(manager, '_create_icon') as mock_create:
            manager.start()
            
            # Should not create icon again
            mock_create.assert_not_called()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_start_disabled(self, mock_icon_manager, mock_pystray):
        """Test starting when tray is disabled."""
        config = UIConfig(show_tray_icon=False)
        manager = SystemTrayManager(config)
        
        with patch.object(manager, '_create_icon') as mock_create:
            manager.start()
            
            # Should not create icon
            mock_create.assert_not_called()
            self.assertFalse(manager._running)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_stop(self, mock_icon_manager, mock_pystray):
        """Test stopping the system tray."""
        manager = SystemTrayManager(self.config)
        
        # Setup mock icon and thread
        mock_icon = Mock()
        manager._icon = mock_icon
        manager._running = True
        
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        manager._thread = mock_thread
        
        manager.stop()
        
        # Check that icon was stopped
        mock_icon.stop.assert_called_once()
        
        # Check that thread was joined
        mock_thread.join.assert_called_once_with(timeout=2.0)
        
        self.assertFalse(manager._running)
        self.assertIsNone(manager._icon)
        self.assertIsNone(manager._thread)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_stop_not_running(self, mock_icon_manager, mock_pystray):
        """Test stopping when not running."""
        manager = SystemTrayManager(self.config)
        manager._running = False
        
        # Should not raise any errors
        manager.stop()
        
        self.assertFalse(manager._running)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_update_status(self, mock_icon_manager, mock_pystray):
        """Test updating tray status."""
        manager = SystemTrayManager(self.config)
        
        # Create mock icon
        mock_icon = Mock()
        manager._icon = mock_icon
        
        with patch.object(manager, '_get_icon_image') as mock_get_image:
            mock_image = Mock()
            mock_get_image.return_value = mock_image
            
            # Update status
            manager.update_status(TrayStatus.ACTIVE)
            
            self.assertEqual(manager._status, TrayStatus.ACTIVE)
            mock_get_image.assert_called_once_with(TrayStatus.ACTIVE)
            self.assertEqual(mock_icon.icon, mock_image)
            self.assertEqual(mock_icon.title, "NexTalk - 识别中")
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_update_status_same(self, mock_icon_manager, mock_pystray):
        """Test updating to same status."""
        manager = SystemTrayManager(self.config)
        manager._status = TrayStatus.ACTIVE
        
        mock_icon = Mock()
        manager._icon = mock_icon
        
        with patch.object(manager, '_get_icon_image') as mock_get_image:
            # Update to same status
            manager.update_status(TrayStatus.ACTIVE)
            
            # Should not update icon
            mock_get_image.assert_not_called()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_show_notification(self, mock_icon_manager, mock_pystray):
        """Test showing notifications."""
        manager = SystemTrayManager(self.config)
        
        mock_icon = Mock()
        manager._icon = mock_icon
        
        manager.show_notification("Test Title", "Test Message")
        
        mock_icon.notify.assert_called_once_with("Test Title", "Test Message")
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_show_notification_disabled(self, mock_icon_manager, mock_pystray):
        """Test showing notifications when disabled."""
        config = UIConfig(show_notifications=False)
        manager = SystemTrayManager(config)
        
        mock_icon = Mock()
        manager._icon = mock_icon
        
        manager.show_notification("Test Title", "Test Message")
        
        # Should not show notification
        mock_icon.notify.assert_not_called()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_set_callbacks(self, mock_icon_manager, mock_pystray):
        """Test setting callbacks."""
        manager = SystemTrayManager(self.config)
        
        quit_cb = Mock()
        toggle_cb = Mock()
        settings_cb = Mock()
        about_cb = Mock()
        
        manager.set_on_quit(quit_cb)
        manager.set_on_toggle(toggle_cb)
        manager.set_on_settings(settings_cb)
        manager.set_on_about(about_cb)
        
        self.assertEqual(manager._on_quit, quit_cb)
        self.assertEqual(manager._on_toggle, toggle_cb)
        self.assertEqual(manager._on_settings, settings_cb)
        self.assertEqual(manager._on_about, about_cb)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_quit(self, mock_icon_manager, mock_pystray):
        """Test handling quit action."""
        manager = SystemTrayManager(self.config)
        
        quit_cb = Mock()
        manager.set_on_quit(quit_cb)
        
        with patch.object(manager, 'stop') as mock_stop:
            item = MenuItem("Quit", MenuAction.QUIT)
            manager._handle_quit(item)
            
            quit_cb.assert_called_once()
            mock_stop.assert_called_once()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_toggle(self, mock_icon_manager, mock_pystray):
        """Test handling toggle action."""
        manager = SystemTrayManager(self.config)
        
        toggle_cb = Mock()
        manager.set_on_toggle(toggle_cb)
        
        item = MenuItem("Toggle", MenuAction.TOGGLE_RECOGNITION)
        manager._handle_toggle(item)
        
        toggle_cb.assert_called_once()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_settings(self, mock_icon_manager, mock_pystray):
        """Test handling settings action."""
        manager = SystemTrayManager(self.config)
        
        settings_cb = Mock()
        manager.set_on_settings(settings_cb)
        
        item = MenuItem("Settings", MenuAction.OPEN_SETTINGS)
        manager._handle_settings(item)
        
        settings_cb.assert_called_once()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_settings_no_callback(self, mock_icon_manager, mock_pystray):
        """Test handling settings without callback."""
        manager = SystemTrayManager(self.config)
        
        with patch.object(manager, 'show_notification') as mock_notify:
            item = MenuItem("Settings", MenuAction.OPEN_SETTINGS)
            manager._handle_settings(item)
            
            mock_notify.assert_called_once_with("设置", "设置界面尚未实现")
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_about(self, mock_icon_manager, mock_pystray):
        """Test handling about action."""
        manager = SystemTrayManager(self.config)
        
        about_cb = Mock()
        manager.set_on_about(about_cb)
        
        item = MenuItem("About", MenuAction.ABOUT)
        manager._handle_about(item)
        
        about_cb.assert_called_once()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_about_no_callback(self, mock_icon_manager, mock_pystray):
        """Test handling about without callback."""
        manager = SystemTrayManager(self.config)
        
        with patch.object(manager, 'show_notification') as mock_notify:
            item = MenuItem("About", MenuAction.ABOUT)
            manager._handle_about(item)
            
            mock_notify.assert_called_once()
            args = mock_notify.call_args[0]
            self.assertIn("NexTalk", args[0])
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_handle_statistics(self, mock_icon_manager, mock_pystray):
        """Test handling statistics action."""
        manager = SystemTrayManager(self.config)
        
        with patch.object(manager, 'show_notification') as mock_notify:
            item = MenuItem("Stats", MenuAction.VIEW_STATISTICS)
            manager._handle_statistics(item)
            
            mock_notify.assert_called_once_with("统计信息", "统计功能尚未实现")
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_get_icon_image(self, mock_icon_manager, mock_pystray):
        """Test getting icon image."""
        manager = SystemTrayManager(self.config)
        
        # Mock icon manager
        mock_icon_mgr = Mock()
        manager._icon_manager = mock_icon_mgr
        mock_icon_mgr.get_icon.return_value = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x00\x0eIDATx\xdab\x00\x02\x00\x00\x05\x00\x01\xe2&\x05[\x00\x00\x00\x00IEND\xaeB`\x82'
        
        with patch('nextalk.ui.tray.Image') as mock_image_cls:
            mock_image = Mock()
            mock_image.size = (16, 16)
            mock_image_cls.open.return_value = mock_image
            
            result = manager._get_icon_image(TrayStatus.ACTIVE)
            
            mock_icon_mgr.get_icon.assert_called_once_with("active")
            self.assertEqual(result, mock_image)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_get_icon_image_resize(self, mock_icon_manager, mock_pystray):
        """Test getting icon image with resize."""
        manager = SystemTrayManager(self.config)
        
        # Mock icon manager
        mock_icon_mgr = Mock()
        manager._icon_manager = mock_icon_mgr
        mock_icon_mgr.get_icon.return_value = b'fake_icon_data'
        
        with patch('nextalk.ui.tray.Image') as mock_image_cls:
            mock_image = Mock()
            mock_image.size = (32, 32)  # Wrong size
            mock_resized = Mock()
            mock_image.resize.return_value = mock_resized
            mock_image_cls.open.return_value = mock_image
            
            result = manager._get_icon_image(TrayStatus.ACTIVE)
            
            # Should resize image
            mock_image.resize.assert_called_once()
            self.assertEqual(result, mock_resized)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_get_icon_image_error(self, mock_icon_manager, mock_pystray):
        """Test getting icon image with error."""
        manager = SystemTrayManager(self.config)
        
        # Mock icon manager to raise error
        mock_icon_mgr = Mock()
        manager._icon_manager = mock_icon_mgr
        mock_icon_mgr.get_icon.side_effect = Exception("Icon error")
        
        with patch.object(manager, '_create_fallback_icon') as mock_fallback:
            mock_fallback_icon = Mock()
            mock_fallback.return_value = mock_fallback_icon
            
            result = manager._get_icon_image(TrayStatus.ERROR)
            
            mock_fallback.assert_called_once_with(TrayStatus.ERROR)
            self.assertEqual(result, mock_fallback_icon)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    @patch('nextalk.ui.tray.Image')
    def test_create_fallback_icon(self, mock_image_cls, mock_icon_manager, mock_pystray):
        """Test creating fallback icon."""
        manager = SystemTrayManager(self.config)
        
        mock_image = Mock()
        mock_image_cls.new.return_value = mock_image
        
        # Test different statuses
        result = manager._create_fallback_icon(TrayStatus.IDLE)
        mock_image_cls.new.assert_called_with('RGB', (16, 16), (128, 128, 128))
        self.assertEqual(result, mock_image)
        
        result = manager._create_fallback_icon(TrayStatus.ACTIVE)
        mock_image_cls.new.assert_called_with('RGB', (16, 16), (0, 255, 0))
        
        result = manager._create_fallback_icon(TrayStatus.ERROR)
        mock_image_cls.new.assert_called_with('RGB', (16, 16), (255, 0, 0))
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_create_pystray_menu(self, mock_icon_manager, mock_pystray):
        """Test creating pystray menu."""
        manager = SystemTrayManager(self.config)
        
        # Mock pystray Menu
        mock_menu_cls = Mock()
        mock_pystray.Menu = mock_menu_cls
        mock_pystray.Menu.SEPARATOR = "SEPARATOR"
        mock_pystray.MenuItem = Mock
        
        result = manager._create_pystray_menu()
        
        # Should create menu with items
        mock_menu_cls.assert_called_once()
        self.assertIsNotNone(result)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_update_menu(self, mock_icon_manager, mock_pystray):
        """Test updating tray menu."""
        manager = SystemTrayManager(self.config)
        
        mock_icon = Mock()
        manager._icon = mock_icon
        
        with patch.object(manager, '_create_pystray_menu') as mock_create_menu:
            mock_menu = Mock()
            mock_create_menu.return_value = mock_menu
            
            manager.update_menu()
            
            mock_create_menu.assert_called_once()
            self.assertEqual(mock_icon.menu, mock_menu)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_is_running(self, mock_icon_manager, mock_pystray):
        """Test checking if tray is running."""
        manager = SystemTrayManager(self.config)
        
        self.assertFalse(manager.is_running())
        
        manager._running = True
        self.assertTrue(manager.is_running())
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_create_icon(self, mock_icon_manager, mock_pystray):
        """Test creating tray icon."""
        manager = SystemTrayManager(self.config)
        
        with patch.object(manager, '_get_icon_image') as mock_get_image:
            with patch.object(manager, '_create_pystray_menu') as mock_create_menu:
                mock_image = Mock()
                mock_menu = Mock()
                mock_get_image.return_value = mock_image
                mock_create_menu.return_value = mock_menu
                
                mock_icon = Mock()
                mock_pystray.Icon.return_value = mock_icon
                
                manager._create_icon()
                
                mock_get_image.assert_called_once_with(TrayStatus.IDLE)
                mock_create_menu.assert_called_once()
                mock_pystray.Icon.assert_called_once_with(
                    "NexTalk",
                    mock_image,
                    "NexTalk - 语音识别输入",
                    mock_menu
                )
                self.assertEqual(manager._icon, mock_icon)
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_run(self, mock_icon_manager, mock_pystray):
        """Test running tray icon."""
        manager = SystemTrayManager(self.config)
        
        mock_icon = Mock()
        manager._icon = mock_icon
        
        manager._run()
        
        mock_icon.run.assert_called_once()
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_run_error(self, mock_icon_manager, mock_pystray):
        """Test running tray icon with error."""
        manager = SystemTrayManager(self.config)
        
        mock_icon = Mock()
        mock_icon.run.side_effect = Exception("Run error")
        manager._icon = mock_icon
        manager._running = True
        
        # Should catch exception and set running to False
        manager._run()
        
        self.assertFalse(manager._running)


class TestTrayIntegration(unittest.TestCase):
    """Test tray integration scenarios."""
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_full_lifecycle(self, mock_icon_manager, mock_pystray):
        """Test full tray lifecycle."""
        config = UIConfig(show_tray_icon=True)
        manager = SystemTrayManager(config)
        
        # Setup callbacks
        quit_cb = Mock()
        toggle_cb = Mock()
        
        manager.set_on_quit(quit_cb)
        manager.set_on_toggle(toggle_cb)
        
        # Start tray
        with patch('threading.Thread'):
            manager.start()
            self.assertTrue(manager.is_running())
        
        # Update status
        with patch.object(manager, '_get_icon_image'):
            manager.update_status(TrayStatus.ACTIVE)
            self.assertEqual(manager._status, TrayStatus.ACTIVE)
        
        # Show notification
        with patch.object(manager, '_icon') as mock_icon:
            manager.show_notification("Test", "Message")
            if mock_icon:
                mock_icon.notify.assert_called_once()
        
        # Stop tray
        manager.stop()
        self.assertFalse(manager.is_running())
    
    @patch('nextalk.ui.tray.pystray')
    @patch('nextalk.ui.tray.IconManager')
    def test_menu_action_flow(self, mock_icon_manager, mock_pystray):
        """Test menu action flow."""
        manager = SystemTrayManager()
        
        # Setup mock handlers
        handlers = {
            'quit': Mock(),
            'toggle': Mock(),
            'settings': Mock(),
            'about': Mock()
        }
        
        manager.set_on_quit(handlers['quit'])
        manager.set_on_toggle(handlers['toggle'])
        manager.set_on_settings(handlers['settings'])
        manager.set_on_about(handlers['about'])
        
        # Trigger actions through menu
        items = manager._menu.get_items()
        
        for item in items:
            if item.action == MenuAction.TOGGLE_RECOGNITION:
                manager._handle_toggle(item)
                handlers['toggle'].assert_called_once()
            elif item.action == MenuAction.OPEN_SETTINGS:
                manager._handle_settings(item)
                handlers['settings'].assert_called_once()
            elif item.action == MenuAction.ABOUT:
                manager._handle_about(item)
                handlers['about'].assert_called_once()
            elif item.action == MenuAction.QUIT:
                with patch.object(manager, 'stop'):
                    manager._handle_quit(item)
                    handlers['quit'].assert_called_once()


if __name__ == '__main__':
    unittest.main()