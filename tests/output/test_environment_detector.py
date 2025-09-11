"""
Unit tests for environment detector.

Tests desktop environment detection logic and tool availability checking
with comprehensive mocking of system environment variables and commands.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from nextalk.output.environment_detector import EnvironmentDetector
from nextalk.output.injection_models import (
    EnvironmentInfo, DesktopEnvironment, DisplayServerType,
    InjectionMethod
)


class TestEnvironmentDetector:
    """Test cases for EnvironmentDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create EnvironmentDetector instance."""
        return EnvironmentDetector()
    
    def test_detect_display_server_wayland_env_var(self, detector):
        """Test Wayland detection via environment variable."""
        with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}):
            result = detector._detect_display_server()
            assert result == DisplayServerType.WAYLAND
    
    def test_detect_display_server_x11_env_var(self, detector):
        """Test X11 detection via DISPLAY environment variable."""
        with patch.dict(os.environ, {'DISPLAY': ':0.0'}, clear=True):
            result = detector._detect_display_server()
            assert result == DisplayServerType.X11
    
    def test_detect_display_server_xwayland(self, detector):
        """Test XWayland detection (both DISPLAY and WAYLAND_DISPLAY set)."""
        env_vars = {'DISPLAY': ':0.0', 'WAYLAND_DISPLAY': 'wayland-0'}
        with patch.dict(os.environ, env_vars):
            result = detector._detect_display_server()
            # Should detect Wayland as primary (XWayland scenario)
            assert result == DisplayServerType.WAYLAND
    
    def test_detect_display_server_unknown(self, detector):
        """Test unknown display server detection."""
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(detector, '_check_wayland_compositor', return_value=False), \
             patch.object(detector, '_check_x11_server', return_value=False):
            result = detector._detect_display_server()
            assert result == DisplayServerType.UNKNOWN
    
    def test_detect_desktop_environment_gnome(self, detector):
        """Test GNOME desktop environment detection."""
        env_vars = {
            'XDG_CURRENT_DESKTOP': 'GNOME',
            'GDMSESSION': 'gnome'
        }
        with patch.dict(os.environ, env_vars):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.GNOME
    
    def test_detect_desktop_environment_kde(self, detector):
        """Test KDE desktop environment detection."""
        env_vars = {
            'XDG_CURRENT_DESKTOP': 'KDE',
            'KDE_SESSION_VERSION': '5'
        }
        with patch.dict(os.environ, env_vars):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.KDE
    
    def test_detect_desktop_environment_xfce(self, detector):
        """Test XFCE desktop environment detection."""
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'XFCE'}):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.XFCE
    
    def test_detect_desktop_environment_i3(self, detector):
        """Test i3 window manager detection."""
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'i3'}):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.I3
    
    def test_detect_desktop_environment_sway(self, detector):
        """Test Sway window manager detection."""
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'sway'}):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.SWAY
    
    def test_detect_desktop_environment_multiple_desktops(self, detector):
        """Test detection with multiple desktop environments."""
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'Unity:GNOME'}):
            result = detector._detect_desktop_environment()
            # Should detect the first recognized desktop
            assert result == DesktopEnvironment.GNOME
    
    def test_detect_desktop_environment_unknown(self, detector):
        """Test unknown desktop environment detection."""
        with patch.dict(os.environ, {'XDG_CURRENT_DESKTOP': 'CustomDE'}, clear=True):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.UNKNOWN
    
    def test_detect_desktop_environment_no_env_var(self, detector):
        """Test desktop environment detection without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            result = detector._detect_desktop_environment()
            assert result == DesktopEnvironment.UNKNOWN
    
    def test_check_portal_availability_dbus_available(self, detector):
        """Test Portal availability when DBus is available."""
        with patch('builtins.__import__') as mock_import:
            # Mock successful dbus import
            mock_dbus = Mock()
            mock_bus = Mock()
            mock_dbus.SessionBus.return_value = mock_bus
            
            # Mock successful portal object access
            mock_portal = Mock()
            mock_bus.get_object.return_value = mock_portal
            
            def import_side_effect(name, *args):
                if name == 'dbus':
                    return mock_dbus
                elif name == 'dbus.mainloop.glib':
                    return Mock()
                return __import__(name, *args)
            
            mock_import.side_effect = import_side_effect
            
            result = detector._check_portal_availability()
            assert result is True
    
    def test_check_portal_availability_import_error(self, detector):
        """Test Portal availability when DBus import fails."""
        with patch('builtins.__import__') as mock_import:
            def import_side_effect(name, *args):
                if name == 'dbus':
                    raise ImportError("No dbus module")
                return __import__(name, *args)
            
            mock_import.side_effect = import_side_effect
            
            result = detector._check_portal_availability()
            assert result is False
    
    def test_check_portal_availability_connection_error(self, detector):
        """Test Portal availability with connection error."""
        with patch('builtins.__import__') as mock_import:
            # Mock successful dbus import but connection failure
            mock_dbus = Mock()
            mock_dbus.SessionBus.side_effect = Exception("Connection failed")
            
            def import_side_effect(name, *args):
                if name == 'dbus':
                    return mock_dbus
                elif name == 'dbus.mainloop.glib':
                    return Mock()
                return __import__(name, *args)
            
            mock_import.side_effect = import_side_effect
            
            result = detector._check_portal_availability()
            assert result is False
    
    def test_check_portal_availability_portal_not_available(self, detector):
        """Test Portal availability when portal service is not available."""
        with patch('builtins.__import__') as mock_import:
            # Mock successful dbus import but portal service failure
            mock_dbus = Mock()
            mock_bus = Mock()
            mock_dbus.SessionBus.return_value = mock_bus
            
            # Mock portal object access failure
            mock_bus.get_object.side_effect = Exception("Portal not available")
            
            def import_side_effect(name, *args):
                if name == 'dbus':
                    return mock_dbus
                elif name == 'dbus.mainloop.glib':
                    return Mock()
                return __import__(name, *args)
            
            mock_import.side_effect = import_side_effect
            
            result = detector._check_portal_availability()
            assert result is False
    
    def test_check_xdotool_availability_found(self, detector):
        """Test xdotool availability when found."""
        with patch('shutil.which', return_value='/usr/bin/xdotool'):
            result = detector._check_xdotool_availability()
            assert result is True
    
    def test_check_xdotool_availability_not_found(self, detector):
        """Test xdotool availability when not found."""
        with patch('shutil.which', return_value=None):
            result = detector._check_xdotool_availability()
            assert result is False
    
    def test_get_available_methods_wayland_with_portal(self, detector):
        """Test available methods on Wayland with Portal."""
        with patch.object(detector, '_detect_display_server', return_value=DisplayServerType.WAYLAND), \
             patch.object(detector, '_check_portal_availability', return_value=True), \
             patch.object(detector, '_check_xdotool_availability', return_value=False):
            
            methods = detector._get_available_methods()
            assert InjectionMethod.PORTAL in methods
            assert InjectionMethod.XDOTOOL not in methods
    
    def test_get_available_methods_x11_with_xdotool(self, detector):
        """Test available methods on X11 with xdotool."""
        with patch.object(detector, '_detect_display_server', return_value=DisplayServerType.X11), \
             patch.object(detector, '_check_portal_availability', return_value=False), \
             patch.object(detector, '_check_xdotool_availability', return_value=True):
            
            methods = detector._get_available_methods()
            assert InjectionMethod.XDOTOOL in methods
            assert InjectionMethod.PORTAL not in methods
    
    def test_get_available_methods_both_available(self, detector):
        """Test available methods when both Portal and xdotool are available."""
        with patch.object(detector, '_detect_display_server', return_value=DisplayServerType.WAYLAND), \
             patch.object(detector, '_check_portal_availability', return_value=True), \
             patch.object(detector, '_check_xdotool_availability', return_value=True):
            
            methods = detector._get_available_methods()
            assert InjectionMethod.PORTAL in methods
            assert InjectionMethod.XDOTOOL in methods
    
    def test_get_available_methods_none_available(self, detector):
        """Test available methods when neither method is available."""
        with patch.object(detector, '_detect_display_server', return_value=DisplayServerType.UNKNOWN), \
             patch.object(detector, '_check_portal_availability', return_value=False), \
             patch.object(detector, '_check_xdotool_availability', return_value=False):
            
            methods = detector._get_available_methods()
            assert len(methods) == 0
    
    def test_detect_environment_complete_wayland_gnome(self, detector):
        """Test complete environment detection for Wayland GNOME."""
        env_vars = {
            'WAYLAND_DISPLAY': 'wayland-0',
            'XDG_CURRENT_DESKTOP': 'GNOME'
        }
        
        with patch.dict(os.environ, env_vars), \
             patch.object(detector, '_check_portal_availability', return_value=True), \
             patch.object(detector, '_check_xdotool_availability', return_value=False):
            
            env_info = detector.detect_environment()
            
            assert env_info.display_server == DisplayServerType.WAYLAND
            assert env_info.desktop_environment == DesktopEnvironment.GNOME_WAYLAND
            assert InjectionMethod.PORTAL in env_info.available_methods
            assert env_info.portal_available is True
            assert env_info.xdotool_available is False
    
    def test_detect_environment_complete_x11_kde(self, detector):
        """Test complete environment detection for X11 KDE."""
        env_vars = {
            'DISPLAY': ':0.0',
            'XDG_CURRENT_DESKTOP': 'KDE'
        }
        
        with patch.dict(os.environ, env_vars, clear=True), \
             patch.object(detector, '_check_portal_availability', return_value=False), \
             patch.object(detector, '_check_xdotool_availability', return_value=True):
            
            env_info = detector.detect_environment()
            
            assert env_info.display_server == DisplayServerType.X11
            assert env_info.desktop_environment == DesktopEnvironment.KDE
            assert InjectionMethod.XDOTOOL in env_info.available_methods
            assert env_info.portal_available is False
            assert env_info.xdotool_available is True
    
    def test_detect_environment_caching(self, detector):
        """Test that environment detection results are cached."""
        env_vars = {'WAYLAND_DISPLAY': 'wayland-0'}
        
        with patch.dict(os.environ, env_vars), \
             patch.object(detector, '_check_portal_availability', return_value=True) as mock_portal, \
             patch.object(detector, '_check_xdotool_availability', return_value=True) as mock_xdotool:
            
            # First call
            env_info1 = detector.detect_environment()
            
            # Second call should use cached result
            env_info2 = detector.detect_environment()
            
            assert env_info1 == env_info2
            
            # Portal and xdotool checks should only be called once
            assert mock_portal.call_count == 1
            assert mock_xdotool.call_count == 1
    
    def test_detect_environment_force_refresh(self, detector):
        """Test force refreshing cached environment detection."""
        env_vars = {'WAYLAND_DISPLAY': 'wayland-0'}
        
        with patch.dict(os.environ, env_vars), \
             patch.object(detector, '_check_portal_availability', return_value=True) as mock_portal:
            
            # First call
            env_info1 = detector.detect_environment()
            
            # Force refresh
            env_info2 = detector.detect_environment(force_refresh=True)
            
            # Content should be the same except for detection_time
            assert env_info1.display_server == env_info2.display_server
            assert env_info1.desktop_environment == env_info2.desktop_environment
            assert env_info1.available_methods == env_info2.available_methods
            assert env_info1.portal_available == env_info2.portal_available
            assert env_info1.xdotool_available == env_info2.xdotool_available
            
            # But detection times should be different
            assert env_info1.detection_time != env_info2.detection_time
            
            # Portal check should be called twice
            assert mock_portal.call_count == 2
    
    def test_get_preferred_method_wayland_portal_available(self, detector):
        """Test preferred method selection on Wayland with Portal."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL, InjectionMethod.XDOTOOL],
            portal_available=True,
            xdotool_available=True
        )
        
        preferred = detector.get_preferred_method(env_info)
        assert preferred == InjectionMethod.PORTAL
    
    def test_get_preferred_method_x11_xdotool_available(self, detector):
        """Test preferred method selection on X11 with xdotool."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.X11,
            desktop_environment=DesktopEnvironment.KDE,
            available_methods=[InjectionMethod.XDOTOOL],
            portal_available=False,
            xdotool_available=True
        )
        
        preferred = detector.get_preferred_method(env_info)
        assert preferred == InjectionMethod.XDOTOOL
    
    def test_get_preferred_method_no_methods(self, detector):
        """Test preferred method selection when no methods available."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.UNKNOWN,
            desktop_environment=DesktopEnvironment.UNKNOWN,
            available_methods=[],
            portal_available=False,
            xdotool_available=False
        )
        
        preferred = detector.get_preferred_method(env_info)
        assert preferred is None
    
    def test_get_preferred_method_override_preference(self, detector):
        """Test preferred method with user preference override."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL, InjectionMethod.XDOTOOL],
            portal_available=True,
            xdotool_available=True
        )
        
        # User prefers xdotool despite being on Wayland
        preferred = detector.get_preferred_method(env_info, user_preference=InjectionMethod.XDOTOOL)
        assert preferred == InjectionMethod.XDOTOOL
    
    def test_get_preferred_method_invalid_preference(self, detector):
        """Test preferred method with invalid user preference."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
        
        # User prefers xdotool but it's not available
        preferred = detector.get_preferred_method(env_info, user_preference=InjectionMethod.XDOTOOL)
        # Should fall back to default logic
        assert preferred == InjectionMethod.PORTAL
    
    def test_is_method_suitable_portal_on_wayland(self, detector):
        """Test method suitability - Portal on Wayland."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
        
        assert detector.is_method_suitable(InjectionMethod.PORTAL, env_info) is True
        assert detector.is_method_suitable(InjectionMethod.XDOTOOL, env_info) is False
    
    def test_is_method_suitable_xdotool_on_x11(self, detector):
        """Test method suitability - xdotool on X11."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.X11,
            desktop_environment=DesktopEnvironment.KDE,
            available_methods=[InjectionMethod.XDOTOOL],
            portal_available=False,
            xdotool_available=True
        )
        
        assert detector.is_method_suitable(InjectionMethod.XDOTOOL, env_info) is True
        assert detector.is_method_suitable(InjectionMethod.PORTAL, env_info) is False
    
    def test_environment_info_representation(self):
        """Test EnvironmentInfo string representation."""
        env_info = EnvironmentInfo(
            display_server=DisplayServerType.WAYLAND,
            desktop_environment=DesktopEnvironment.GNOME,
            available_methods=[InjectionMethod.PORTAL],
            portal_available=True,
            xdotool_available=False
        )
        
        str_repr = str(env_info)
        assert "WAYLAND" in str_repr
        assert "GNOME" in str_repr
        assert "PORTAL" in str_repr