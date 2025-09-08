"""
GTK3 + AppIndicator system tray manager for NexTalk.

Provides the most compatible Linux desktop integration using GTK3 and AppIndicator.
"""

import logging
import threading
from enum import Enum
from typing import Optional, Callable, Any
import time
from .icon_manager import get_icon_manager

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GLib
    
    # Try AppIndicator3 first, then Ayatana
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
        INDICATOR_AVAILABLE = True
        INDICATOR_TYPE = "AppIndicator3"
    except (ImportError, ValueError):
        try:
            gi.require_version('AyatanaAppIndicator3', '0.1')
            from gi.repository import AyatanaAppIndicator3 as AppIndicator
            INDICATOR_AVAILABLE = True
            INDICATOR_TYPE = "AyatanaAppIndicator3"
        except (ImportError, ValueError):
            INDICATOR_AVAILABLE = False
            AppIndicator = None
            INDICATOR_TYPE = None
    
    GTK3_AVAILABLE = True
except (ImportError, ValueError) as e:
    GTK3_AVAILABLE = False
    INDICATOR_AVAILABLE = False
    logging.warning(f"GTK3/AppIndicator not available: {e}")
    Gtk = None
    AppIndicator = None
    GLib = None


logger = logging.getLogger(__name__)


# Import TrayStatus from main tray module to ensure consistency
from .tray import TrayStatus


