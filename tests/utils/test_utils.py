"""
测试工具函数 - 提供强化的清理和超时机制
"""

import asyncio
import functools
import signal
import sys
import threading
import time
import warnings
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


def timeout_test(timeout: int = 30):
    """
    测试超时装饰器 - 为异步测试添加强制超时保护
    
    Args:
        timeout: 超时时间（秒）
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 设置计时器
            timer = None
            
            def timeout_handler():
                logger.error(f"测试 {func.__name__} 超时 ({timeout}秒)")
                # 尝试获取当前事件循环并停止
                try:
                    loop = asyncio.get_running_loop()
                    for task in asyncio.all_tasks(loop):
                        if not task.done():
                            task.cancel()
                    # 强制退出
                    sys.exit(124)
                except Exception as e:
                    logger.error(f"超时处理失败: {e}")
                    sys.exit(124)
            
            timer = threading.Timer(timeout, timeout_handler)
            timer.start()
            
            try:
                # 使用 asyncio.wait_for 添加双重保护
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout-1)
                return result
            except asyncio.TimeoutError:
                logger.error(f"测试 {func.__name__} asyncio 超时")
                raise
            finally:
                if timer:
                    timer.cancel()
        
        return wrapper
    return decorator


class AsyncTaskManager:
    """异步任务管理器 - 确保所有任务正确清理"""
    
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.loop = loop or asyncio.get_event_loop()
        self.tasks = set()
        self.cleanup_timeout = 5.0
    
    def create_task(self, coro, name: Optional[str] = None) -> asyncio.Task:
        """创建并跟踪异步任务"""
        task = self.loop.create_task(coro, name=name)
        self.tasks.add(task)
        
        # 添加完成回调以自动清理
        def cleanup_task(t):
            self.tasks.discard(t)
        
        task.add_done_callback(cleanup_task)
        return task
    
    async def cleanup_all(self, force: bool = False) -> None:
        """清理所有未完成的任务"""
        if not self.tasks:
            return
        
        logger.debug(f"清理 {len(self.tasks)} 个异步任务")
        
        # 首先取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务完成或超时
        if self.tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.tasks, return_exceptions=True),
                    timeout=self.cleanup_timeout if not force else 1.0
                )
            except asyncio.TimeoutError:
                if force:
                    logger.warning("强制清理：部分任务可能未正确终止")
                else:
                    logger.error("任务清理超时")
                    raise
            except Exception as e:
                logger.debug(f"任务清理过程中的异常（正常）: {e}")
        
        self.tasks.clear()


class WebSocketMockManager:
    """WebSocket模拟管理器 - 防止连接泄漏"""
    
    def __init__(self):
        self.connections = []
        self.closed = False
    
    def create_mock_websocket(self, **kwargs):
        """创建模拟的WebSocket连接"""
        from unittest.mock import AsyncMock, MagicMock
        
        mock_ws = AsyncMock()
        
        # 模拟基本方法
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.ping = AsyncMock()
        mock_ws.close = AsyncMock()
        
        # 模拟状态
        mock_ws.state = MagicMock()
        mock_ws.state.name = "OPEN"
        
        # 添加到连接列表
        self.connections.append(mock_ws)
        
        return mock_ws
    
    async def close_all(self):
        """关闭所有模拟连接"""
        if self.closed:
            return
        
        for conn in self.connections:
            try:
                if hasattr(conn, 'close'):
                    if asyncio.iscoroutinefunction(conn.close):
                        await conn.close()
                    else:
                        conn.close()
            except Exception as e:
                logger.debug(f"关闭模拟连接时出现异常: {e}")
        
        self.connections.clear()
        self.closed = True


class ForceCleanupEventLoop:
    """强制清理事件循环"""
    
    @staticmethod
    async def force_cleanup_loop(loop: asyncio.AbstractEventLoop, timeout: float = 3.0):
        """强制清理事件循环中的所有任务"""
        # 获取所有未完成的任务
        pending_tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        
        if not pending_tasks:
            return
        
        logger.debug(f"强制清理 {len(pending_tasks)} 个未完成任务")
        
        # 取消所有任务
        for task in pending_tasks:
            task.cancel()
        
        # 等待任务完成
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"强制清理超时，{len([t for t in pending_tasks if not t.done()])} 个任务可能未正确终止")
        except Exception as e:
            logger.debug(f"强制清理过程中的异常: {e}")
    
    @staticmethod
    def force_close_loop(loop: asyncio.AbstractEventLoop):
        """强制关闭事件循环"""
        if loop.is_running():
            logger.warning("尝试关闭正在运行的事件循环")
            return
        
        try:
            # 确保循环完全关闭
            if not loop.is_closed():
                loop.close()
        except Exception as e:
            logger.debug(f"关闭事件循环时出现异常: {e}")


def suppress_async_warnings():
    """抑制测试中的异步相关警告"""
    warnings.filterwarnings("ignore", message=".*coroutine.*was never awaited.*")
    warnings.filterwarnings("ignore", message=".*Task was destroyed but it is pending.*")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*was never awaited.*")


def setup_test_timeout_protection():
    """设置测试超时保护"""
    def timeout_handler(signum, frame):
        logger.error("测试进程超时，强制退出")
        # 尝试清理当前事件循环
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                for task in asyncio.all_tasks(loop):
                    task.cancel()
        except Exception:
            pass
        sys.exit(124)
    
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)


# 测试装饰器
def safe_async_test(timeout: int = 30):
    """
    安全的异步测试装饰器 - 结合超时和清理
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            task_manager = AsyncTaskManager()
            ws_manager = WebSocketMockManager()
            
            try:
                # 应用超时装饰器
                timed_func = timeout_test(timeout)(func)
                result = await timed_func(*args, **kwargs)
                return result
            finally:
                # 确保清理
                try:
                    await task_manager.cleanup_all()
                    await ws_manager.close_all()
                except Exception as e:
                    logger.debug(f"清理过程中的异常: {e}")
        
        return wrapper
    return decorator