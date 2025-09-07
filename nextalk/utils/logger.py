"""
Logging utilities for NexTalk.

Provides centralized logging configuration and utilities.
"""

import logging
import logging.handlers
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None,
                 use_colors: bool = True):
        """
        Initialize colored formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            use_colors: Whether to use colors
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
                record.msg = f"{self.COLORS[levelname]}{record.msg}{self.COLORS['RESET']}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename',
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread',
                          'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class LoggerManager:
    """Manages application logging configuration."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger manager."""
        if not self._initialized:
            self.loggers: Dict[str, logging.Logger] = {}
            self.log_dir: Optional[Path] = None
            self.log_level = logging.INFO
            self._initialized = True
    
    def setup(self, log_level: str = "INFO", log_dir: Optional[Path] = None,
             console: bool = True, file: bool = True, json_format: bool = False) -> None:
        """
        Setup logging configuration.
        
        Args:
            log_level: Logging level
            log_dir: Directory for log files
            console: Enable console logging
            file: Enable file logging
            json_format: Use JSON format
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir = log_dir
        
        # Create log directory if needed
        if file and log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(self.log_level)
            
            if json_format:
                console_formatter = JSONFormatter()
            else:
                console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                console_formatter = ColoredFormatter(console_format)
            
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler
        if file and log_dir:
            log_file = log_dir / f"nextalk_{datetime.now():%Y%m%d}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(self.log_level)
            
            if json_format:
                file_formatter = JSONFormatter()
            else:
                file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                file_formatter = logging.Formatter(file_format)
            
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Configure third-party loggers
        self._configure_third_party_loggers()
    
    def _configure_third_party_loggers(self) -> None:
        """Configure third-party library loggers."""
        # Reduce verbosity of third-party libraries
        third_party = [
            "asyncio",
            "websockets",
            "urllib3",
            "pyaudio",
            "pynput",
            "PIL"
        ]
        
        for name in third_party:
            logger = logging.getLogger(name)
            logger.setLevel(logging.WARNING)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        return self.loggers[name]
    
    def log_exception(self, logger: logging.Logger, msg: str = "Exception occurred") -> None:
        """
        Log exception with traceback.
        
        Args:
            logger: Logger to use
            msg: Error message
        """
        logger.error(msg, exc_info=True)
    
    def log_performance(self, logger: logging.Logger, operation: str,
                       duration: float, **kwargs) -> None:
        """
        Log performance metrics.
        
        Args:
            logger: Logger to use
            operation: Operation name
            duration: Duration in seconds
            **kwargs: Additional metrics
        """
        metrics = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            **kwargs
        }
        logger.info(f"Performance: {operation}", extra={'metrics': metrics})
    
    def create_session_logger(self, session_id: str) -> logging.Logger:
        """
        Create a logger for a specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session-specific logger
        """
        logger_name = f"nextalk.session.{session_id}"
        logger = self.get_logger(logger_name)
        
        # Add session ID to all logs
        class SessionFilter(logging.Filter):
            def filter(self, record):
                record.session_id = session_id
                return True
        
        logger.addFilter(SessionFilter())
        return logger
    
    def get_log_files(self) -> list[Path]:
        """
        Get list of log files.
        
        Returns:
            List of log file paths
        """
        if not self.log_dir or not self.log_dir.exists():
            return []
        
        return sorted(self.log_dir.glob("nextalk_*.log"))
    
    def rotate_logs(self) -> None:
        """Rotate log files."""
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.doRollover()
    
    def set_level(self, level: str, logger_name: Optional[str] = None) -> None:
        """
        Set logging level.
        
        Args:
            level: Log level
            logger_name: Optional specific logger name
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        if logger_name:
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
        else:
            logging.getLogger().setLevel(log_level)
            self.log_level = log_level


# Global logger manager instance
logger_manager = LoggerManager()


def setup_logging(log_level: str = "INFO", log_dir: Optional[Path] = None,
                 console: bool = True, file: bool = True,
                 json_format: bool = False) -> None:
    """
    Setup application logging.
    
    Args:
        log_level: Logging level
        log_dir: Directory for log files
        console: Enable console logging
        file: Enable file logging
        json_format: Use JSON format
    """
    logger_manager.setup(log_level, log_dir, console, file, json_format)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logger_manager.get_logger(name)


def log_exception(msg: str = "Exception occurred") -> None:
    """
    Log current exception.
    
    Args:
        msg: Error message
    """
    logger = logging.getLogger()
    logger_manager.log_exception(logger, msg)


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """
    Log performance metrics.
    
    Args:
        operation: Operation name
        duration: Duration in seconds
        **kwargs: Additional metrics
    """
    logger = logging.getLogger()
    logger_manager.log_performance(logger, operation, duration, **kwargs)