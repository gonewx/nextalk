"""
IME状态监控器 - 实时监控IME状态和焦点变化。

提供异步事件流接口，跟踪IME状态变化和系统焦点切换。
"""

import asyncio
import logging
import time
import sys
from enum import Enum
from typing import Optional, Dict, Any, AsyncGenerator, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime

from .ime_base import (
    IMEStateEvent, FocusEvent, IMEStatus, IMEInfo, CompositionState,
    IMEStateMonitor, IMEException
)
from .ime_manager import IMEManager


logger = logging.getLogger(__name__)


class MonitorState(Enum):
    """监控器状态."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class MonitorEvent(Enum):
    """监控器事件."""
    IME_STATUS_CHANGED = "ime_status_changed"
    FOCUS_CHANGED = "focus_changed"
    IME_ACTIVATED = "ime_activated"
    IME_DEACTIVATED = "ime_deactivated"
    COMPOSITION_STARTED = "composition_started"
    COMPOSITION_ENDED = "composition_ended"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class MonitorConfig:
    """监控器配置."""
    monitor_interval: float = 0.1
    focus_change_debounce: float = 0.05
    ime_state_debounce: float = 0.02
    enable_composition_monitoring: bool = True
    enable_focus_monitoring: bool = True
    max_error_count: int = 10
    error_reset_interval: float = 60.0


@dataclass
class MonitorStats:
    """监控器统计信息."""
    start_time: datetime = field(default_factory=datetime.now)
    ime_events_count: int = 0
    focus_events_count: int = 0
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    last_ime_change: Optional[datetime] = None
    last_focus_change: Optional[datetime] = None


class IMEStateMonitorManager:
    """IME状态监控管理器."""
    
    def __init__(self, ime_manager: IMEManager, config: Optional[Dict[str, Any]] = None):
        """
        初始化IME状态监控管理器.
        
        Args:
            ime_manager: IME管理器实例
            config: 监控配置
        """
        self.ime_manager = ime_manager
        self.config = MonitorConfig(**(config or {}))
        self.stats = MonitorStats()
        self.logger = logging.getLogger(f"{__name__}.IMEStateMonitorManager")
        
        # 状态管理
        self._state = MonitorState.STOPPED
        self._monitor_task: Optional[asyncio.Task] = None
        self._focus_monitor_task: Optional[asyncio.Task] = None
        self._ime_monitor_task: Optional[asyncio.Task] = None
        
        # 事件处理
        self._event_handlers: Dict[MonitorEvent, Set[Callable]] = {
            event: set() for event in MonitorEvent
        }
        
        # 状态缓存
        self._last_ime_status: Optional[IMEStatus] = None
        self._last_focus_info: Optional[Dict[str, Any]] = None
        self._last_composition_state: Optional[CompositionState] = None
        
        # 去抖动
        self._last_ime_change_time = 0.0
        self._last_focus_change_time = 0.0
        
        # 错误处理
        self._consecutive_errors = 0
        self._last_error_reset = time.time()
    
    @property
    def state(self) -> MonitorState:
        """获取监控器状态."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """检查监控器是否正在运行."""
        return self._state == MonitorState.RUNNING
    
    async def start(self) -> bool:
        """
        启动监控器.
        
        Returns:
            启动成功返回True
        """
        if self._state == MonitorState.RUNNING:
            self.logger.warning("Monitor already running")
            return True
        
        if self._state == MonitorState.STARTING:
            self.logger.warning("Monitor already starting")
            return False
        
        self._state = MonitorState.STARTING
        
        try:
            # 确保IME管理器已初始化
            if not self.ime_manager.is_initialized:
                self.logger.error("IME manager not initialized")
                self._state = MonitorState.ERROR
                return False
            
            # 重置统计信息
            self.stats = MonitorStats()
            self._consecutive_errors = 0
            
            # 启动监控任务
            if self.config.enable_focus_monitoring:
                self._focus_monitor_task = asyncio.create_task(
                    self._monitor_focus_changes()
                )
            
            self._ime_monitor_task = asyncio.create_task(
                self._monitor_ime_state()
            )
            
            # 主监控任务
            self._monitor_task = asyncio.create_task(self._main_monitor_loop())
            
            self._state = MonitorState.RUNNING
            self.logger.info("IME state monitor started")
            
            # 触发启动事件
            await self._emit_event(MonitorEvent.IME_ACTIVATED, {
                'timestamp': datetime.now(),
                'message': 'IME state monitoring started'
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start monitor: {e}")
            self._state = MonitorState.ERROR
            await self._cleanup_tasks()
            return False
    
    async def stop(self) -> None:
        """停止监控器."""
        if self._state in [MonitorState.STOPPED, MonitorState.STOPPING]:
            return
        
        self._state = MonitorState.STOPPING
        self.logger.info("Stopping IME state monitor")
        
        try:
            # 停止所有监控任务
            await self._cleanup_tasks()
            
            # 触发停止事件
            await self._emit_event(MonitorEvent.IME_DEACTIVATED, {
                'timestamp': datetime.now(),
                'message': 'IME state monitoring stopped'
            })
            
            self._state = MonitorState.STOPPED
            self.logger.info("IME state monitor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping monitor: {e}")
            self._state = MonitorState.ERROR
    
    def add_event_handler(self, event: MonitorEvent, handler: Callable) -> None:
        """
        添加事件处理器.
        
        Args:
            event: 事件类型
            handler: 处理器函数
        """
        self._event_handlers[event].add(handler)
    
    def remove_event_handler(self, event: MonitorEvent, handler: Callable) -> None:
        """
        移除事件处理器.
        
        Args:
            event: 事件类型
            handler: 处理器函数
        """
        self._event_handlers[event].discard(handler)
    
    async def get_current_status(self) -> Optional[IMEStatus]:
        """
        获取当前IME状态.
        
        Returns:
            当前IME状态，如果获取失败返回None
        """
        try:
            return await self.ime_manager.get_ime_status()
        except Exception as e:
            self.logger.error(f"Failed to get current IME status: {e}")
            return None
    
    async def get_monitor_stats(self) -> MonitorStats:
        """
        获取监控器统计信息.
        
        Returns:
            监控器统计信息
        """
        return self.stats
    
    async def _main_monitor_loop(self) -> None:
        """主监控循环."""
        while self._state == MonitorState.RUNNING:
            try:
                # 检查错误重置
                now = time.time()
                if now - self._last_error_reset > self.config.error_reset_interval:
                    self._consecutive_errors = 0
                    self._last_error_reset = now
                
                # 检查错误计数
                if self._consecutive_errors >= self.config.max_error_count:
                    self.logger.error(f"Too many consecutive errors ({self._consecutive_errors}), stopping monitor")
                    await self._emit_event(MonitorEvent.ERROR_OCCURRED, {
                        'error': f'Too many consecutive errors: {self._consecutive_errors}',
                        'timestamp': datetime.now()
                    })
                    break
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in main monitor loop: {e}")
                self._consecutive_errors += 1
                self.stats.error_count += 1
                self.stats.last_error_time = datetime.now()
                
                await self._emit_event(MonitorEvent.ERROR_OCCURRED, {
                    'error': str(e),
                    'timestamp': datetime.now()
                })
                
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _monitor_ime_state(self) -> None:
        """监控IME状态变化."""
        while self._state == MonitorState.RUNNING:
            try:
                current_status = await self.ime_manager.get_ime_status()
                
                if current_status and self._should_emit_ime_event(current_status):
                    # 更新统计信息
                    self.stats.ime_events_count += 1
                    self.stats.last_ime_change = datetime.now()
                    
                    # 检查组合状态变化
                    if (self.config.enable_composition_monitoring and 
                        self._last_composition_state != current_status.composition_state):
                        
                        if current_status.composition_state == CompositionState.COMPOSING:
                            await self._emit_event(MonitorEvent.COMPOSITION_STARTED, {
                                'ime_status': current_status,
                                'timestamp': datetime.now()
                            })
                        elif (self._last_composition_state == CompositionState.COMPOSING and
                              current_status.composition_state in [CompositionState.COMMITTED, 
                                                                  CompositionState.CANCELLED]):
                            await self._emit_event(MonitorEvent.COMPOSITION_ENDED, {
                                'ime_status': current_status,
                                'previous_state': self._last_composition_state,
                                'timestamp': datetime.now()
                            })
                    
                    # 触发状态变化事件
                    await self._emit_event(MonitorEvent.IME_STATUS_CHANGED, {
                        'old_status': self._last_ime_status,
                        'new_status': current_status,
                        'timestamp': datetime.now()
                    })
                    
                    self._last_ime_status = current_status
                    self._last_composition_state = current_status.composition_state
                    self._last_ime_change_time = time.time()
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring IME state: {e}")
                self._consecutive_errors += 1
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _monitor_focus_changes(self) -> None:
        """监控焦点变化."""
        while self._state == MonitorState.RUNNING:
            try:
                # 获取当前焦点信息（通过平台特定的适配器）
                current_focus = await self._get_current_focus_info()
                
                if current_focus and self._should_emit_focus_event(current_focus):
                    # 更新统计信息
                    self.stats.focus_events_count += 1
                    self.stats.last_focus_change = datetime.now()
                    
                    # 触发焦点变化事件
                    await self._emit_event(MonitorEvent.FOCUS_CHANGED, {
                        'old_focus': self._last_focus_info,
                        'new_focus': current_focus,
                        'timestamp': datetime.now()
                    })
                    
                    self._last_focus_info = current_focus
                    self._last_focus_change_time = time.time()
                
                await asyncio.sleep(self.config.monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring focus changes: {e}")
                self._consecutive_errors += 1
                await asyncio.sleep(self.config.monitor_interval)
    
    async def _get_current_focus_info(self) -> Optional[Dict[str, Any]]:
        """获取当前焦点信息."""
        try:
            # 通过IME管理器获取焦点信息
            adapter = self.ime_manager._get_platform_adapter()
            if adapter and hasattr(adapter, '_get_focus_info'):
                return await adapter._get_focus_info()
            return None
        except Exception as e:
            self.logger.debug(f"Failed to get focus info: {e}")
            return None
    
    def _should_emit_ime_event(self, current_status: IMEStatus) -> bool:
        """判断是否应该触发IME事件."""
        if not self._last_ime_status:
            return True
        
        # 去抖动检查
        now = time.time()
        if now - self._last_ime_change_time < self.config.ime_state_debounce:
            return False
        
        # 检查重要状态变化
        return (
            self._last_ime_status.current_ime != current_status.current_ime or
            self._last_ime_status.is_active != current_status.is_active or
            self._last_ime_status.focus_app != current_status.focus_app or
            self._last_ime_status.composition_state != current_status.composition_state
        )
    
    def _should_emit_focus_event(self, current_focus: Dict[str, Any]) -> bool:
        """判断是否应该触发焦点事件."""
        if not self._last_focus_info:
            return True
        
        # 去抖动检查
        now = time.time()
        if now - self._last_focus_change_time < self.config.focus_change_debounce:
            return False
        
        # 检查焦点变化
        return (
            self._last_focus_info.get('app_name') != current_focus.get('app_name') or
            self._last_focus_info.get('window_title') != current_focus.get('window_title')
        )
    
    async def _emit_event(self, event: MonitorEvent, data: Dict[str, Any]) -> None:
        """触发事件."""
        try:
            handlers = self._event_handlers.get(event, set())
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event, data)
                    else:
                        handler(event, data)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event}: {e}")
        except Exception as e:
            self.logger.error(f"Error emitting event {event}: {e}")
    
    async def _cleanup_tasks(self) -> None:
        """清理监控任务."""
        tasks = [
            self._monitor_task,
            self._focus_monitor_task, 
            self._ime_monitor_task
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.logger.error(f"Error cleaning up task: {e}")
        
        self._monitor_task = None
        self._focus_monitor_task = None
        self._ime_monitor_task = None


class CrossPlatformIMEMonitor:
    """跨平台IME监控器."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化跨平台IME监控器.
        
        Args:
            config: 监控配置
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.CrossPlatformIMEMonitor")
        self._platform_monitor: Optional[IMEStateMonitor] = None
        self._manager: Optional[IMEStateMonitorManager] = None
    
    async def initialize(self, ime_manager: IMEManager) -> bool:
        """
        初始化监控器.
        
        Args:
            ime_manager: IME管理器实例
            
        Returns:
            初始化成功返回True
        """
        try:
            # 创建监控管理器
            self._manager = IMEStateMonitorManager(ime_manager, self.config)
            
            # 创建平台特定监控器
            self._platform_monitor = self._create_platform_monitor()
            
            if self._platform_monitor:
                await self._platform_monitor.start_monitoring()
            
            self.logger.info("Cross-platform IME monitor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cross-platform monitor: {e}")
            return False
    
    async def start(self) -> bool:
        """启动监控器."""
        if self._manager:
            return await self._manager.start()
        return False
    
    async def stop(self) -> None:
        """停止监控器."""
        if self._manager:
            await self._manager.stop()
        
        if self._platform_monitor:
            await self._platform_monitor.stop_monitoring()
    
    def add_event_handler(self, event: MonitorEvent, handler: Callable) -> None:
        """添加事件处理器."""
        if self._manager:
            self._manager.add_event_handler(event, handler)
    
    def _create_platform_monitor(self) -> Optional[IMEStateMonitor]:
        """创建平台特定的监控器."""
        try:
            if sys.platform == "win32":
                from .ime_windows import WindowsIMEStateMonitor
                return WindowsIMEStateMonitor(self.config)
            elif sys.platform == "darwin":
                from .ime_macos import MacOSIMEStateMonitor
                return MacOSIMEStateMonitor(self.config)
            elif sys.platform.startswith("linux"):
                from .ime_linux import LinuxIMEStateMonitor
                return LinuxIMEStateMonitor(self.config)
            else:
                self.logger.warning(f"Unsupported platform: {sys.platform}")
                return None
        except ImportError as e:
            self.logger.error(f"Failed to import platform monitor: {e}")
            return None