"""
Global hotkey management for NexTalk.

Provides high-level hotkey registration and management with conflict detection.
"""

import logging
import threading
from typing import Callable, Optional, Dict, List, Set
from dataclasses import dataclass
import time

from ..config.models import HotkeyConfig
from .listener import KeyListener, HotkeyEvent, KeyEventType


logger = logging.getLogger(__name__)


@dataclass
class HotkeyRegistration:
    """Represents a registered hotkey."""
    hotkey: str
    callback: Callable
    description: str
    enabled: bool = True
    last_triggered: Optional[float] = None
    trigger_count: int = 0


class HotkeyConflictError(Exception):
    """Raised when a hotkey conflicts with an existing registration."""
    pass


class HotkeyManager:
    """
    Manages global hotkeys for the application.
    
    Provides hotkey registration, conflict detection, and configuration management.
    """
    
    def __init__(self, config: Optional[HotkeyConfig] = None):
        """
        Initialize the hotkey manager.
        
        Args:
            config: Hotkey configuration
        """
        self.config = config or HotkeyConfig()
        self._listener = KeyListener()
        self._registrations: Dict[str, HotkeyRegistration] = {}
        self._lock = threading.Lock()
        self._started = False
        
        # Sound feedback
        self._sound_enabled = self.config.enable_sound_feedback
        
        # Conflict detection
        self._conflict_detection = self.config.conflict_detection
        
        # Cooldown to prevent rapid triggering
        self._cooldown_ms = 200  # 200ms between triggers
        self._last_trigger_times: Dict[str, float] = {}
        
        # Add listener callback for events
        self._listener.add_callback(self._on_hotkey_event)
    
    def start(self) -> None:
        """Start the hotkey manager and begin listening."""
        with self._lock:
            if self._started:
                logger.warning("HotkeyManager already started")
                return
            
            self._listener.start()
            self._started = True
            
            # Register configured hotkeys
            self._register_default_hotkeys()
            
            logger.info("HotkeyManager started")
    
    def stop(self) -> None:
        """Stop the hotkey manager."""
        with self._lock:
            if not self._started:
                return
            
            self._listener.stop()
            self._started = False
            self._registrations.clear()
            self._last_trigger_times.clear()
            
            logger.info("HotkeyManager stopped")
    
    def is_running(self) -> bool:
        """Check if the manager is running."""
        return self._started
    
    def register_press_release(
        self,
        hotkey: str,
        on_press: Callable = None,
        on_release: Callable = None,
        description: str = "",
        check_conflicts: bool = True
    ) -> None:
        """
        Register a hotkey with separate press and release callbacks.
        
        Args:
            hotkey: Hotkey combination (e.g., "ctrl+alt+space")
            on_press: Function to call when hotkey is pressed
            on_release: Function to call when hotkey is released
            description: Description of what the hotkey does
            check_conflicts: Whether to check for conflicts
            
        Raises:
            HotkeyConflictError: If hotkey conflicts with existing registration
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            
            # Check for conflicts
            if check_conflicts and self._conflict_detection:
                conflicts = self._check_conflicts(normalized)
                if conflicts:
                    conflict_desc = ", ".join([
                        f"{h} ({r.description})" for h, r in conflicts
                    ])
                    raise HotkeyConflictError(
                        f"Hotkey '{hotkey}' conflicts with: {conflict_desc}"
                    )
            
            # Create registration
            registration = HotkeyRegistration(
                hotkey=normalized,
                callback=on_press,  # Store press callback as main callback
                description=description or f"Press/Release Hotkey: {normalized}"
            )
            
            # Register with listener
            self._listener.register_press_release_hotkey(normalized, on_press, on_release)
            
            # Store registration
            self._registrations[normalized] = registration
            
            logger.info(f"Registered press/release hotkey: {normalized} - {description}")
    
    def register(
        self,
        hotkey: str,
        callback: Callable,
        description: str = "",
        check_conflicts: bool = True
    ) -> None:
        """
        Register a global hotkey.
        
        Args:
            hotkey: Hotkey combination (e.g., "ctrl+alt+space")
            callback: Function to call when hotkey is triggered
            description: Description of what the hotkey does
            check_conflicts: Whether to check for conflicts
            
        Raises:
            HotkeyConflictError: If hotkey conflicts with existing registration
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            
            # Check for conflicts
            if check_conflicts and self._conflict_detection:
                conflicts = self._check_conflicts(normalized)
                if conflicts:
                    conflict_desc = ", ".join([
                        f"{h} ({r.description})" for h, r in conflicts
                    ])
                    raise HotkeyConflictError(
                        f"Hotkey '{hotkey}' conflicts with: {conflict_desc}"
                    )
            
            # Create registration
            registration = HotkeyRegistration(
                hotkey=normalized,
                callback=callback,
                description=description or f"Hotkey: {normalized}"
            )
            
            # Register with listener
            self._listener.register_hotkey(normalized, lambda: self._trigger_hotkey(normalized))
            
            # Store registration
            self._registrations[normalized] = registration
            
            logger.info(f"Registered hotkey: {normalized} - {description}")
    
    def unregister(self, hotkey: str) -> None:
        """
        Unregister a hotkey.
        
        Args:
            hotkey: Hotkey combination to unregister
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            
            if normalized in self._registrations:
                # Unregister from listener
                self._listener.unregister_hotkey(normalized)
                
                # Remove registration
                del self._registrations[normalized]
                
                # Clear trigger time
                self._last_trigger_times.pop(normalized, None)
                
                logger.info(f"Unregistered hotkey: {normalized}")
    
    def set_enabled(self, hotkey: str, enabled: bool) -> None:
        """
        Enable or disable a hotkey.
        
        Args:
            hotkey: Hotkey combination
            enabled: Whether to enable or disable
        """
        with self._lock:
            normalized = self._normalize_hotkey(hotkey)
            
            if normalized in self._registrations:
                self._registrations[normalized].enabled = enabled
                logger.debug(f"Hotkey {normalized} {'enabled' if enabled else 'disabled'}")
    
    def is_registered(self, hotkey: str) -> bool:
        """
        Check if a hotkey is registered.
        
        Args:
            hotkey: Hotkey combination to check
            
        Returns:
            True if registered, False otherwise
        """
        normalized = self._normalize_hotkey(hotkey)
        return normalized in self._registrations
    
    def get_registrations(self) -> List[HotkeyRegistration]:
        """Get all registered hotkeys."""
        with self._lock:
            return list(self._registrations.values())
    
    def validate_hotkey(self, hotkey: str) -> List[str]:
        """
        Validate a hotkey string.
        
        Args:
            hotkey: Hotkey string to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not hotkey:
            errors.append("Hotkey cannot be empty")
            return errors
        
        parts = [p.strip().lower() for p in hotkey.split("+")]
        
        if len(parts) == 0:
            errors.append("Invalid hotkey format")
            return errors
        
        # Check for valid modifiers
        valid_modifiers = {"ctrl", "alt", "shift", "cmd", "meta"}
        modifiers = []
        keys = []
        
        for part in parts:
            if part in valid_modifiers:
                modifiers.append(part)
            else:
                keys.append(part)
        
        # Must have at least one non-modifier key
        if len(keys) == 0:
            errors.append("Hotkey must include at least one non-modifier key")
        
        # Check for duplicate modifiers
        if len(modifiers) != len(set(modifiers)):
            errors.append("Duplicate modifier keys")
        
        # Validate key names (basic check)
        valid_keys = {
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "space", "enter", "tab", "escape", "backspace", "delete",
            "home", "end", "page_up", "page_down",
            "up", "down", "left", "right",
            "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"
        }
        
        for key in keys:
            if key not in valid_keys and not key.startswith("vk_"):
                errors.append(f"Invalid key: {key}")
        
        return errors
    
    def _normalize_hotkey(self, hotkey: str) -> str:
        """
        Normalize a hotkey string for consistent comparison.
        
        Args:
            hotkey: Hotkey string
            
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
    
    def _check_conflicts(self, hotkey: str) -> List[tuple[str, HotkeyRegistration]]:
        """
        Check if a hotkey conflicts with existing registrations.
        
        Args:
            hotkey: Normalized hotkey string
            
        Returns:
            List of conflicting (hotkey, registration) tuples
        """
        conflicts = []
        
        # Direct conflict - exact match
        if hotkey in self._registrations:
            conflicts.append((hotkey, self._registrations[hotkey]))
        
        # Check for subset conflicts (e.g., "ctrl+a" conflicts with "ctrl+shift+a")
        hotkey_parts = set(hotkey.split("+"))
        
        for registered, registration in self._registrations.items():
            if registered == hotkey:
                continue  # Already checked
            
            registered_parts = set(registered.split("+"))
            
            # Check if one is a subset of the other
            if hotkey_parts.issubset(registered_parts) or registered_parts.issubset(hotkey_parts):
                # Additional logic could be added here for more sophisticated conflict detection
                pass
        
        return conflicts
    
    def _trigger_hotkey(self, hotkey: str) -> None:
        """
        Trigger a hotkey callback.
        
        Args:
            hotkey: Normalized hotkey string
        """
        # Check cooldown
        current_time = time.time() * 1000  # Convert to milliseconds
        last_trigger = self._last_trigger_times.get(hotkey, 0)
        
        if current_time - last_trigger < self._cooldown_ms:
            logger.debug(f"Hotkey {hotkey} triggered too quickly, ignoring")
            return
        
        registration = self._registrations.get(hotkey)
        if not registration:
            return
        
        if not registration.enabled:
            logger.debug(f"Hotkey {hotkey} is disabled")
            return
        
        # Update trigger time
        self._last_trigger_times[hotkey] = current_time
        
        # Update registration stats
        registration.last_triggered = time.time()
        registration.trigger_count += 1
        
        # Play sound feedback if enabled
        if self._sound_enabled:
            self._play_feedback_sound()
        
        # Call the callback
        try:
            registration.callback()
        except Exception as e:
            logger.error(f"Error in hotkey callback for {hotkey}: {e}")
    
    def _on_hotkey_event(self, event: HotkeyEvent) -> None:
        """
        Handle hotkey events from the listener.
        
        Args:
            event: Hotkey event
        """
        # Log the event for debugging
        logger.debug(f"Hotkey event: {event.hotkey} ({event.event_type.value})")
    
    def _register_default_hotkeys(self) -> None:
        """Register default hotkeys from configuration."""
        # These will be registered by the main controller
        # Just log what's configured
        logger.info(f"Configured trigger key: {self.config.trigger_key}")
        logger.info(f"Configured stop key: {self.config.stop_key}")
    
    def _play_feedback_sound(self) -> None:
        """Play audio feedback for hotkey activation."""
        # TODO: Implement actual sound playback
        # For now, just log
        logger.debug("Playing feedback sound (not implemented)")
    
    def get_statistics(self) -> Dict[str, dict]:
        """
        Get usage statistics for registered hotkeys.
        
        Returns:
            Dictionary mapping hotkey to statistics
        """
        with self._lock:
            stats = {}
            for hotkey, registration in self._registrations.items():
                stats[hotkey] = {
                    "description": registration.description,
                    "enabled": registration.enabled,
                    "trigger_count": registration.trigger_count,
                    "last_triggered": registration.last_triggered
                }
            return stats