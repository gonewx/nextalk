#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NexTalk main entry point.

Personal lightweight real-time voice recognition and input system.
"""

import sys
import os
import logging

# 设置默认编码为 UTF-8
import locale
import io

# 确保使用 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
if 'LC_ALL' not in os.environ:
    os.environ['LC_ALL'] = 'C.UTF-8'

if sys.platform == "win32":
    import codecs
    # Windows 下强制使用 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
else:
    # Unix/Linux 系统设置 locale
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            pass  # 忽略 locale 设置失败
import argparse
import asyncio
import signal
import time
from pathlib import Path
from typing import Optional

from .core.controller import MainController, ControllerState
from .config.manager import ConfigManager
from .utils.system import check_system_requirements, setup_environment


# Setup logging
def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup application logging.
    
    Args:
        level: Logging level
        log_file: Optional log file path
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        # Create log directory if needed
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    # Set third-party library log levels
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("pynput").setLevel(logging.WARNING)


class NexTalkApp:
    """Main NexTalk application."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize NexTalk application.
        
        Args:
            config_path: Path to configuration file
        """
        self.controller: Optional[MainController] = None
        self.config_path = config_path
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._shutdown_in_progress = False
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown and toggle recording."""
        def signal_handler(signum, frame):
            if self._shutdown_in_progress:
                # Second signal = force exit
                logging.warning("Received second signal, forcing exit...")
                os._exit(1)
                return
            logging.info(f"Received signal {signum}, shutting down...")
            self._shutdown()
            
            # Start force exit timer
            import threading
            def force_exit():
                time.sleep(5.0)  # Wait 5 seconds for graceful shutdown
                logging.warning("Graceful shutdown timeout, forcing exit...")
                os._exit(1)
            
            threading.Thread(target=force_exit, daemon=True).start()
        
        def toggle_recording_handler(signum, frame):
            """Handle SIGUSR1 signal to toggle recording state."""
            logging.info("Received SIGUSR1 signal, toggling recording...")
            if self.controller and hasattr(self.controller, 'toggle_recording'):
                try:
                    # 使用线程安全的方式调度到事件循环
                    if (hasattr(self.controller, '_event_loop') and 
                        self.controller._event_loop and 
                        not self.controller._event_loop.is_closed()):
                        # 使用controller的事件循环
                        future = asyncio.run_coroutine_threadsafe(
                            self.controller.toggle_recording(),
                            self.controller._event_loop
                        )
                        logging.info("Toggle recording task scheduled")
                    elif hasattr(self.controller, '_event_loop') and self.controller._event_loop.is_closed():
                        logging.warning("Event loop is closed, cannot toggle recording")
                        return
                    else:
                        # 回退到同步方式直接调用_toggle_recognition
                        logging.info("Using synchronous toggle method")
                        if hasattr(self.controller, '_toggle_recognition'):
                            self.controller._toggle_recognition()
                        else:
                            logging.error("No toggle method available")
                except Exception as e:
                    logging.error(f"Error toggling recording: {e}")
                    import traceback
                    logging.error(traceback.format_exc())
            else:
                logging.warning("Controller not available or toggle_recording method not found")
        
        # Register handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Unix/Linux specific - SIGUSR1 for toggle recording
        if sys.platform != "win32":
            signal.signal(signal.SIGUSR1, toggle_recording_handler)
        
        # Windows specific
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, signal_handler)
    
    async def initialize(self) -> bool:
        """
        Initialize the application.
        
        Returns:
            True if initialization successful
        """
        try:
            logging.info("Initializing NexTalk...")
            
            # Check system requirements
            if not check_system_requirements():
                logging.error("System requirements not met")
                return False
            
            # Setup environment
            setup_environment()
            
            # Create controller
            self.controller = MainController(self.config_path)

            # Set app exit callback so tray can properly exit the application
            self.controller.set_app_exit_callback(self._shutdown)

            # Initialize controller
            if not await self.controller.initialize():
                logging.error("Failed to initialize controller")
                return False
            
            logging.info("NexTalk initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Initialization failed: {e}")
            return False
    
    async def run(self) -> int:
        """
        Run the application.
        
        Returns:
            Exit code
        """
        try:
            # Initialize
            if not await self.initialize():
                return 1
            
            # Start controller
            self.controller.start()
            self._running = True
            
            logging.info("NexTalk is running. Press Ctrl+C to quit.")
            
            # Run until shutdown
            await self._shutdown_event.wait()
            
            return 0
            
        except Exception as e:
            logging.error(f"Application error: {e}")
            return 1
        
        finally:
            await self.cleanup()
    
    def _shutdown(self) -> None:
        """Trigger application shutdown."""
        logging.info("_shutdown() called")

        if self._shutdown_in_progress or not self._running:
            logging.info("Already shutting down or not running")
            return

        self._shutdown_in_progress = True
        self._running = False

        logging.info("Setting shutdown event")
        self._shutdown_event.set()

        # 强制退出保险机制
        import threading
        import os
        import time

        def emergency_exit():
            time.sleep(3.0)
            logging.warning("Emergency exit triggered - forcing process termination")
            os._exit(0)

        threading.Thread(target=emergency_exit, daemon=True).start()
        logging.info("Emergency exit timer started")
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        logging.info("Cleaning up...")
        
        try:
            # Reset signal handlers to prevent receiving signals after cleanup
            import sys
            if sys.platform != "win32":
                signal.signal(signal.SIGUSR1, signal.SIG_DFL)
                logging.debug("Signal handlers reset")
            
            if self.controller:
                self.controller.shutdown()
                
                # Wait for controller to fully shutdown
                max_wait = 3.0
                wait_interval = 0.1
                waited = 0.0
                
                while (self.controller.state_manager.get_state() != ControllerState.SHUTDOWN 
                       and waited < max_wait):
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                
                if self.controller.state_manager.get_state() != ControllerState.SHUTDOWN:
                    logging.warning("Controller did not shutdown cleanly within timeout, forcing exit")
            
            # Cancel any remaining tasks
            pending = [task for task in asyncio.all_tasks() if not task.done()]
            if pending:
                logging.debug(f"Cancelling {len(pending)} pending tasks")
                for task in pending:
                    task.cancel()
                
                # Wait briefly for tasks to cancel
                try:
                    await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=1.0)
                except asyncio.TimeoutError:
                    logging.warning("Some tasks did not cancel within timeout, forcing exit")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
        
        logging.info("Cleanup complete")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="NexTalk - Personal Voice Recognition System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  nextalk                     # Run with default config
  nextalk -c myconfig.yaml    # Run with custom config
  nextalk --check             # Check system requirements
  nextalk --version           # Show version
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "-l", "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO"
    )
    
    parser.add_argument(
        "--log-file",
        help="Path to log file",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "--check",
        help="Check system requirements and exit",
        action="store_true"
    )
    
    parser.add_argument(
        "--version",
        help="Show version and exit",
        action="store_true"
    )
    
    parser.add_argument(
        "--no-tray",
        help="Run without system tray icon",
        action="store_true"
    )
    
    parser.add_argument(
        "--server",
        help="WebSocket server URL",
        type=str,
        default=None
    )
    
    parser.add_argument(
        "--port",
        help="WebSocket server port",
        type=int,
        default=None
    )
    
    return parser.parse_args()


