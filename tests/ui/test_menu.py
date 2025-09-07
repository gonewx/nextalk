"""
Unit tests for tray menu management.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from nextalk.ui.menu import TrayMenu, MenuItem, MenuAction


class TestMenuItem(unittest.TestCase):
    """Test MenuItem dataclass."""
    
    def test_create_item(self):
        """Test creating menu item."""
        item = MenuItem(
            label="Test Item",
            action=MenuAction.CUSTOM,
            enabled=True,
            checked=False
        )
        
        self.assertEqual(item.label, "Test Item")
        self.assertEqual(item.action, MenuAction.CUSTOM)
        self.assertTrue(item.enabled)
        self.assertFalse(item.checked)
        self.assertIsNone(item.callback)
        self.assertIsNone(item.icon)
        self.assertIsNone(item.shortcut)
        self.assertIsNone(item.submenu)
        self.assertIsNone(item.data)
    
    def test_create_item_with_all_fields(self):
        """Test creating menu item with all fields."""
        callback = Mock()
        submenu = [MenuItem("Sub1", MenuAction.CUSTOM)]
        
        item = MenuItem(
            label="Test Item",
            action=MenuAction.CUSTOM,
            callback=callback,
            enabled=False,
            checked=True,
            icon="test_icon",
            shortcut="Ctrl+T",
            submenu=submenu,
            data={"key": "value"}
        )
        
        self.assertEqual(item.label, "Test Item")
        self.assertEqual(item.callback, callback)
        self.assertFalse(item.enabled)
        self.assertTrue(item.checked)
        self.assertEqual(item.icon, "test_icon")
        self.assertEqual(item.shortcut, "Ctrl+T")
        self.assertEqual(item.submenu, submenu)
        self.assertEqual(item.data, {"key": "value"})
    
    def test_separator_item(self):
        """Test creating separator item."""
        item = MenuItem(
            label="",
            action=MenuAction.SEPARATOR
        )
        
        self.assertEqual(item.label, "")
        self.assertEqual(item.action, MenuAction.SEPARATOR)


class TestTrayMenu(unittest.TestCase):
    """Test TrayMenu class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.menu = TrayMenu()
    
    def test_init(self):
        """Test menu initialization."""
        self.assertIsInstance(self.menu._items, list)
        self.assertIsInstance(self.menu._action_handlers, dict)
        
        # Check default menu items
        items = self.menu.get_items()
        self.assertTrue(len(items) > 0)
        
        # Check for expected default items
        actions = [item.action for item in items]
        self.assertIn(MenuAction.TOGGLE_RECOGNITION, actions)
        self.assertIn(MenuAction.OPEN_SETTINGS, actions)
        self.assertIn(MenuAction.QUIT, actions)
    
    def test_get_items(self):
        """Test getting menu items."""
        items = self.menu.get_items()
        
        self.assertIsInstance(items, list)
        self.assertTrue(all(isinstance(item, MenuItem) for item in items))
        
        # Should return a copy
        items.clear()
        self.assertTrue(len(self.menu.get_items()) > 0)
    
    def test_add_item(self):
        """Test adding menu item."""
        callback = Mock()
        
        item = self.menu.add_item(
            label="Custom Item",
            action=MenuAction.CUSTOM,
            callback=callback,
            icon="custom_icon"
        )
        
        self.assertIsInstance(item, MenuItem)
        self.assertEqual(item.label, "Custom Item")
        self.assertEqual(item.action, MenuAction.CUSTOM)
        self.assertEqual(item.callback, callback)
        self.assertEqual(item.icon, "custom_icon")
        
        # Check item was added
        items = self.menu.get_items()
        self.assertIn(item, items)
    
    def test_add_item_with_position(self):
        """Test adding menu item at specific position."""
        original_items = self.menu.get_items()
        
        item = self.menu.add_item(
            label="Inserted Item",
            action=MenuAction.CUSTOM,
            position=1
        )
        
        items = self.menu.get_items()
        self.assertEqual(items[1], item)
        self.assertEqual(len(items), len(original_items) + 1)
    
    def test_remove_item(self):
        """Test removing menu item."""
        item = self.menu.add_item("Test Item", MenuAction.CUSTOM)
        
        # Remove item
        result = self.menu.remove_item(item)
        self.assertTrue(result)
        
        # Check item was removed
        items = self.menu.get_items()
        self.assertNotIn(item, items)
    
    def test_remove_item_not_found(self):
        """Test removing non-existent item."""
        fake_item = MenuItem("Fake", MenuAction.CUSTOM)
        
        result = self.menu.remove_item(fake_item)
        self.assertFalse(result)
    
    def test_find_item(self):
        """Test finding menu item by action."""
        # Find default item
        item = self.menu.find_item(MenuAction.QUIT)
        
        self.assertIsNotNone(item)
        self.assertEqual(item.action, MenuAction.QUIT)
        self.assertEqual(item.label, "退出")
    
    def test_find_item_not_found(self):
        """Test finding non-existent item."""
        # Clear menu first
        self.menu.clear()
        
        item = self.menu.find_item(MenuAction.QUIT)
        self.assertIsNone(item)
    
    def test_find_item_in_submenu(self):
        """Test finding item in submenu."""
        # Create submenu
        sub_item = MenuItem("Sub Item", MenuAction.CUSTOM)
        parent_item = self.menu.add_item(
            "Parent",
            MenuAction.CUSTOM,
            submenu=[sub_item]
        )
        
        # Find submenu item
        found = self.menu.find_item(MenuAction.CUSTOM)
        self.assertIsNotNone(found)
    
    def test_update_item(self):
        """Test updating menu item."""
        # Update existing item
        result = self.menu.update_item(
            MenuAction.QUIT,
            label="Exit Application",
            enabled=False,
            checked=True,
            icon="new_icon"
        )
        
        self.assertTrue(result)
        
        # Check updates
        item = self.menu.find_item(MenuAction.QUIT)
        self.assertEqual(item.label, "Exit Application")
        self.assertFalse(item.enabled)
        self.assertTrue(item.checked)
        self.assertEqual(item.icon, "new_icon")
    
    def test_update_item_partial(self):
        """Test partial update of menu item."""
        original_item = self.menu.find_item(MenuAction.QUIT)
        original_label = original_item.label
        
        # Update only enabled state
        result = self.menu.update_item(
            MenuAction.QUIT,
            enabled=False
        )
        
        self.assertTrue(result)
        
        # Check partial update
        item = self.menu.find_item(MenuAction.QUIT)
        self.assertEqual(item.label, original_label)  # Unchanged
        self.assertFalse(item.enabled)  # Changed
    
    def test_update_item_not_found(self):
        """Test updating non-existent item."""
        self.menu.clear()
        
        result = self.menu.update_item(
            MenuAction.QUIT,
            label="New Label"
        )
        
        self.assertFalse(result)
    
    def test_register_handler(self):
        """Test registering action handler."""
        handler = Mock()
        
        self.menu.register_handler(MenuAction.CUSTOM, handler)
        
        self.assertIn(MenuAction.CUSTOM, self.menu._action_handlers)
        self.assertEqual(self.menu._action_handlers[MenuAction.CUSTOM], handler)
    
    def test_trigger_action_with_callback(self):
        """Test triggering action with item callback."""
        callback = Mock()
        item = MenuItem("Test", MenuAction.CUSTOM, callback=callback)
        
        self.menu.trigger_action(item)
        
        callback.assert_called_once_with(item)
    
    def test_trigger_action_with_handler(self):
        """Test triggering action with registered handler."""
        handler = Mock()
        self.menu.register_handler(MenuAction.CUSTOM, handler)
        
        item = MenuItem("Test", MenuAction.CUSTOM)
        
        self.menu.trigger_action(item)
        
        handler.assert_called_once_with(item)
    
    def test_trigger_action_callback_priority(self):
        """Test callback has priority over handler."""
        callback = Mock()
        handler = Mock()
        
        self.menu.register_handler(MenuAction.CUSTOM, handler)
        item = MenuItem("Test", MenuAction.CUSTOM, callback=callback)
        
        self.menu.trigger_action(item)
        
        # Callback should be called, not handler
        callback.assert_called_once_with(item)
        handler.assert_not_called()
    
    def test_trigger_action_no_handler(self):
        """Test triggering action without handler."""
        item = MenuItem("Test", MenuAction.CUSTOM)
        
        # Should not raise exception
        self.menu.trigger_action(item)
    
    def test_trigger_action_callback_error(self):
        """Test triggering action with callback error."""
        callback = Mock(side_effect=Exception("Callback error"))
        item = MenuItem("Test", MenuAction.CUSTOM, callback=callback)
        
        # Should catch exception
        self.menu.trigger_action(item)
        callback.assert_called_once()
    
    def test_trigger_action_handler_error(self):
        """Test triggering action with handler error."""
        handler = Mock(side_effect=Exception("Handler error"))
        self.menu.register_handler(MenuAction.CUSTOM, handler)
        
        item = MenuItem("Test", MenuAction.CUSTOM)
        
        # Should catch exception
        self.menu.trigger_action(item)
        handler.assert_called_once()
    
    def test_create_submenu(self):
        """Test creating submenu."""
        items = [
            MenuItem("Sub1", MenuAction.CUSTOM),
            MenuItem("Sub2", MenuAction.CUSTOM)
        ]
        
        submenu = self.menu.create_submenu(items)
        
        self.assertEqual(submenu, items)
    
    def test_add_separator(self):
        """Test adding separator."""
        original_count = len(self.menu.get_items())
        
        separator = self.menu.add_separator()
        
        self.assertIsInstance(separator, MenuItem)
        self.assertEqual(separator.label, "")
        self.assertEqual(separator.action, MenuAction.SEPARATOR)
        
        # Check separator was added
        items = self.menu.get_items()
        self.assertEqual(len(items), original_count + 1)
        self.assertIn(separator, items)
    
    def test_add_separator_with_position(self):
        """Test adding separator at specific position."""
        separator = self.menu.add_separator(position=0)
        
        items = self.menu.get_items()
        self.assertEqual(items[0], separator)
    
    def test_clear(self):
        """Test clearing menu."""
        # Add custom item
        self.menu.add_item("Custom", MenuAction.CUSTOM)
        
        # Clear menu
        self.menu.clear()
        
        items = self.menu.get_items()
        self.assertEqual(len(items), 0)
    
    def test_rebuild(self):
        """Test rebuilding menu."""
        # Clear and add custom items
        self.menu.clear()
        self.menu.add_item("Custom", MenuAction.CUSTOM)
        
        # Rebuild to default
        self.menu.rebuild()
        
        items = self.menu.get_items()
        self.assertTrue(len(items) > 0)
        
        # Check default items are back
        actions = [item.action for item in items]
        self.assertIn(MenuAction.TOGGLE_RECOGNITION, actions)
        self.assertIn(MenuAction.QUIT, actions)
        
        # Custom item should be gone
        custom_items = [i for i in items if i.label == "Custom"]
        self.assertEqual(len(custom_items), 0)