if GTK3_AVAILABLE and INDICATOR_AVAILABLE:
    class GTK3AppIndicatorTrayManager:
        """
        GTK3 + AppIndicator based system tray manager.
        
        Provides excellent Linux desktop integration with broad compatibility.
        """
        
        def __init__(self, config: Any):
            """
            Initialize GTK3 AppIndicator tray manager.
            
            Args:
                config: UI configuration object
            """
            self.config = config
            self._status = TrayStatus.IDLE
            self._running = False
            self._gtk_initialized = False
            
            # 初始化图标管理器
            self._icon_manager = get_icon_manager()
            self._custom_icons_available = self._icon_manager.is_available()
            logger.info(f"Icon manager initialized: {self._custom_icons_available}")
            logger.info(f"Icons directory: {self._icon_manager.icons_dir}")
            
            # Callbacks
            self._on_quit: Optional[Callable] = None
            self._on_toggle: Optional[Callable] = None
            self._on_settings: Optional[Callable] = None
            self._on_about: Optional[Callable] = None
            
            # AppIndicator components
            self._indicator: Optional[AppIndicator.Indicator] = None
            self._menu: Optional[Gtk.Menu] = None
            self._main_loop: Optional[GLib.MainLoop] = None
            self._thread: Optional[threading.Thread] = None
            
            # 系统图标备用方案
            self._fallback_icons = {
                TrayStatus.IDLE: "audio-input-microphone",
                TrayStatus.ACTIVE: "audio-input-microphone-high",
                TrayStatus.ERROR: "dialog-error"
            }
            
            logger.info(f"Initializing GTK3 AppIndicator tray ({INDICATOR_TYPE})")
            
        
        def _get_icon_path(self, status: TrayStatus) -> str:
            """Get the file path for the icon of the given status."""
            logger.info(f"Getting icon for status: {status}, custom_icons_available: {self._custom_icons_available}")
            
            if not self._custom_icons_available:
                logger.info(f"Using fallback system icon: {self._fallback_icons[status]}")
                return self._fallback_icons[status]
                
            try:
                status_map = {
                    TrayStatus.IDLE: "idle",
                    TrayStatus.ACTIVE: "active",
                    TrayStatus.ERROR: "error"
                }
                
                status_str = status_map.get(status, "idle")
                icon_path = self._icon_manager.get_icon_path(status_str)
                
                if icon_path:
                    logger.info(f"Using custom icon: {icon_path}")
                    return icon_path
                else:
                    logger.info(f"Custom icon not found, fallback to system icon: {self._fallback_icons[status]}")
                    return self._fallback_icons[status]
                    
            except Exception as e:
                logger.error(f"Error getting icon path: {e}")
                logger.info(f"Exception fallback to system icon: {self._fallback_icons[status]}")
                return self._fallback_icons[status]
            
        def start(self) -> None:
            """Start the AppIndicator tray manager."""
            if self._running:
                logger.warning("GTK3 AppIndicator tray already running")
                return
                
            if not self.config.show_tray_icon:
                logger.info("System tray disabled in configuration")
                return
                
            logger.info("Starting GTK3 AppIndicator tray manager...")
            
            self._running = True
            self._thread = threading.Thread(target=self._run_gtk_main, daemon=True)
            self._thread.start()
            
            # Give GTK time to initialize
            time.sleep(0.3)
            
            if self._indicator:
                logger.info("GTK3 AppIndicator tray started successfully")
            else:
                logger.warning("GTK3 AppIndicator tray may not have started properly")
                
        def stop(self) -> None:
            """Stop the AppIndicator tray manager."""
            if not self._running:
                return
                
            logger.info("Stopping GTK3 AppIndicator tray manager...")
            self._running = False
            
            if self._indicator:
                # Hide the indicator
                GLib.idle_add(self._indicator.set_status, AppIndicator.IndicatorStatus.PASSIVE)
            
            if self._main_loop and self._main_loop.is_running():
                GLib.idle_add(self._main_loop.quit)
                
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
                
            logger.info("GTK3 AppIndicator tray stopped")
            
        def _run_gtk_main(self) -> None:
            """Run the GTK main loop in a separate thread."""
            try:
                # Initialize GTK if not already done
                if not self._gtk_initialized:
                    Gtk.init([])
                    self._gtk_initialized = True
                
                # 检查自定义图标可用性（无需安装）
                if self._custom_icons_available:
                    logger.info("Custom NexTalk icons available")
                else:
                    logger.info("Using fallback system icons")
                
                # Create the indicator
                self._create_indicator()
                
                # Create the menu
                self._create_menu()
                
                # Set the menu
                if self._indicator and self._menu:
                    self._indicator.set_menu(self._menu)
                    self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
                    logger.debug("AppIndicator activated")
                
                # Create and run main loop
                self._main_loop = GLib.MainLoop()
                
                logger.debug("Starting GTK main loop...")
                self._main_loop.run()
                
            except Exception as e:
                logger.error(f"GTK main loop error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                self._running = False
                logger.debug("GTK main loop ended")
                
        def _create_indicator(self) -> None:
            """Create the AppIndicator."""
            try:
                # 简单获取图标路径并创建indicator
                icon_path = self._get_icon_path(self._status)
                
                self._indicator = AppIndicator.Indicator.new(
                    "nextalk",
                    icon_path,
                    AppIndicator.IndicatorCategory.APPLICATION_STATUS
                )
                
                logger.info(f"Created indicator with icon: {icon_path}")
                
                # Set properties
                self._indicator.set_title("NexTalk")
                
                logger.info("AppIndicator created successfully")
                
            except Exception as e:
                logger.error(f"Failed to create AppIndicator: {e}")
                logger.error(f"Status: {self._status}, Icon: {icon_path}")
                import traceback
                logger.error(traceback.format_exc())
                self._indicator = None
                
        def _create_menu(self) -> None:
            """Create the context menu."""
            try:
                self._menu = Gtk.Menu()
                
                # Toggle recognition item
                toggle_item = Gtk.MenuItem(label="开始/停止识别")
                toggle_item.connect("activate", lambda x: self._handle_toggle())
                self._menu.append(toggle_item)
                
                # Separator
                separator = Gtk.SeparatorMenuItem()
                self._menu.append(separator)
                
                # Settings item
                settings_item = Gtk.MenuItem(label="设置")
                settings_item.connect("activate", lambda x: self._handle_settings())
                self._menu.append(settings_item)
                
                # About item
                about_item = Gtk.MenuItem(label="关于")
                about_item.connect("activate", lambda x: self._handle_about())
                self._menu.append(about_item)
                
                # Separator
                separator2 = Gtk.SeparatorMenuItem()
                self._menu.append(separator2)
                
                # Quit item
                quit_item = Gtk.MenuItem(label="退出")
                quit_item.connect("activate", lambda x: self._handle_quit())
                self._menu.append(quit_item)
                
                # Show all menu items
                self._menu.show_all()
                
                logger.debug("AppIndicator menu created")
                
            except Exception as e:
                logger.error(f"Failed to create menu: {e}")
                self._menu = None
                
        def update_status(self, status: TrayStatus) -> None:
            """Update tray status."""
            if status == self._status:
                return
                
            old_status = self._status
            self._status = status
            
            logger.debug(f"Tray status changed: {old_status.value} -> {status.value}")
            
            # Update indicator icon
            if self._indicator:
                def update_icon():
                    try:
                        # 简单获取图标路径并更新
                        icon_path = self._get_icon_path(status)
                        logger.info(f"Updating icon to: {icon_path}")
                        self._indicator.set_icon(icon_path)
                        
                    except Exception as e:
                        logger.error(f"Failed to update indicator icon: {e}")
                
                GLib.idle_add(update_icon)
                
        def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
            """Show a notification."""
            try:
                # Use GTK3 notifications if available
                notification = Gtk.InfoBar()
                # For now, just log the notification
                logger.info(f"Notification: {title} - {message}")
                
                # TODO: Could implement actual desktop notifications here
                # using notify2 or similar
                
            except Exception as e:
                logger.debug(f"Failed to show notification: {e}")
                
        def _handle_toggle(self) -> None:
            """Handle toggle recognition action."""
            logger.info("Toggle recognition requested from AppIndicator menu")
            if self._on_toggle:
                # Call in separate thread to avoid blocking GTK
                threading.Thread(target=self._on_toggle, daemon=True).start()
                
        def _handle_settings(self) -> None:
            """Handle open settings action."""
            logger.info("Open settings requested from AppIndicator menu")
            if self._on_settings:
                threading.Thread(target=self._on_settings, daemon=True).start()
            else:
                self.show_notification("设置", "设置功能尚未实现")
                
        def _handle_about(self) -> None:
            """Handle about action."""
            logger.info("About requested from AppIndicator menu")
            if self._on_about:
                threading.Thread(target=self._on_about, daemon=True).start()
            else:
                self.show_notification(
                    "关于 NexTalk",
                    "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
                )
                
        def _handle_quit(self) -> None:
            """Handle quit action."""
            logger.info("Quit requested from AppIndicator menu")
            if self._on_quit:
                threading.Thread(target=self._on_quit, daemon=True).start()
            self.stop()
            
        # Callback setters (same interface as other implementations)
        def set_on_quit(self, callback: Callable) -> None:
            """Set quit callback."""
            self._on_quit = callback
            
        def set_on_toggle(self, callback: Callable) -> None:
            """Set toggle recognition callback."""
            self._on_toggle = callback
            
        def set_on_settings(self, callback: Callable) -> None:
            """Set open settings callback."""
            self._on_settings = callback
            
        def set_on_about(self, callback: Callable) -> None:
            """Set about callback."""
            self._on_about = callback
            
        def is_running(self) -> bool:
            """Check if tray is running."""
            return self._running and self._indicator is not None

else:
    # Dummy class when GTK3/AppIndicator is not available
    class GTK3AppIndicatorTrayManager:
        """Dummy AppIndicator tray manager when GTK3/AppIndicator is not available."""
        
        def __init__(self, config: Any):
            logger.error("GTK3/AppIndicator not available - cannot create tray manager")
            raise RuntimeError("GTK3/AppIndicator not available")
        
        def start(self) -> None:
            pass
        
        def stop(self) -> None:
            pass
        
        def update_status(self, status: TrayStatus) -> None:
            pass
        
        def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
            pass
        
        def set_on_quit(self, callback: Callable) -> None:
            pass
        
        def set_on_toggle(self, callback: Callable) -> None:
            pass
        
        def set_on_settings(self, callback: Callable) -> None:
            pass
        
        def set_on_about(self, callback: Callable) -> None:
            pass
        
        def is_running(self) -> bool:
            return False