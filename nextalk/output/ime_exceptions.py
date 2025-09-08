"""
IME异常处理类 - 提供详细的错误处理和诊断信息。

定义IME相关的异常类型，实现错误码和错误消息管理。
"""

import logging
import sys
import traceback
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


logger = logging.getLogger(__name__)


class IMEErrorCode(Enum):
    """IME错误码枚举."""
    
    # 初始化错误 (1000-1099)
    INIT_GENERAL_ERROR = "IME_1000"
    INIT_PLATFORM_NOT_SUPPORTED = "IME_1001"
    INIT_LIBRARY_NOT_FOUND = "IME_1002"
    INIT_PERMISSIONS_DENIED = "IME_1003"
    INIT_CONTEXT_CREATION_FAILED = "IME_1004"
    INIT_ADAPTER_CREATION_FAILED = "IME_1005"
    
    # 权限错误 (1100-1199)
    PERMISSION_ACCESSIBILITY_DENIED = "IME_1100"
    PERMISSION_INPUT_MONITORING_DENIED = "IME_1101"
    PERMISSION_ADMIN_REQUIRED = "IME_1102"
    PERMISSION_IME_ACCESS_DENIED = "IME_1103"
    
    # 兼容性错误 (1200-1299)
    COMPATIBILITY_APP_NOT_SUPPORTED = "IME_1200"
    COMPATIBILITY_IME_NOT_SUPPORTED = "IME_1201"
    COMPATIBILITY_OS_VERSION_TOO_OLD = "IME_1202"
    COMPATIBILITY_FRAMEWORK_MISMATCH = "IME_1203"
    
    # 超时错误 (1300-1399)
    TIMEOUT_INJECTION = "IME_1300"
    TIMEOUT_COMPOSITION = "IME_1301"
    TIMEOUT_STATUS_CHECK = "IME_1302"
    TIMEOUT_FOCUS_DETECTION = "IME_1303"
    
    # 状态错误 (1400-1499)
    STATE_INVALID = "IME_1400"
    STATE_NOT_INITIALIZED = "IME_1401"
    STATE_ALREADY_INITIALIZED = "IME_1402"
    STATE_COMPOSITION_CONFLICT = "IME_1403"
    STATE_IME_NOT_ACTIVE = "IME_1404"
    
    # 注入错误 (1500-1599)
    INJECTION_FAILED = "IME_1500"
    INJECTION_TEXT_TOO_LONG = "IME_1501"
    INJECTION_INVALID_ENCODING = "IME_1502"
    INJECTION_NO_TARGET = "IME_1503"
    INJECTION_METHOD_UNAVAILABLE = "IME_1504"
    
    # 网络/通信错误 (1600-1699)
    COMMUNICATION_DBUS_ERROR = "IME_1600"
    COMMUNICATION_COM_ERROR = "IME_1601"
    COMMUNICATION_API_ERROR = "IME_1602"
    
    # 资源错误 (1700-1799)
    RESOURCE_HANDLE_INVALID = "IME_1700"
    RESOURCE_MEMORY_ALLOCATION = "IME_1701"
    RESOURCE_FILE_NOT_FOUND = "IME_1702"
    
    # 未知/其他错误 (1900-1999)
    UNKNOWN_ERROR = "IME_1900"
    INTERNAL_ERROR = "IME_1901"


@dataclass
class IMEErrorContext:
    """IME错误上下文信息."""
    
    timestamp: datetime = field(default_factory=datetime.now)
    platform: str = sys.platform
    ime_name: Optional[str] = None
    app_name: Optional[str] = None
    operation: Optional[str] = None
    stack_trace: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)


