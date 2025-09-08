"""
GTK4-based system tray manager for NexTalk.

Provides modern Linux desktop integration using GTK4 and GApplication.
"""

import logging
import threading
from enum import Enum
from typing import Optional, Callable, Any

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gio', '2.0')
    from gi.repository import Gtk, Gio, GLib
    GTK4_AVAILABLE = True
except (ImportError, ValueError) as e:
    GTK4_AVAILABLE = False
    logging.warning(f"GTK4 not available: {e}")
    # Create dummy objects
    Gtk = None
    Gio = None
    GLib = None


logger = logging.getLogger(__name__)


# Import TrayStatus from main tray module to ensure consistency
from .tray import TrayStatus


if GTK4_AVAILABLE:
    class GTK4TrayManager:
        """
        GTK4-based system tray manager.
        
        Provides modern Linux desktop integration using GTK4 Application framework.
        """
        
        def __init__(self, config: Any):
            """
            Initialize GTK4 tray manager.
            
            Args:
                config: UI configuration object
            """
            self.config = config
            self._status = TrayStatus.IDLE
            self._running = False
            
            # Callbacks
            self._on_quit: Optional[Callable] = None
            self._on_toggle: Optional[Callable] = None
            self._on_settings: Optional[Callable] = None
            self._on_about: Optional[Callable] = None
            
            # GTK4 Application
            self._app: Optional[Gtk.Application] = None
            self._main_loop: Optional[GLib.MainLoop] = None
            self._thread: Optional[threading.Thread] = None
            
            # Status tracking
            self._status_icons = {
                TrayStatus.IDLE: "audio-input-microphone-symbolic",
                TrayStatus.ACTIVE: "audio-input-microphone-high-symbolic", 
                TrayStatus.ERROR: "dialog-error-symbolic"
            }
            
        def start(self) -> None:
            """Start the GTK4 tray manager."""
            if self._running:
                logger.warning("GTK4 tray already running")
                return
                
            if not self.config.show_tray_icon:
                logger.info("System tray disabled in configuration")
                return
                
            logger.info("Starting GTK4 tray manager...")
            
            self._running = True
            self._thread = threading.Thread(target=self._run_gtk_loop, daemon=True)
            self._thread.start()
            
            # Give GTK time to initialize
            import time
            time.sleep(0.2)
            
            logger.info("GTK4 tray manager started successfully")
            
        def stop(self) -> None:
            """Stop the GTK4 tray manager."""
            if not self._running:
                return
                
            logger.info("Stopping GTK4 tray manager...")
            self._running = False
            
            if self._app:
                # Schedule quit on main thread
                GLib.idle_add(self._app.quit)
                
            if self._main_loop and self._main_loop.is_running():
                GLib.idle_add(self._main_loop.quit)
                
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
                
            logger.info("GTK4 tray manager stopped")
            
        def _run_gtk_loop(self) -> None:
            """Run the GTK4 main loop in a separate thread."""
            try:
                # Create GTK Application
                self._app = Gtk.Application(
                    application_id='com.nextalk.app',
                    flags=Gio.ApplicationFlags.FLAGS_NONE
                )
                
                # Connect application signals
                self._app.connect('activate', self._on_app_activate)
                self._app.connect('shutdown', self._on_app_shutdown)
                
                logger.debug("Starting GTK4 application...")
                
                # Run the application (this blocks)
                self._app.run([])
                
            except Exception as e:
                logger.error(f"GTK4 loop error: {e}")
            finally:
                self._running = False
                logger.debug("GTK4 loop ended")
                
        def _on_app_activate(self, app: Gtk.Application) -> None:
            """Handle GTK application activation."""
            logger.debug("GTK4 application activated")
            
            try:
                # Create application menu
                self._setup_app_menu()
                
                # Set up status indication
                self._setup_status_indication()
                
                logger.info("GTK4 tray interface ready")
                
            except Exception as e:
                logger.error(f"Failed to activate GTK4 app: {e}")
                
        def _on_app_shutdown(self, app: Gtk.Application) -> None:
            """Handle GTK application shutdown."""
            logger.debug("GTK4 application shutting down")
            
        def _setup_app_menu(self) -> None:
            """Set up the application menu."""
            try:
                # Create menu model
                menu = Gio.Menu()
                
                # Add menu items
                menu.append("开始/停止识别", "app.toggle_recognition")
                menu.append("设置", "app.open_settings")
                menu.append("关于", "app.about")
                menu.append("退出", "app.quit")
                
                # Create actions
                self._create_action("toggle_recognition", self._handle_toggle)
                self._create_action("open_settings", self._handle_settings)
                self._create_action("about", self._handle_about)
                self._create_action("quit", self._handle_quit)
                
                # Set application menu
                self._app.set_menubar(menu)
                
                logger.debug("GTK4 application menu created")
                
            except Exception as e:
                logger.error(f"Failed to create app menu: {e}")
                
        def _create_action(self, name: str, callback: Callable) -> None:
            """Create a GAction and connect it to a callback."""
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda action, param: callback())
            self._app.add_action(action)
            
        def _setup_status_indication(self) -> None:
            """Set up status indication using available mechanisms."""
            try:
                # Send startup notification
                self._send_notification("NexTalk", "应用已启动，使用快捷键开始语音识别")
                
            except Exception as e:
                logger.debug(f"Status indication setup: {e}")
                
        def _send_notification(self, title: str, message: str) -> None:
            """Send desktop notification."""
            try:
                notification = Gio.Notification.new(title)
                notification.set_body(message)
                
                # Set icon
                icon = Gio.ThemedIcon.new(self._status_icons[self._status])
                notification.set_icon(icon)
                
                # Send notification
                self._app.send_notification(None, notification)
                
            except Exception as e:
                logger.debug(f"Failed to send notification: {e}")
                
        def update_status(self, status: TrayStatus) -> None:
            """Update tray status."""
            if status == self._status:
                return
                
            old_status = self._status
            self._status = status
            
            logger.debug(f"Tray status changed: {old_status.value} -> {status.value}")
            
            # Send status notification
            status_messages = {
                TrayStatus.IDLE: "空闲状态",
                TrayStatus.ACTIVE: "正在识别语音...",
                TrayStatus.ERROR: "发生错误"
            }
            
            if self._app:
                GLib.idle_add(
                    self._send_notification,
                    "NexTalk",
                    status_messages[status]
                )
                
        def show_notification(self, title: str, message: str, timeout: float = 3.0) -> None:
            """Show a notification."""
            if self._app:
                GLib.idle_add(self._send_notification, title, message)
            else:
                logger.warning("Cannot show notification - GTK4 app not running")
                
        def _handle_toggle(self) -> None:
            """Handle toggle recognition action."""
            logger.info("Toggle recognition requested from GTK4 menu")
            if self._on_toggle:
                # Call in separate thread to avoid blocking GTK
                threading.Thread(target=self._on_toggle, daemon=True).start()
                
        def _handle_settings(self) -> None:
            """Handle open settings action."""
            logger.info("Open settings requested from GTK4 menu")
            if self._on_settings:
                threading.Thread(target=self._on_settings, daemon=True).start()
            else:
                self.show_notification("设置", "设置功能尚未实现")
                
        def _handle_about(self) -> None:
            """Handle about action."""
            logger.info("About requested from GTK4 menu")
            if self._on_about:
                threading.Thread(target=self._on_about, daemon=True).start()
            else:
                self.show_notification(
                    "关于 NexTalk",
                    "NexTalk v0.1.0\n个人轻量级实时语音识别与输入系统"
                )
                
        def _handle_quit(self) -> None:
            """Handle quit action."""
            logger.info("Quit requested from GTK4 menu")
            if self._on_quit:
                threading.Thread(target=self._on_quit, daemon=True).start()
            self.stop()
            
        # Callback setters (same interface as pystray version)
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
            return self._running and self._app is not None

else:
    # Dummy class when GTK4 is not available
    class GTK4TrayManager:
        """Dummy GTK4 tray manager when GTK4 is not available."""
        
        def __init__(self, config: Any):
            logger.error("GTK4 not available - cannot create tray manager")
            raise RuntimeError("GTK4 not available")
        
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


# Compatibility function for easy switching
def create_tray_manager(config: Any) -> GTK4TrayManager:
    """Create GTK4 tray manager instance."""
    return GTK4TrayManager(config)