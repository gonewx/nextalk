"""
Exception hierarchy for text injection system.

Provides structured error handling for the modernized text injection architecture,
categorizing errors by type and providing clear diagnostic information.
"""

from typing import Optional, Dict, Any


class InjectionError(Exception):
    """Base exception for all text injection related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize injection error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            context: Additional context information for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context or {}

    def __str__(self) -> str:
        """Return string representation with error code."""
        return f"[{self.error_code}] {self.message}"

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get detailed diagnostic information for logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
        }


class InitializationError(InjectionError):
    """Raised when injection system initialization fails."""

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        underlying_error: Optional[Exception] = None,
    ):
        """
        Initialize initialization error.

        Args:
            message: Error description
            component: Component that failed to initialize
            underlying_error: The original exception that caused the failure
        """
        context = {}
        if component:
            context["component"] = component
        if underlying_error:
            context["underlying_error"] = str(underlying_error)

        super().__init__(message, "INIT_ERROR", context)
        self.component = component
        self.underlying_error = underlying_error


class EnvironmentError(InjectionError):
    """Raised when environment detection or validation fails."""

    def __init__(self, message: str, environment_info: Optional[Dict[str, Any]] = None):
        """
        Initialize environment error.

        Args:
            message: Error description
            environment_info: Environment detection results
        """
        context = {"environment_info": environment_info} if environment_info else {}
        super().__init__(message, "ENV_ERROR", context)
        self.environment_info = environment_info


class PortalError(InjectionError):
    """Base exception for Portal-related errors."""

    def __init__(
        self,
        message: str,
        portal_operation: Optional[str] = None,
        session_handle: Optional[str] = None,
    ):
        """
        Initialize Portal error.

        Args:
            message: Error description
            portal_operation: The Portal operation that failed
            session_handle: Portal session handle if available
        """
        context = {}
        if portal_operation:
            context["operation"] = portal_operation
        if session_handle:
            context["session_handle"] = session_handle

        super().__init__(message, "PORTAL_ERROR", context)
        self.portal_operation = portal_operation
        self.session_handle = session_handle


class PortalConnectionError(PortalError):
    """Raised when Portal service connection fails."""

    def __init__(self, message: str = "Failed to connect to xdg-desktop-portal service"):
        super().__init__(message, "connection", None)
        self.error_code = "PORTAL_CONNECTION_ERROR"


class PortalPermissionError(PortalError):
    """Raised when Portal permission is denied by user."""

    def __init__(
        self,
        message: str = "User denied Portal permissions",
        requested_permissions: Optional[list] = None,
    ):
        context = {"requested_permissions": requested_permissions} if requested_permissions else {}
        super().__init__(message, "permission", None)
        self.error_code = "PORTAL_PERMISSION_ERROR"
        self.context.update(context)
        self.requested_permissions = requested_permissions


class PortalSessionError(PortalError):
    """Raised when Portal session management fails."""

    def __init__(
        self,
        message: str,
        session_state: Optional[str] = None,
        session_handle: Optional[str] = None,
    ):
        super().__init__(message, "session", session_handle)
        self.error_code = "PORTAL_SESSION_ERROR"
        if session_state:
            self.context["session_state"] = session_state
        self.session_state = session_state


class PortalTimeoutError(PortalError):
    """Raised when Portal operations timeout."""

    def __init__(self, message: str, operation: str, timeout: float):
        super().__init__(message, operation, None)
        self.error_code = "PORTAL_TIMEOUT_ERROR"
        self.context.update({"timeout_seconds": timeout, "operation": operation})
        self.timeout = timeout


class XDoToolError(InjectionError):
    """Base exception for xdotool-related errors."""

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
    ):
        """
        Initialize xdotool error.

        Args:
            message: Error description
            command: The xdotool command that failed
            exit_code: Command exit code
            stderr: Standard error output
        """
        context = {}
        if command:
            context["command"] = command
        if exit_code is not None:
            context["exit_code"] = exit_code
        if stderr:
            context["stderr"] = stderr

        super().__init__(message, "XDOTOOL_ERROR", context)
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr


class XDoToolNotFoundError(XDoToolError):
    """Raised when xdotool binary is not found on the system."""

    def __init__(self, message: str = "xdotool command not found on system"):
        super().__init__(message, None, None, None)
        self.error_code = "XDOTOOL_NOT_FOUND_ERROR"


class XDoToolExecutionError(XDoToolError):
    """Raised when xdotool command execution fails."""

    def __init__(self, command: str, exit_code: int, stderr: str = ""):
        message = f"xdotool command failed: {command}"
        super().__init__(message, command, exit_code, stderr)
        self.error_code = "XDOTOOL_EXECUTION_ERROR"


# Alias for compatibility
CommandExecutionError = XDoToolExecutionError


class InjectionFailedError(InjectionError):
    """Raised when text injection operation fails."""

    def __init__(
        self,
        message: str,
        text: Optional[str] = None,
        method: Optional[str] = None,
        retry_count: int = 0,
    ):
        """
        Initialize injection failure error.

        Args:
            message: Error description
            text: Text that failed to inject (truncated for security)
            method: Injection method that was used
            retry_count: Number of retry attempts made
        """
        context = {
            "text_length": len(text) if text else 0,
            "text_preview": text[:50] + "..." if text and len(text) > 50 else text,
            "method": method,
            "retry_count": retry_count,
        }

        super().__init__(message, "INJECTION_FAILED", context)
        self.text = text
        self.method = method
        self.retry_count = retry_count


class ConfigurationError(InjectionError):
    """Raised when injection configuration is invalid."""

    def __init__(
        self, message: str, config_field: Optional[str] = None, invalid_value: Optional[Any] = None
    ):
        """
        Initialize configuration error.

        Args:
            message: Error description
            config_field: Name of the invalid configuration field
            invalid_value: The invalid configuration value
        """
        context = {}
        if config_field:
            context["config_field"] = config_field
        if invalid_value is not None:
            context["invalid_value"] = str(invalid_value)

        super().__init__(message, "CONFIG_ERROR", context)
        self.config_field = config_field
        self.invalid_value = invalid_value


class DependencyError(InjectionError):
    """Raised when required dependencies are missing."""

    def __init__(
        self, message: str, missing_dependency: str, installation_hint: Optional[str] = None
    ):
        """
        Initialize dependency error.

        Args:
            message: Error description
            missing_dependency: Name of missing dependency
            installation_hint: Suggestion for installing the dependency
        """
        context = {"missing_dependency": missing_dependency, "installation_hint": installation_hint}

        super().__init__(message, "DEPENDENCY_ERROR", context)
        self.missing_dependency = missing_dependency
        self.installation_hint = installation_hint


class SecurityError(InjectionError):
    """Raised when security constraints are violated."""

    def __init__(self, message: str, security_context: Optional[Dict[str, Any]] = None):
        """
        Initialize security error.

        Args:
            message: Error description
            security_context: Additional security-related information
        """
        super().__init__(message, "SECURITY_ERROR", security_context or {})
        self.security_context = security_context


class FactoryError(InjectionError):
    """Raised when injection factory operations fail."""

    def __init__(self, message: str, factory_operation: Optional[str] = None):
        """
        Initialize factory error.

        Args:
            message: Error description
            factory_operation: The factory operation that failed
        """
        context = {}
        if factory_operation:
            context["factory_operation"] = factory_operation

        super().__init__(message, "FACTORY_ERROR", context)
        self.factory_operation = factory_operation


# Convenience functions for common error patterns


def raise_portal_connection_error(underlying_error: Optional[Exception] = None):
    """Raise a Portal connection error with optional chaining."""
    message = "Cannot connect to xdg-desktop-portal service"
    if underlying_error:
        message += f": {underlying_error}"
    raise PortalConnectionError(message) from underlying_error


def raise_xdotool_not_found():
    """Raise xdotool not found error with installation hint."""
    error = XDoToolNotFoundError()
    error.installation_hint = "Install xdotool: sudo apt-get install xdotool"
    raise error


def raise_permission_denied(service: str = "Portal"):
    """Raise permission denied error for specified service."""
    message = f"User denied permissions for {service} service"
    if service.lower() == "portal":
        raise PortalPermissionError(message)
    else:
        raise SecurityError(message, {"service": service})


def chain_injection_error(
    original_error: Exception, text: Optional[str] = None, method: Optional[str] = None
) -> InjectionFailedError:
    """Create an injection error chained from another exception."""
    message = f"Text injection failed: {original_error}"
    error = InjectionFailedError(message, text, method)
    return error
