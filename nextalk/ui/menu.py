"""
System tray menu management for NexTalk.

Provides menu structure and action handling.
"""

import logging
from enum import Enum
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class MenuAction(Enum):
    """Predefined menu actions."""
    TOGGLE_RECOGNITION = "toggle_recognition"
    OPEN_SETTINGS = "open_settings"
    VIEW_STATISTICS = "view_statistics"
    ABOUT = "about"
    QUIT = "quit"
    SEPARATOR = "separator"
    CUSTOM = "custom"
    # IME related actions
    VIEW_IME_STATUS = "view_ime_status"
    TOGGLE_IME = "toggle_ime"
    IME_SETTINGS = "ime_settings"
    TEST_IME_INJECTION = "test_ime_injection"


@dataclass
class MenuItem:
    """Represents a menu item."""
    label: str
    action: MenuAction
    callback: Optional[Callable] = None
    enabled: bool = True
    checked: bool = False
    icon: Optional[str] = None
    shortcut: Optional[str] = None
    submenu: Optional[List['MenuItem']] = None
    data: Optional[Any] = None


class TrayMenu:
    """
    Manages the system tray context menu.
    
    Provides menu construction and action dispatch.
    """
    
    def __init__(self):
        """Initialize the tray menu."""
        self._items: List[MenuItem] = []
        self._action_handlers: Dict[MenuAction, Callable] = {}
        self._build_default_menu()
    
    def _build_default_menu(self) -> None:
        """Build the default menu structure."""
        self._items = [
            MenuItem(
                label="开始/停止识别",
                action=MenuAction.TOGGLE_RECOGNITION,
                shortcut="Ctrl+Alt+Space",
                icon="toggle"
            ),
            MenuItem(
                label="",
                action=MenuAction.SEPARATOR
            ),
            MenuItem(
                label="退出",
                action=MenuAction.QUIT,
                icon="exit"
            )
        ]
    
    def get_items(self) -> List[MenuItem]:
        """Get all menu items."""
        return self._items.copy()
    
    def add_item(
        self,
        label: str,
        action: MenuAction = MenuAction.CUSTOM,
        callback: Optional[Callable] = None,
        position: Optional[int] = None,
        **kwargs
    ) -> MenuItem:
        """
        Add a menu item.
        
        Args:
            label: Menu item label
            action: Menu action type
            callback: Callback function
            position: Position to insert at (None for end)
            **kwargs: Additional MenuItem parameters
            
        Returns:
            Created menu item
        """
        item = MenuItem(
            label=label,
            action=action,
            callback=callback,
            **kwargs
        )
        
        if position is not None:
            self._items.insert(position, item)
        else:
            self._items.append(item)
        
        logger.debug(f"Added menu item: {label}")
        return item
    
    def remove_item(self, item: MenuItem) -> bool:
        """
        Remove a menu item.
        
        Args:
            item: Menu item to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            self._items.remove(item)
            logger.debug(f"Removed menu item: {item.label}")
            return True
        except ValueError:
            return False
    
    def find_item(self, action: MenuAction) -> Optional[MenuItem]:
        """
        Find a menu item by action.
        
        Args:
            action: Action to search for
            
        Returns:
            Menu item if found, None otherwise
        """
        for item in self._items:
            if item.action == action:
                return item
            if item.submenu:
                for subitem in item.submenu:
                    if subitem.action == action:
                        return subitem
        return None
    
    def update_item(
        self,
        action: MenuAction,
        label: Optional[str] = None,
        enabled: Optional[bool] = None,
        checked: Optional[bool] = None,
        icon: Optional[str] = None
    ) -> bool:
        """
        Update a menu item.
        
        Args:
            action: Action of item to update
            label: New label
            enabled: New enabled state
            checked: New checked state
            icon: New icon
            
        Returns:
            True if updated, False if not found
        """
        item = self.find_item(action)
        if not item:
            return False
        
        if label is not None:
            item.label = label
        if enabled is not None:
            item.enabled = enabled
        if checked is not None:
            item.checked = checked
        if icon is not None:
            item.icon = icon
        
        logger.debug(f"Updated menu item: {action.value}")
        return True
    
    def register_handler(self, action: MenuAction, handler: Callable) -> None:
        """
        Register an action handler.
        
        Args:
            action: Menu action
            handler: Handler function
        """
        self._action_handlers[action] = handler
        logger.debug(f"Registered handler for: {action.value}")
    
    def trigger_action(self, item: MenuItem) -> None:
        """
        Trigger a menu item action.
        
        Args:
            item: Menu item that was activated
        """
        logger.info(f"Menu action triggered: {item.label}")
        
        # Check for custom callback first
        if item.callback:
            try:
                item.callback(item)
            except Exception as e:
                logger.error(f"Error in menu callback: {e}")
            return
        
        # Check for registered handler
        if item.action in self._action_handlers:
            handler = self._action_handlers[item.action]
            try:
                handler(item)
            except Exception as e:
                logger.error(f"Error in action handler: {e}")
        else:
            logger.warning(f"No handler for action: {item.action.value}")
    
    def create_submenu(self, items: List[MenuItem]) -> List[MenuItem]:
        """
        Create a submenu.
        
        Args:
            items: Menu items for submenu
            
        Returns:
            Submenu items
        """
        return items
    
    def add_separator(self, position: Optional[int] = None) -> MenuItem:
        """
        Add a separator to the menu.
        
        Args:
            position: Position to insert at
            
        Returns:
            Separator menu item
        """
        return self.add_item("", MenuAction.SEPARATOR, position=position)
    
    def clear(self) -> None:
        """Clear all menu items."""
        self._items.clear()
        logger.debug("Cleared all menu items")
    
    def rebuild(self) -> None:
        """Rebuild the menu to default state."""
        self.clear()
        self._build_default_menu()
        logger.debug("Rebuilt menu to default")