class TestMenuIntegration(unittest.TestCase):
    """Test menu integration scenarios."""
    
    def test_full_menu_workflow(self):
        """Test complete menu workflow."""
        menu = TrayMenu()
        
        # Register handlers
        handlers = {
            MenuAction.TOGGLE_RECOGNITION: Mock(),
            MenuAction.OPEN_SETTINGS: Mock(),
            MenuAction.QUIT: Mock()
        }
        
        for action, handler in handlers.items():
            menu.register_handler(action, handler)
        
        # Add custom items
        custom_handler = Mock()
        custom_item = menu.add_item(
            "Custom Action",
            MenuAction.CUSTOM,
            callback=custom_handler
        )
        
        # Add separator
        menu.add_separator()
        
        # Trigger all actions
        for item in menu.get_items():
            if item.action != MenuAction.SEPARATOR:
                menu.trigger_action(item)
        
        # Check handlers were called
        for action, handler in handlers.items():
            if action in [MenuAction.TOGGLE_RECOGNITION, MenuAction.OPEN_SETTINGS, MenuAction.QUIT]:
                handler.assert_called()
        
        custom_handler.assert_called_once()
    
    def test_dynamic_menu_updates(self):
        """Test dynamic menu updates."""
        menu = TrayMenu()
        
        # Initial state
        toggle_item = menu.find_item(MenuAction.TOGGLE_RECOGNITION)
        original_label = toggle_item.label
        
        # Simulate recognition started
        menu.update_item(
            MenuAction.TOGGLE_RECOGNITION,
            label="停止识别",
            checked=True
        )
        
        toggle_item = menu.find_item(MenuAction.TOGGLE_RECOGNITION)
        self.assertEqual(toggle_item.label, "停止识别")
        self.assertTrue(toggle_item.checked)
        
        # Simulate recognition stopped
        menu.update_item(
            MenuAction.TOGGLE_RECOGNITION,
            label="开始识别",
            checked=False
        )
        
        toggle_item = menu.find_item(MenuAction.TOGGLE_RECOGNITION)
        self.assertEqual(toggle_item.label, "开始识别")
        self.assertFalse(toggle_item.checked)
    
    def test_menu_with_submenu(self):
        """Test menu with submenu structure."""
        menu = TrayMenu()
        
        # Create submenu items
        sub_items = [
            MenuItem("Option 1", MenuAction.CUSTOM, data={"id": 1}),
            MenuItem("Option 2", MenuAction.CUSTOM, data={"id": 2}),
            MenuItem("", MenuAction.SEPARATOR),
            MenuItem("Option 3", MenuAction.CUSTOM, data={"id": 3})
        ]
        
        # Add parent item with submenu
        parent = menu.add_item(
            "Options",
            MenuAction.CUSTOM,
            submenu=sub_items
        )
        
        self.assertIsNotNone(parent.submenu)
        self.assertEqual(len(parent.submenu), 4)
        
        # Test finding items in submenu
        for sub_item in sub_items:
            if sub_item.action != MenuAction.SEPARATOR:
                found = menu.find_item(sub_item.action)
                self.assertIsNotNone(found)
    
    def test_menu_state_management(self):
        """Test menu state management."""
        menu = TrayMenu()
        
        # Track state changes
        state = {
            'recognition_active': False,
            'settings_open': False
        }
        
        def toggle_recognition(item):
            state['recognition_active'] = not state['recognition_active']
            menu.update_item(
                MenuAction.TOGGLE_RECOGNITION,
                label="停止识别" if state['recognition_active'] else "开始识别",
                checked=state['recognition_active']
            )
        
        def open_settings(item):
            state['settings_open'] = True
            menu.update_item(
                MenuAction.OPEN_SETTINGS,
                enabled=False  # Disable while open
            )
        
        # Register handlers
        menu.register_handler(MenuAction.TOGGLE_RECOGNITION, toggle_recognition)
        menu.register_handler(MenuAction.OPEN_SETTINGS, open_settings)
        
        # Test state changes
        toggle_item = menu.find_item(MenuAction.TOGGLE_RECOGNITION)
        settings_item = menu.find_item(MenuAction.OPEN_SETTINGS)
        
        # Toggle recognition
        menu.trigger_action(toggle_item)
        self.assertTrue(state['recognition_active'])
        toggle_item = menu.find_item(MenuAction.TOGGLE_RECOGNITION)
        self.assertEqual(toggle_item.label, "停止识别")
        self.assertTrue(toggle_item.checked)
        
        # Open settings
        menu.trigger_action(settings_item)
        self.assertTrue(state['settings_open'])
        settings_item = menu.find_item(MenuAction.OPEN_SETTINGS)
        self.assertFalse(settings_item.enabled)


if __name__ == '__main__':
    unittest.main()