"""
Keyboard listener and event handling for NexTalk.

Provides low-level keyboard event monitoring and hotkey detection.
"""

import logging
import threading
from typing import Callable, Optional, Set, List
from dataclasses import dataclass
from enum import Enum
from pynput import keyboard
from pynput.keyboard import Key, KeyCode


logger = logging.getLogger(__name__)


class KeyEventType(Enum):
    """Types of keyboard events."""
    PRESS = "press"
    RELEASE = "release"


@dataclass
class HotkeyEvent:
    """Represents a hotkey event."""
    hotkey: str
    event_type: KeyEventType
    timestamp: float
    modifiers: Set[str]
    key: Optional[str] = None


class KeyListener:
    """
    Low-level keyboard listener using pynput.
    
    Handles keyboard event monitoring and hotkey detection.
    """
    
    def __init__(self):
        """Initialize the key listener."""
        self._listener: Optional[keyboard.Listener] = None
        self._callbacks: List[Callable[[HotkeyEvent], None]] = []
        self._running = False
        self._lock = threading.Lock()
        
        # Current key states
        self._pressed_keys: Set[str] = set()
        self._pressed_modifiers: Set[str] = set()
        
        # Hotkey registration
        self._registered_hotkeys: dict[str, Callable] = {}
        self._press_callbacks: dict[str, Callable] = {}
        self._release_callbacks: dict[str, Callable] = {}
        
        # Modifier key mapping
        self._modifier_map = {
            Key.ctrl_l: "ctrl",
            Key.ctrl_r: "ctrl",
            Key.alt_l: "alt",
            Key.alt_r: "alt",
            Key.alt_gr: "alt",
            Key.shift_l: "shift",
            Key.shift_r: "shift",
            Key.cmd: "cmd",
            Key.cmd_l: "cmd",
            Key.cmd_r: "cmd",
        }
        
        # Special key mapping
        self._special_key_map = {
            Key.space: "space",
            Key.enter: "enter",
            Key.tab: "tab",
            Key.esc: "escape",
            Key.backspace: "backspace",
            Key.delete: "delete",
            Key.home: "home",
            Key.end: "end",
            Key.page_up: "page_up",
            Key.page_down: "page_down",
            Key.up: "up",
            Key.down: "down",
            Key.left: "left",
            Key.right: "right",
            Key.f1: "f1",
            Key.f2: "f2",
            Key.f3: "f3",
            Key.f4: "f4",
            Key.f5: "f5",
            Key.f6: "f6",
            Key.f7: "f7",
            Key.f8: "f8",
            Key.f9: "f9",
            Key.f10: "f10",
            Key.f11: "f11",
            Key.f12: "f12",
        }
    
    def start(self) -> None:
        """Start the keyboard listener."""
        with self._lock:
            if self._running:
                logger.warning("KeyListener already running")
                return
            
            self._running = True
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self._listener.start()
            logger.info("Keyboard listener started")
    
    def stop(self) -> None:
        """Stop the keyboard listener."""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            if self._listener:
                try:
                    self._listener.stop()
                except Exception as e:
                    logger.warning(f"Error stopping keyboard listener: {e}")
                finally:
                    self._listener = None
            
            self._pressed_keys.clear()
            self._pressed_modifiers.clear()
            logger.info("Keyboard listener stopped")
    
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> None:
        """
        Register a hotkey with a callback function.
        
        Args:
            hotkey: Hotkey combination (e.g., "ctrl+alt+space")
            callback: Function to call when hotkey is triggered
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            self._registered_hotkeys[normalized] = callback
            logger.debug(f"Registered hotkey: {normalized}")
    
    def register_press_release_hotkey(self, hotkey: str, on_press: Callable = None, on_release: Callable = None) -> None:
        """
        Register a hotkey with separate press and release callbacks.
        
        Args:
            hotkey: Hotkey combination (e.g., "ctrl+alt+space")
            on_press: Function to call when hotkey is pressed
            on_release: Function to call when hotkey is released
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            if on_press:
                self._press_callbacks[normalized] = on_press
            if on_release:
                self._release_callbacks[normalized] = on_release
            logger.debug(f"Registered press/release hotkey: {normalized} (press: {on_press is not None}, release: {on_release is not None})")
    
    def unregister_hotkey(self, hotkey: str) -> None:
        """
        Unregister a hotkey.
        
        Args:
            hotkey: Hotkey combination to unregister
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            if normalized in self._registered_hotkeys:
                del self._registered_hotkeys[normalized]
                logger.debug(f"Unregistered hotkey: {normalized}")
    
    def add_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
        """Add a callback for all hotkey events."""
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[HotkeyEvent], None]) -> None:
        """Remove a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _normalize_hotkey(self, hotkey: str) -> str:
        """
        Normalize a hotkey string for consistent comparison.
        
        Args:
            hotkey: Hotkey string (e.g., "ctrl+alt+space")
            
        Returns:
            Normalized hotkey string
        """
        parts = [p.strip().lower() for p in hotkey.split("+")]
        
        # Separate modifiers and key
        modifiers = []
        key = None
        
        modifier_names = {"ctrl", "alt", "shift", "cmd", "meta"}
        
        for part in parts:
            if part in modifier_names:
                if part == "meta":
                    part = "cmd"  # Normalize meta to cmd
                modifiers.append(part)
            else:
                key = part
        
        # Sort modifiers for consistent ordering
        modifiers.sort()
        
        # Reconstruct hotkey
        if key:
            return "+".join(modifiers + [key])
        else:
            return "+".join(modifiers)
    
    def _get_key_name(self, key) -> Optional[str]:
        """
        Get the name of a key.
        
        Args:
            key: pynput Key or KeyCode object
            
        Returns:
            Key name as string, or None if unrecognized
        """
        # Check if it's a modifier
        if key in self._modifier_map:
            return self._modifier_map[key]
        
        # Check if it's a special key
        if key in self._special_key_map:
            return self._special_key_map[key]
        
        # Check if it's a regular character key
        if isinstance(key, KeyCode):
            if key.char:
                return key.char.lower()
            elif key.vk:
                # Virtual key code (for special keys not in char)
                return f"vk_{key.vk}"
        
        return None
    
    def _on_press(self, key) -> None:
        """Handle key press events."""
        if not self._running:
            return
        
        key_name = self._get_key_name(key)
        if not key_name:
            return
        
        # Update modifier state
        if key_name in {"ctrl", "alt", "shift", "cmd"}:
            self._pressed_modifiers.add(key_name)
        else:
            self._pressed_keys.add(key_name)
        
        # Check for hotkey match
        self._check_hotkey_triggered(key_name, KeyEventType.PRESS)
    
    def _on_release(self, key) -> None:
        """Handle key release events."""
        if not self._running:
            return
        
        key_name = self._get_key_name(key)
        if not key_name:
            return
        
        logger.info(f"Key released: {key_name}, modifiers: {self._pressed_modifiers}, keys: {self._pressed_keys}")
        
        # Check for hotkey match BEFORE updating state (important for release events)
        self._check_hotkey_triggered(key_name, KeyEventType.RELEASE)
        
        # Update modifier state AFTER checking hotkey
        if key_name in {"ctrl", "alt", "shift", "cmd"}:
            self._pressed_modifiers.discard(key_name)
        else:
            self._pressed_keys.discard(key_name)
    
    def _check_hotkey_triggered(self, key_name: str, event_type: KeyEventType) -> None:
        """
        Check if a registered hotkey has been triggered.
        
        Args:
            key_name: Name of the key that triggered the event
            event_type: Type of key event (press or release)
        """
        # For release events, we need to build the combo before the key state is updated
        # So we need to capture the state before _on_release updates it
        if event_type == KeyEventType.RELEASE:
            # Build combo using current state (before removal)
            current_combo = self._build_release_combo(key_name)
        else:
            # For press events, use normal combo building
            current_combo = self._build_current_combo(key_name)
        
        # Debug logging
        logger.info(f"Key event: {key_name} ({event_type.value}), combo: {current_combo}, modifiers: {self._pressed_modifiers}, keys: {self._pressed_keys}")
        if event_type == KeyEventType.RELEASE:
            logger.info(f"Registered release callbacks: {list(self._release_callbacks.keys())}")
        
        if not current_combo:
            return
        
        # Create hotkey event
        import time
        event = HotkeyEvent(
            hotkey=current_combo,
            event_type=event_type,
            timestamp=time.time(),
            modifiers=self._pressed_modifiers.copy(),
            key=key_name if key_name not in self._pressed_modifiers else None
        )
        
        # Check if it matches any registered hotkey (legacy)
        if current_combo in self._registered_hotkeys and event_type == KeyEventType.PRESS:
            callback = self._registered_hotkeys[current_combo]
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in hotkey callback: {e}")
        
        # Check for press/release specific callbacks
        if event_type == KeyEventType.PRESS and current_combo in self._press_callbacks:
            callback = self._press_callbacks[current_combo]
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in press callback: {e}")
        
        if event_type == KeyEventType.RELEASE and current_combo in self._release_callbacks:
            logger.info(f"Found release callback for: {current_combo}")
            callback = self._release_callbacks[current_combo]
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in release callback: {e}")
        
        # Call general callbacks
        if current_combo in self._registered_hotkeys or current_combo in self._press_callbacks or current_combo in self._release_callbacks:
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
    
    def _build_current_combo(self, current_key: str) -> Optional[str]:
        """
        Build the current key combination string.
        
        Args:
            current_key: The key that was just pressed/released
            
        Returns:
            Normalized hotkey combination string
        """
        # Don't build combo for modifier-only presses
        if current_key in {"ctrl", "alt", "shift", "cmd"}:
            return None
        
        if not self._pressed_modifiers:
            # No modifiers, just the key itself
            return current_key
        
        # Build combination with modifiers
        modifiers = sorted(list(self._pressed_modifiers))
        return "+".join(modifiers + [current_key])
    
    def _build_release_combo(self, current_key: str) -> Optional[str]:
        """
        Build the key combination string for release events.
        
        For release events, we need to construct the combo based on what WAS pressed
        before this key was released, since we want to match the full combination.
        
        Args:
            current_key: The key that was just released
            
        Returns:
            Normalized hotkey combination string that represents the full combo being released
        """
        # For release events, we check against all registered release callbacks
        # to see if the current pressed state (including the key being released) 
        # matches any registered combinations
        
        # Build the complete combination including the key being released
        if current_key in {"ctrl", "alt", "shift", "cmd"}:
            # Releasing a modifier - include it in the modifiers list
            all_modifiers = self._pressed_modifiers.copy()  # This still includes the current key
            if self._pressed_keys:
                # There are non-modifier keys pressed
                modifiers = sorted(list(all_modifiers))
                non_modifier_keys = sorted(list(self._pressed_keys))
                if non_modifier_keys:
                    combo = "+".join(modifiers + non_modifier_keys)
                    # Check if this matches any registered release callback
                    if combo in self._release_callbacks:
                        return combo
            return None
        else:
            # Releasing a non-modifier key - include all current modifiers
            if self._pressed_modifiers:
                modifiers = sorted(list(self._pressed_modifiers))
                combo = "+".join(modifiers + [current_key])
                # Check if this matches any registered release callback
                if combo in self._release_callbacks:
                    return combo
            else:
                # No modifiers, just the key
                if current_key in self._release_callbacks:
                    return current_key
        
        return None
    
    def get_pressed_keys(self) -> Set[str]:
        """Get currently pressed keys."""
        with self._lock:
            return self._pressed_keys.copy()
    
    def get_pressed_modifiers(self) -> Set[str]:
        """Get currently pressed modifier keys."""
        with self._lock:
            return self._pressed_modifiers.copy()