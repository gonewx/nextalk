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
    # These are simple placeholder icons - replace with actual icons
    ICONS = {
        "idle_light": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAAN5JREFUOI2lk7ENwjAQRZ+NC0QBDRUjZAIqRmAEJqBiBEZgAipGYAQm
        oKKioSAFEsL5XSAhJMdx4Euvs+/e/bPPBiBlDhiNRhNgCXSBFngAF+AInPM8v/5KMABWwMN5FE/g
        DByAnd8gABbAzQMu6gHLLghMnaSviXbANAJ8EAKTENiqCYCx89ACm4gAwEYNuiH4JyAMdBWhI0kS
        WqAqEQBUatDS0apEAFC7XqthSwReJQKAl7M8iQlO7qJOTHBwVuxF4O5fMQDuwMUJbEWg8ldaAFs1
        UL8RiXKJzLJ+AN0aN+9KCqy+AAAAAElFTkSuQmCC
        """,
        "idle_dark": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAANlJREFUOI2lk7EOwjAMRJ+bFIkBNjYmPgEmNn4BP4A/gF+AiY2JjQkm
        JDYGBqRKbXwOqFJpnbaoXGLZ5+d7dhwACRkwGAz6wBxoAy/gDpyBPXDIsuxWRTAAFsDdeRQP4Ahs
        gU3RoAUsgasDXNQFFk0QGJP0NdEWGEeAD0JgFAJrJQEwdB5aYBkRAFioQTsE/wSEgY4i1CdJ0gKV
        RQBQqUFTRysTAUDleq2GLRCoiwQAtZtVJSY4uYvaMcHOmb0VgZt/xQC4AScnsBABX78SCSySrB6A
        H/FFN6b+mjD3AAAAAElFTkSuQmCC
        """,
        "active_light": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAAONJREFUOI2lkzEOgjAUhv9XqIkDm5sbJ/AEbnoCT+AJ3NzcOIEncHNz
        c+MEJm5ubCYOJBDK60BE0BYV/5fm9X3f+/teWwA5c8BoNJoAC6AL1MADOAMHYJdl2eVXggGwBO7O
        o3gAJ2ADbP0GLWAOXBzgoi6waILAmKSviXbAJAJ8EAKjEFgpCYCB81ADiwgAgLkatEPwT0AY6ChC
        fZIkLVCRCAAqNWjqaFkiAChdr6dhSwTKMgFA6Wq5iQmO7qJWTLBzZm9F4OpfMQCuwNEJzEXg00ck
        siUyy/oBeMBNOKF2TFMAAAAASUVORK5CYII=
        """,
        "active_dark": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAAOBJREFUOI2lkzEOgjAUhv9XSEwc2NzcOAEncNMTeAJP4Obm5glO4Obm
        5glM3NzYmDiQQCgvgYigLSr+L83r+7739722AHLmgOFw2AemQBuogDtwAnbAJs2y8/cEPWAG3JxH
        cQf2wApY+g2awAS4OMBFnWHeBIEBSV8TbYFRBPggBAYhsFQSAD3noQJmEQEAMzVoh+CfgDDQUYR6
        JElaoCQRAJRq0NTRkkQAULheT8MWCBQlAoDC1XITE+zcRc2YYOvMXorAxb9iAFyAnRMYi8C7j0hk
        S2SW9QPEqk0+nz4VcAAAAABJRU5ErkJggg==
        """,
        "error_light": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAAPFJREFUOI2lkzEOgjAYhb9fqYkDGxsbJ+AEbnoCT+AJ3NjcOIEncHNj
        YwImbnZwMIFQWgciQluU+Cbv9b3vvX/7A8iZA/r9/ghYAB2gAh7AGdgD2yzLLr8S9IElcHcexQM4
        AVtg4zdog3PgykEu6gqLJgiMSPqaaAdMIsAHITAMgbWSAOg7DxWwiAgAmKtBKwT/BISBliLUI0nS
        ApVFAFCpQUNHyxIBQOl6PQ1bIlCWCQBKV8tNTHB0F7Vigp0zeysCV/+KAXAFjk5gLgKfPiKRLZFZ
        1g/Vy03JMhNQrQAAAABJRU5ErkJggg==
        """,
        "error_dark": """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAAOBJREFUOI2lkzEOgjAUhv9XqIkDm5sbJ/AEbnoCT+AJ3Nzc2DiBm5sb
        JzBxc3MzcSCBUF4CUUFbVPxfmtf3fe997W8B5MwBg8FgDCyADlADD+AC7IFdlmXnXwn6wBK4O4/i
        AZyALbDxG7SBGXB1gIu6wKIJAiOSvibaAdMI8EEIDENgrSQA+s5DDSwiAgDmatAKwT8BYaClCPVI
        krRAZREAVGrQ1NGSRABQuF5Pw5YIFCUCgMLVchMT7NxFzZhg68xeisDFv2IAXIGdExiLwLuPSGRL
        ZJb1A73Rzj2Ys+N6AAAAASUVORK5CYII=
        """,
    }
    
    def __init__(self, theme: IconTheme = IconTheme.AUTO):
        """
        Initialize the icon manager.
        
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
        
        # Check cache
        if icon_key in self._icon_cache:
            return self._icon_cache[icon_key]
        
        # Try to load from file first
        icon_data = self._load_icon_from_file(icon_key)
        
        if not icon_data:
            # Fall back to embedded icon
            icon_data = self._get_embedded_icon(icon_key)
        
        # Cache the icon
        if icon_data:
            self._icon_cache[icon_key] = icon_data
        
        return icon_data
    
    def _get_theme_suffix(self) -> str:
        """Get the theme suffix based on current theme setting."""
        if self.theme == IconTheme.LIGHT:
            return "light"
        elif self.theme == IconTheme.DARK:
            return "dark"
        else:
            # Auto-detect based on system theme
            # For now, default to light
            return "light"
    
    def _load_icon_from_file(self, icon_key: str) -> Optional[bytes]:
        """
        Load icon from file.
        
        Args:
            icon_key: Icon key (e.g., "idle_light")
            
        Returns:
            Icon data as bytes, or None if not found
        """
        icon_path = self._icons_dir / f"{icon_key}.png"
        
        if icon_path.exists():
            try:
                with open(icon_path, 'rb') as f:
                    return f.read()
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
            # Decode base64 icon data
            icon_b64 = self.ICONS[icon_key].strip().replace('\n', '').replace(' ', '')
            try:
                return base64.b64decode(icon_b64)
            except Exception as e:
                # Log as debug, not error, since we have fallbacks
                from logging import getLogger
                logger = getLogger(__name__)
                logger.debug(f"Failed to decode embedded icon {icon_key}: {e}")
        
        # Return a default icon if not found
        return self._get_default_icon()
    
    def _get_default_icon(self) -> bytes:
        """Get default icon data."""
        # Simple 16x16 gray square as fallback
        default_b64 = """
        iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
        AAALEwAACxMBAJqcGAAAADxJREFUOI1jYBgFwwAw0tIAFhYWFgZGRkYGBgYGhv///zMwMDAw/P//
        n4GRkZGBhYWFgZGREQAaQBsXAADUaAbvqm8KjAAAAABJRU5ErkJggg==
        """
        return base64.b64decode(default_b64.strip().replace('\n', '').replace(' ', ''))
    
    def set_theme(self, theme: IconTheme) -> None:
        """
        Set the icon theme.
        
        Args:
            theme: New theme to use
        """
        self.theme = theme
        # Clear cache to reload icons with new theme
        self._icon_cache.clear()
    
    def clear_cache(self) -> None:
        """Clear the icon cache."""
        self._icon_cache.clear()