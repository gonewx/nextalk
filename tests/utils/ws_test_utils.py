"""
WebSocket 测试工具 - 提供安全的 WebSocket 模拟和清理
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from unittest.mock import AsyncMock, MagicMock
import time

logger = logging.getLogger(__name__)


class SafeWebSocketMock:
    """安全的 WebSocket 模拟，确保正确清理"""
    
    def __init__(self, auto_responses: Optional[List[str]] = None):
        self.auto_responses = auto_responses or []
        self.response_index = 0
        self.closed = False
        self.send_count = 0
        self.recv_count = 0
        
        # 创建模拟方法
        self.send = AsyncMock(side_effect=self._mock_send)
        self.recv = AsyncMock(side_effect=self._mock_recv)
        self.close = AsyncMock(side_effect=self._mock_close)
        self.ping = AsyncMock(side_effect=self._mock_ping)
        
        # 模拟状态
        self.state = MagicMock()
        self.state.name = "OPEN"
        
        # 错误注入
        self.should_fail_send = False
        self.should_fail_recv = False
        self.recv_timeout = False
    
    async def _mock_send(self, data):
        """模拟发送"""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        
        if self.should_fail_send:
            raise Exception("Mock send error")
        
        self.send_count += 1
        logger.debug(f"Mock WebSocket sent: {data[:100] if isinstance(data, str) else data}")
    
    async def _mock_recv(self):
        """模拟接收"""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        
        if self.should_fail_recv:
            raise Exception("Mock recv error")
        
        if self.recv_timeout:
            await asyncio.sleep(10)  # 模拟超时
        
        if self.response_index < len(self.auto_responses):
            response = self.auto_responses[self.response_index]
            self.response_index += 1
            self.recv_count += 1
            logger.debug(f"Mock WebSocket received: {response[:100] if isinstance(response, str) else response}")
            return response
        
        # 如果没有更多预设响应，等待一段时间
        await asyncio.sleep(0.1)
        return '{"type": "status", "message": "mock"}'
    
    async def _mock_close(self):
        """模拟关闭"""
        self.closed = True
        self.state.name = "CLOSED"
        logger.debug("Mock WebSocket closed")
    
    async def _mock_ping(self):
        """模拟 ping"""
        if self.closed:
            raise ConnectionError("WebSocket is closed")
        
        # 返回一个可等待的对象
        async def pong():
            await asyncio.sleep(0.01)  # 模拟网络延迟
        
        return pong()


class WebSocketTestManager:
    """WebSocket 测试管理器 - 管理多个 WebSocket 模拟"""
    
    def __init__(self):
        self.websockets: List[SafeWebSocketMock] = []
        self.connection_factory = None
    
    def create_websocket(self, **kwargs) -> SafeWebSocketMock:
        """创建一个新的 WebSocket 模拟"""
        ws = SafeWebSocketMock(**kwargs)
        self.websockets.append(ws)
        return ws
    
    def set_connection_factory(self, factory: Callable):
        """设置连接工厂函数"""
        self.connection_factory = factory
    
    async def close_all(self):
        """关闭所有 WebSocket 连接"""
        for ws in self.websockets:
            try:
                if not ws.closed:
                    await ws.close()
            except Exception as e:
                logger.debug(f"关闭 WebSocket 模拟时出错: {e}")
        
        self.websockets.clear()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_websockets": len(self.websockets),
            "closed_websockets": sum(1 for ws in self.websockets if ws.closed),
            "total_sends": sum(ws.send_count for ws in self.websockets),
            "total_recvs": sum(ws.recv_count for ws in self.websockets)
        }


class AsyncTimeoutWrapper:
    """异步超时包装器"""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    async def run_with_timeout(self, coro, error_message: str = "Operation timed out"):
        """运行协程并添加超时保护"""
        try:
            return await asyncio.wait_for(coro, timeout=self.timeout)
        except asyncio.TimeoutError:
            logger.error(f"{error_message} (timeout: {self.timeout}s)")
            raise asyncio.TimeoutError(error_message)


def mock_websockets_connect():
    """创建 websockets.connect 的模拟"""
    manager = WebSocketTestManager()
    
    async def mock_connect(uri, **kwargs):
        """模拟 websockets.connect"""
        logger.debug(f"模拟连接到: {uri}")
        return manager.create_websocket()
    
    mock_connect.manager = manager
    return mock_connect


class WebSocketClientTestHelper:
    """WebSocket 客户端测试助手"""
    
    def __init__(self):
        self.client = None
        self.mock_connect = None
        self.timeout_wrapper = AsyncTimeoutWrapper(timeout=10.0)
    
    async def setup_client(self, client_class, config, **kwargs):
        """设置客户端进行测试"""
        self.client = client_class(config, **kwargs)
        
        # 设置模拟连接
        self.mock_connect = mock_websockets_connect()
        return self.client
    
    async def cleanup_client(self):
        """清理客户端"""
        if self.client:
            try:
                # 尝试断开连接
                await self.timeout_wrapper.run_with_timeout(
                    self.client.disconnect(),
                    "客户端断开连接超时"
                )
            except Exception as e:
                logger.debug(f"断开客户端连接时出错: {e}")
        
        if self.mock_connect and hasattr(self.mock_connect, 'manager'):
            try:
                await self.timeout_wrapper.run_with_timeout(
                    self.mock_connect.manager.close_all(),
                    "关闭模拟连接超时"
                )
            except Exception as e:
                logger.debug(f"关闭模拟连接时出错: {e}")
    
    async def wait_for_connection(self, max_wait: float = 5.0):
        """等待连接建立"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if self.client and self.client.is_connected():
                return True
            await asyncio.sleep(0.1)
        return False
    
    async def wait_for_disconnection(self, max_wait: float = 5.0):
        """等待连接断开"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if not self.client or not self.client.is_connected():
                return True
            await asyncio.sleep(0.1)
        return False


def create_test_websocket_responses():
    """创建测试用的 WebSocket 响应"""
    return [
        '{"type": "server_ready", "status": "ok"}',
        '{"type": "recognition_started", "session_id": "test123"}',
        '{"type": "partial_result", "text": "hello", "is_final": false}',
        '{"type": "final_result", "text": "hello world", "is_final": true}',
        '{"type": "recognition_ended", "session_id": "test123"}'
    ]


# 测试装饰器
def with_websocket_cleanup(func):
    """WebSocket 清理装饰器"""
    async def wrapper(*args, **kwargs):
        helper = WebSocketClientTestHelper()
        try:
            # 将 helper 注入到参数中
            if args and hasattr(args[0], '__dict__'):
                args[0].ws_helper = helper
            result = await func(*args, **kwargs)
            return result
        finally:
            await helper.cleanup_client()
    
    return wrapper