class IMEException(Exception):
    """IME操作基础异常类."""
    
    def __init__(
        self,
        message: str,
        error_code: IMEErrorCode,
        context: Optional[IMEErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化IME异常.
        
        Args:
            message: 错误消息
            error_code: 错误码
            context: 错误上下文信息
            cause: 原始异常
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or IMEErrorContext()
        self.cause = cause
        
        # 自动填充堆栈跟踪
        if not self.context.stack_trace:
            self.context.stack_trace = traceback.format_exc()
    
    def __str__(self) -> str:
        """返回详细的错误描述."""
        parts = [
            f"[{self.error_code.value}] {self.message}"
        ]
        
        if self.context.operation:
            parts.append(f"Operation: {self.context.operation}")
        
        if self.context.ime_name:
            parts.append(f"IME: {self.context.ime_name}")
            
        if self.context.app_name:
            parts.append(f"App: {self.context.app_name}")
        
        if self.cause:
            parts.append(f"Caused by: {str(self.cause)}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式."""
        return {
            'error_code': self.error_code.value,
            'message': self.message,
            'timestamp': self.context.timestamp.isoformat(),
            'platform': self.context.platform,
            'ime_name': self.context.ime_name,
            'app_name': self.context.app_name,
            'operation': self.context.operation,
            'stack_trace': self.context.stack_trace,
            'additional_info': self.context.additional_info,
            'cause': str(self.cause) if self.cause else None
        }


class IMEInitializationError(IMEException):
    """IME初始化异常."""
    
    def __init__(
        self,
        message: str = "IME initialization failed",
        error_code: IMEErrorCode = IMEErrorCode.INIT_GENERAL_ERROR,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class IMEPermissionError(IMEException):
    """IME权限异常."""
    
    def __init__(
        self,
        message: str = "IME permission denied",
        error_code: IMEErrorCode = IMEErrorCode.PERMISSION_ACCESSIBILITY_DENIED,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class IMECompatibilityError(IMEException):
    """IME兼容性异常."""
    
    def __init__(
        self,
        message: str = "IME compatibility error",
        error_code: IMEErrorCode = IMEErrorCode.COMPATIBILITY_APP_NOT_SUPPORTED,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class IMETimeoutError(IMEException):
    """IME超时异常."""
    
    def __init__(
        self,
        message: str = "IME operation timeout",
        error_code: IMEErrorCode = IMEErrorCode.TIMEOUT_INJECTION,
        timeout_seconds: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)
        if timeout_seconds and self.context:
            self.context.additional_info['timeout_seconds'] = timeout_seconds


class IMEStateError(IMEException):
    """IME状态异常."""
    
    def __init__(
        self,
        message: str = "IME state error",
        error_code: IMEErrorCode = IMEErrorCode.STATE_INVALID,
        current_state: Optional[str] = None,
        expected_state: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)
        if self.context:
            if current_state:
                self.context.additional_info['current_state'] = current_state
            if expected_state:
                self.context.additional_info['expected_state'] = expected_state


class IMEInjectionError(IMEException):
    """IME注入异常."""
    
    def __init__(
        self,
        message: str = "IME text injection failed",
        error_code: IMEErrorCode = IMEErrorCode.INJECTION_FAILED,
        text_length: Optional[int] = None,
        injection_method: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)
        if self.context:
            if text_length is not None:
                self.context.additional_info['text_length'] = text_length
            if injection_method:
                self.context.additional_info['injection_method'] = injection_method


class IMECommunicationError(IMEException):
    """IME通信异常."""
    
    def __init__(
        self,
        message: str = "IME communication error",
        error_code: IMEErrorCode = IMEErrorCode.COMMUNICATION_API_ERROR,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class IMEResourceError(IMEException):
    """IME资源异常."""
    
    def __init__(
        self,
        message: str = "IME resource error",
        error_code: IMEErrorCode = IMEErrorCode.RESOURCE_HANDLE_INVALID,
        **kwargs
    ):
        super().__init__(message, error_code, **kwargs)


class IMEErrorHandler:
    """IME错误处理器."""
    
    def __init__(self, logger_name: str = __name__):
        """
        初始化错误处理器.
        
        Args:
            logger_name: 日志器名称
        """
        self.logger = logging.getLogger(logger_name)
        self._error_history: List[IMEException] = []
        self._max_history = 100
    
    def handle_exception(
        self,
        exc: IMEException,
        log_level: int = logging.ERROR,
        include_stack: bool = True
    ) -> None:
        """
        处理IME异常.
        
        Args:
            exc: IME异常
            log_level: 日志级别
            include_stack: 是否包含堆栈跟踪
        """
        # 记录到历史
        self._error_history.append(exc)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
        
        # 构造日志消息
        log_data = {
            'error_code': exc.error_code.value,
            'message': exc.message,
            'platform': exc.context.platform,
            'operation': exc.context.operation,
            'ime_name': exc.context.ime_name,
            'app_name': exc.context.app_name
        }
        
        if exc.context.additional_info:
            log_data.update(exc.context.additional_info)
        
        # 记录日志
        self.logger.log(
            log_level,
            f"IME Error: {exc}",
            extra=log_data,
            exc_info=include_stack and exc.cause
        )
    
    def create_context(
        self,
        operation: Optional[str] = None,
        ime_name: Optional[str] = None,
        app_name: Optional[str] = None,
        **additional_info
    ) -> IMEErrorContext:
        """
        创建错误上下文.
        
        Args:
            operation: 操作名称
            ime_name: IME名称
            app_name: 应用程序名称
            **additional_info: 额外信息
            
        Returns:
            错误上下文对象
        """
        return IMEErrorContext(
            operation=operation,
            ime_name=ime_name,
            app_name=app_name,
            additional_info=additional_info
        )
    
    def get_error_history(self, limit: Optional[int] = None) -> List[IMEException]:
        """
        获取错误历史.
        
        Args:
            limit: 限制返回数量
            
        Returns:
            错误历史列表
        """
        if limit:
            return self._error_history[-limit:]
        return self._error_history.copy()
    
    def clear_error_history(self) -> None:
        """清除错误历史."""
        self._error_history.clear()
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息.
        
        Returns:
            错误统计字典
        """
        if not self._error_history:
            return {
                'total_errors': 0,
                'error_types': {},
                'error_codes': {},
                'platforms': {},
                'operations': {}
            }
        
        # 统计错误类型
        error_types = {}
        error_codes = {}
        platforms = {}
        operations = {}
        
        for exc in self._error_history:
            # 错误类型
            exc_type = type(exc).__name__
            error_types[exc_type] = error_types.get(exc_type, 0) + 1
            
            # 错误码
            code = exc.error_code.value
            error_codes[code] = error_codes.get(code, 0) + 1
            
            # 平台
            platform = exc.context.platform
            platforms[platform] = platforms.get(platform, 0) + 1
            
            # 操作
            if exc.context.operation:
                op = exc.context.operation
                operations[op] = operations.get(op, 0) + 1
        
        return {
            'total_errors': len(self._error_history),
            'error_types': error_types,
            'error_codes': error_codes,
            'platforms': platforms,
            'operations': operations
        }


# 全局错误处理器实例
_global_error_handler = IMEErrorHandler()


def handle_ime_exception(
    exc: IMEException,
    log_level: int = logging.ERROR,
    include_stack: bool = True
) -> None:
    """
    处理IME异常的便捷函数.
    
    Args:
        exc: IME异常
        log_level: 日志级别
        include_stack: 是否包含堆栈跟踪
    """
    _global_error_handler.handle_exception(exc, log_level, include_stack)


def create_ime_context(
    operation: Optional[str] = None,
    ime_name: Optional[str] = None,
    app_name: Optional[str] = None,
    **additional_info
) -> IMEErrorContext:
    """
    创建IME错误上下文的便捷函数.
    
    Args:
        operation: 操作名称
        ime_name: IME名称
        app_name: 应用程序名称
        **additional_info: 额外信息
        
    Returns:
        错误上下文对象
    """
    return _global_error_handler.create_context(
        operation, ime_name, app_name, **additional_info
    )


def get_ime_error_history(limit: Optional[int] = None) -> List[IMEException]:
    """
    获取IME错误历史的便捷函数.
    
    Args:
        limit: 限制返回数量
        
    Returns:
        错误历史列表
    """
    return _global_error_handler.get_error_history(limit)


def get_ime_error_statistics() -> Dict[str, Any]:
    """
    获取IME错误统计信息的便捷函数.
    
    Returns:
        错误统计字典
    """
    return _global_error_handler.get_error_statistics()


# 错误码到用户友好消息的映射
ERROR_MESSAGES = {
    IMEErrorCode.INIT_PLATFORM_NOT_SUPPORTED: "当前操作系统不支持此IME功能",
    IMEErrorCode.INIT_LIBRARY_NOT_FOUND: "缺少必要的系统库，请安装相关依赖",
    IMEErrorCode.INIT_PERMISSIONS_DENIED: "权限不足，请授予必要的系统权限",
    
    IMEErrorCode.PERMISSION_ACCESSIBILITY_DENIED: "需要辅助功能权限才能进行文本注入",
    IMEErrorCode.PERMISSION_INPUT_MONITORING_DENIED: "需要输入监控权限才能检测IME状态",
    IMEErrorCode.PERMISSION_ADMIN_REQUIRED: "需要管理员权限才能执行此操作",
    
    IMEErrorCode.COMPATIBILITY_APP_NOT_SUPPORTED: "当前应用程序不支持IME文本注入",
    IMEErrorCode.COMPATIBILITY_IME_NOT_SUPPORTED: "当前输入法不受支持",
    IMEErrorCode.COMPATIBILITY_OS_VERSION_TOO_OLD: "操作系统版本过低，请升级系统",
    
    IMEErrorCode.TIMEOUT_INJECTION: "文本注入操作超时，请重试",
    IMEErrorCode.TIMEOUT_COMPOSITION: "IME组合操作超时",
    IMEErrorCode.TIMEOUT_STATUS_CHECK: "IME状态检查超时",
    
    IMEErrorCode.STATE_NOT_INITIALIZED: "IME系统未初始化",
    IMEErrorCode.STATE_IME_NOT_ACTIVE: "输入法未激活，请切换到中文输入法",
    
    IMEErrorCode.INJECTION_FAILED: "文本注入失败，请检查目标应用程序",
    IMEErrorCode.INJECTION_TEXT_TOO_LONG: "文本过长，请分段输入",
    IMEErrorCode.INJECTION_NO_TARGET: "未找到可输入的目标窗口"
}


def get_user_friendly_message(error_code: IMEErrorCode) -> str:
    """
    获取用户友好的错误消息.
    
    Args:
        error_code: 错误码
        
    Returns:
        用户友好的错误消息
    """
    return ERROR_MESSAGES.get(error_code, "未知错误，请查看日志获取详细信息")