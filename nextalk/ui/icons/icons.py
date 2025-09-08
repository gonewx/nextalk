"""
Icon management for NexTalk system tray.

Provides icon resources and theme management.
"""

import os
import base64
from enum import Enum
from typing import Optional, Dict
from pathlib import Path


class IconTheme(Enum):
    """Icon theme options."""
    AUTO = "auto"
    LIGHT = "light"
    DARK = "dark"


class IconManager:
    """
    Manages icons for the system tray.
    
    Provides theme-aware icon selection and embedded icon resources.
    """
    
    # Base64 encoded PNG icons (16x16)
    # Simple reliable solid color icons
    ICONS = {
        "idle_light": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGNsaGhgIAUwkaR6VMOohiGlAQDJTAGgLgFHggAAAABJRU5ErkJggg==",  # Gray
        "idle_dark": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGNsaGhgIAUwkaR6VMOohiGlAQDJTAGgLgFHggAAAABJRU5ErkJggg==",  # Gray
        "active_light": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGklEQVR4nGP4jxvBREsYVToaXsNtNJZGNwwpDQAKBQEMTBgJeAAAAABJRU5ErkJggg==",  # Green
        "active_dark": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGklEQVR4nGP4jxvBREsYVToaXsNtNJZGNwwpDQAKBQEMTBgJeAAAAABJRU5ErkJggg==",  # Green  
        "error_light": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGP8//8/AymAiSTVoxpGNQwpDQBlMwGrOwI8/wAAAABJRU5ErkJggg==",  # Red
        "error_dark": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGP8//8/AymAiSTVoxpGNQwpDQBlMwGrOwI8/wAAAABJRU5ErkJggg=="  # Red
    }
    
    def __init__(self, theme: IconTheme = IconTheme.AUTO):
        """
        Initialize icon manager.
        
        Args:
            theme: Icon theme to use
        """
        self.theme = theme
        self._icons_dir = self._get_icons_directory()
        self._icon_cache: Dict[str, bytes] = {}
    
    def _get_icons_directory(self) -> Path:
        """Get the directory containing icon files."""
        # Try to find icons in package data
        package_dir = Path(__file__).parent
        icons_dir = package_dir / "icons"
        
        if not icons_dir.exists():
            # Create icons directory if it doesn't exist
            icons_dir.mkdir(parents=True, exist_ok=True)
        
        return icons_dir
    
    def get_icon(self, status: str) -> bytes:
        """
        Get icon data for a given status.
        
        Args:
            status: Status name (idle, active, error)
            
        Returns:
            Icon data as bytes
        """
        # Determine theme
        theme_suffix = self._get_theme_suffix()
        icon_key = f"{status}_{theme_suffix}"
        
        # Try to load from file first
        icon_data = self._load_icon_from_file(icon_key)
        
        return icon_data
    
    def _get_theme_suffix(self) -> str:
        """Get the theme suffix based on current theme setting."""
        if self.theme == IconTheme.LIGHT:
            return "light"
        elif self.theme == IconTheme.DARK:
            return "dark"
        else:
            # Auto-detect based on system theme
            return self._detect_system_theme()
    
    def _detect_system_theme(self) -> str:
        """
        Detect system theme.
        
        Returns:
            Theme suffix (light/dark)
        """
        try:
            # Try to detect GTK theme
            gtk_theme = os.environ.get('GTK_THEME', '').lower()
            if 'dark' in gtk_theme:
                return "dark"
            
            # Check for KDE theme
            kde_theme = os.environ.get('KDE_SESSION_VERSION', '')
            if kde_theme:
                # KDE theme detection would be more complex
                pass
            
            # Default to light theme
            return "light"
            
        except:
            return "light"
    
    def _load_icon_from_file(self, icon_key: str) -> Optional[bytes]:
        """
        Load icon from file.
        
        Args:
            icon_key: Icon key (e.g., "idle_light")
            
        Returns:
            Icon data or None if not found
        """
        try:
            icon_file = self._icons_dir / f"{icon_key}.png"
            if icon_file.exists():
                return icon_file.read_bytes()
        except Exception:
            pass
        
        return None
    
    def _get_embedded_icon(self, icon_key: str) -> bytes:
        """
        Get embedded icon data.
        
        Args:
            icon_key: Icon key (e.g., "idle_light")
            
        Returns:
            Icon data as bytes
        """
        if icon_key in self.ICONS:
            try:
                return base64.b64decode(self.ICONS[icon_key])
            except Exception:
                pass
        
        # Fallback to a simple default icon
        return self._create_default_icon()
    
    def _create_default_icon(self) -> bytes:
        """
        Create a default icon as fallback.
        
        Returns:
            Default icon data
        """
        # Simple 16x16 gray square PNG
        default_icon_b64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGUlEQVR4nGNsaGhgIAUwkaR6VMOohiGlAQDJTAGgLgFHggAAAABJRU5ErkJggg=="
        try:
            return base64.b64decode(default_icon_b64)
        except:
            # Last resort: return empty bytes
            return b''