def show_version() -> None:
    """Show version information."""
    from . import __version__
    
    print(f"NexTalk v{__version__}")
    print("Personal Lightweight Real-time Voice Recognition System")
    print("Copyright (c) 2024 NexTalk Contributors")


def check_requirements() -> int:
    """
    Check system requirements.
    
    Returns:
        Exit code
    """
    print("Checking system requirements...")
    
    requirements = {
        "Python": sys.version,
        "Platform": sys.platform,
        "Audio": "Available" if check_audio_devices() else "Not available",
        "Network": "Available" if check_network() else "Not available"
    }
    
    print("\nSystem Information:")
    for key, value in requirements.items():
        print(f"  {key}: {value}")
    
    if check_system_requirements():
        print("\n✓ All requirements met")
        return 0
    else:
        print("\n✗ Some requirements not met")
        return 1


def check_audio_devices() -> bool:
    """Check if audio devices are available."""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        p.terminate()
        return device_count > 0
    except:
        return False


def check_network() -> bool:
    """Check network connectivity."""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False


def apply_runtime_config(args: argparse.Namespace) -> None:
    """
    Apply runtime configuration from command line arguments.
    
    Args:
        args: Command line arguments
    """
    if args.no_tray:
        # Override tray setting
        os.environ["NEXTALK_NO_TRAY"] = "1"
    
    if args.server:
        os.environ["NEXTALK_SERVER"] = args.server
    
    if args.port:
        os.environ["NEXTALK_PORT"] = str(args.port)


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code
    """
    # Parse arguments
    args = parse_arguments()
    
    # Handle special commands
    if args.version:
        show_version()
        return 0
    
    if args.check:
        return check_requirements()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Apply runtime configuration
    apply_runtime_config(args)
    
    # Create and run application
    app = NexTalkApp(args.config)
    
    # Run async main
    try:
        if sys.platform == "win32":
            # Windows specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        return asyncio.run(app.run())
        
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 0
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())