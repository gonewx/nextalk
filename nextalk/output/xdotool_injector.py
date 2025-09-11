"""
xdotool-based text injection implementation.

Provides text injection through xdotool command-line utility,
designed as a fallback for traditional X11 environments.
"""

import asyncio
import shutil
import subprocess
import time
import logging
from typing import Optional, Dict, Any, List

from .base_injector import BaseInjector, InjectorCapabilities
from .injection_models import InjectorState, InjectionResult, InjectionMethod, InjectorConfiguration
from .injection_exceptions import (
    XDoToolError,
    XDoToolNotFoundError,
    XDoToolExecutionError,
    InjectionFailedError,
    InitializationError,
)


logger = logging.getLogger(__name__)


class XDoToolInjector(BaseInjector):
    """
    Text injector implementation using xdotool.

    This implementation provides text injection for traditional X11
    environments through the xdotool command-line utility, serving
    as a fallback when Portal is not available.
    """

    def __init__(self, config: Optional[InjectorConfiguration] = None):
        """
        Initialize xdotool injector.

        Args:
            config: Injector configuration
        """
        super().__init__(config)
        self._xdotool_path: Optional[str] = None
        self._xdotool_version: Optional[str] = None

        # xdotool-specific configuration
        self._xdotool_delay = getattr(config, "xdotool_delay", 0.02) if config else 0.02

        self._logger.debug("xdotool injector created")

    @property
    def capabilities(self) -> InjectorCapabilities:
        """Get xdotool injector capabilities."""
        return InjectorCapabilities(
            method=InjectionMethod.XDOTOOL,
            supports_keyboard=True,
            supports_mouse=True,  # xdotool supports mouse operations too
            requires_permissions=False,
            requires_external_tools=True,
            platform_specific=True,
            description="xdotool X11 text injection",
        )

    @property
    def method(self) -> InjectionMethod:
        """Get injection method."""
        return InjectionMethod.XDOTOOL

    @property
    def xdotool_available(self) -> bool:
        """Check if xdotool is available."""
        return self._xdotool_path is not None

    async def initialize(self) -> bool:
        """
        Initialize xdotool injector.

        Returns:
            True if initialization successful

        Raises:
            InitializationError: If initialization fails
        """
        if self.is_initialized:
            return True

        await self._set_state(InjectorState.INITIALIZING)

        try:
            self._logger.info("Initializing xdotool injector")

            # Check xdotool availability
            await self._check_xdotool()

            # Verify X11 environment
            await self._check_x11_environment()

            await self._set_state(InjectorState.READY)
            self._logger.info(f"xdotool injector initialized (version: {self._xdotool_version})")
            return True

        except Exception as e:
            await self._set_state(InjectorState.ERROR)
            self._logger.error(f"xdotool injector initialization failed: {e}")
            raise InitializationError(
                "xdotool injector initialization failed", "XDoToolInjector", e
            ) from e

    async def cleanup(self) -> None:
        """Clean up xdotool injector resources."""
        try:
            self._logger.info("Cleaning up xdotool injector")

            # xdotool doesn't require explicit cleanup
            await self._set_state(InjectorState.UNINITIALIZED)
            self._logger.info("xdotool injector cleanup complete")

        except Exception as e:
            self._logger.warning(f"Error during xdotool cleanup: {e}")

    async def inject_text(self, text: str) -> InjectionResult:
        """
        Inject text using xdotool.

        Args:
            text: Text to inject

        Returns:
            InjectionResult with operation details

        Raises:
            InjectionFailedError: If injection fails
        """
        start_time = time.time()

        try:
            # Validate text
            validated_text = await self._validate_text(text)

            # Check if ready
            if not self.is_ready:
                raise InjectionFailedError(
                    f"xdotool injector not ready. State: {self.state.value}",
                    text=validated_text,
                    method=self.method.value,
                )

            # Perform text injection
            await self._inject_text_xdotool(validated_text)

            # Build successful result
            result = InjectionResult(
                success=True,
                method_used=self.method,
                text_length=len(validated_text),
                injection_time=start_time,
                performance_metrics={
                    "duration": time.time() - start_time,
                    "characters_per_second": len(validated_text) / (time.time() - start_time),
                },
            )

            self._logger.debug(f"xdotool injection successful: {len(validated_text)} characters")
            return result

        except Exception as e:
            self._logger.error(f"xdotool text injection failed: {e}")
            raise InjectionFailedError(
                f"xdotool text injection failed: {e}", text=text, method=self.method.value
            ) from e

    async def test_injection(self) -> bool:
        """
        Test xdotool text injection.

        Returns:
            True if test successful
        """
        try:
            test_text = "xdotool test"
            result = await self.inject_text(test_text)
            return result.success
        except Exception as e:
            self._logger.debug(f"xdotool test injection failed: {e}")
            return False

    async def check_availability(self) -> bool:
        """
        Check if xdotool injector is available.

        Returns:
            True if xdotool is available
        """
        try:
            # Check xdotool binary
            xdotool_path = shutil.which("xdotool")
            if not xdotool_path:
                return False

            # Test basic functionality
            result = await self._run_xdotool_command(["--version"])
            return result.returncode == 0

        except Exception as e:
            self._logger.debug(f"xdotool availability check failed: {e}")
            return False

    async def get_health_status(self) -> Dict[str, Any]:
        """Get xdotool injector health status."""
        status = {
            "xdotool_available": self.xdotool_available,
            "xdotool_path": self._xdotool_path,
            "xdotool_version": self._xdotool_version,
            "x11_display": None,
        }

        # Check X11 display
        import os

        x11_display = os.environ.get("DISPLAY")
        status["x11_display"] = x11_display
        status["x11_available"] = x11_display is not None

        return status

    # Private implementation methods

    async def _check_xdotool(self) -> None:
        """Check xdotool availability and get version."""
        try:
            # Find xdotool binary
            self._xdotool_path = shutil.which("xdotool")
            if not self._xdotool_path:
                raise XDoToolNotFoundError()

            # Get version information
            result = await self._run_xdotool_command(["--version"])

            if result.returncode != 0:
                raise XDoToolExecutionError("xdotool --version", result.returncode, result.stderr)

            # Parse version from output
            version_output = result.stdout.strip()
            self._xdotool_version = version_output.split()[-1] if version_output else "unknown"

            self._logger.debug(
                f"xdotool found: {self._xdotool_path} (version: {self._xdotool_version})"
            )

        except subprocess.TimeoutExpired:
            raise XDoToolError("xdotool version check timed out")
        except FileNotFoundError:
            raise XDoToolNotFoundError()

    async def _check_x11_environment(self) -> None:
        """Check X11 environment availability."""
        import os

        display = os.environ.get("DISPLAY")
        if not display:
            raise XDoToolError(
                "No X11 DISPLAY environment variable found. xdotool requires X11.",
                context={"environment": "X11", "display": None},
            )

        self._logger.debug(f"X11 display available: {display}")

    async def _inject_text_xdotool(self, text: str) -> None:
        """Inject text using xdotool commands."""
        try:
            # Escape text for xdotool
            escaped_text = self._escape_text(text)

            # Use xdotool type command for text injection
            command = ["type", "--delay", str(int(self._xdotool_delay * 1000)), escaped_text]

            result = await self._run_xdotool_command(command)

            if result.returncode != 0:
                raise XDoToolExecutionError(
                    " ".join(["xdotool"] + command), result.returncode, result.stderr
                )

            self._logger.debug(f"xdotool injected {len(text)} characters")

        except Exception as e:
            raise InjectionFailedError(f"xdotool text injection failed: {e}") from e

    def _escape_text(self, text: str) -> str:
        """
        Escape text for xdotool.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for xdotool
        """
        # xdotool type handles most characters well, but we need to escape some special ones
        # For safety, we'll use a more conservative approach with character-by-character typing

        # Replace problematic characters
        escaped = text

        # Handle backslashes (must be doubled)
        escaped = escaped.replace("\\", "\\\\")

        # Handle single quotes (escape with backslash)
        escaped = escaped.replace("'", "\\'")

        # Handle newlines (convert to actual newlines that xdotool understands)
        escaped = escaped.replace("\n", "\\n")
        escaped = escaped.replace("\r", "\\r")
        escaped = escaped.replace("\t", "\\t")

        return escaped

    async def _run_xdotool_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """
        Run xdotool command with proper error handling.

        Args:
            args: Command arguments (without 'xdotool' prefix)

        Returns:
            CompletedProcess result
        """
        if not self._xdotool_path:
            raise XDoToolNotFoundError()

        command = [self._xdotool_path] + args

        try:
            self._logger.debug(f"Running xdotool command: {' '.join(command)}")

            # Run command asynchronously
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=None
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=10.0  # 10 second timeout for xdotool commands
            )

            result = subprocess.CompletedProcess(
                command,
                process.returncode,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )

            self._logger.debug(f"xdotool command result: {result.returncode}")

            return result

        except asyncio.TimeoutError:
            # Kill the process if it's still running
            if process.returncode is None:
                process.kill()
                await process.wait()

            raise XDoToolError(
                f"xdotool command timed out: {' '.join(command)}", command=" ".join(command)
            )

        except Exception as e:
            raise XDoToolError(
                f"xdotool command execution failed: {e}", command=" ".join(command)
            ) from e

    # Additional xdotool-specific methods

    async def focus_window(self, window_name: Optional[str] = None) -> bool:
        """
        Focus a window before text injection.

        Args:
            window_name: Name of window to focus, or None for current window

        Returns:
            True if successful
        """
        try:
            if window_name:
                # Search for window by name and focus it
                result = await self._run_xdotool_command(
                    ["search", "--name", window_name, "windowfocus"]
                )
            else:
                # Focus the currently active window (no-op, but ensures xdotool works)
                result = await self._run_xdotool_command(["getactivewindow", "windowfocus"])

            return result.returncode == 0

        except Exception as e:
            self._logger.debug(f"Window focus failed: {e}")
            return False

    async def get_active_window_info(self) -> Dict[str, str]:
        """
        Get information about the currently active window.

        Returns:
            Dictionary with window information
        """
        try:
            # Get active window ID
            result = await self._run_xdotool_command(["getactivewindow"])

            if result.returncode != 0:
                return {}

            window_id = result.stdout.strip()

            # Get window name
            name_result = await self._run_xdotool_command(["getwindowname", window_id])

            window_name = name_result.stdout.strip() if name_result.returncode == 0 else "Unknown"

            return {"window_id": window_id, "window_name": window_name}

        except Exception as e:
            self._logger.debug(f"Failed to get active window info: {e}")
            return {}

    async def simulate_key_combination(self, keys: str) -> bool:
        """
        Simulate key combination (e.g., "ctrl+c", "alt+Tab").

        Args:
            keys: Key combination string

        Returns:
            True if successful
        """
        try:
            result = await self._run_xdotool_command(["key", keys])
            return result.returncode == 0

        except Exception as e:
            self._logger.debug(f"Key combination simulation failed: {e}")
            return False
