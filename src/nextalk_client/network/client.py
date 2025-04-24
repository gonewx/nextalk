"""
NexTalk WebSocket 客户端。

该模块提供了一个异步WebSocket客户端，用于与NexTalk服务器通信，
发送音频数据并接收转录结果。
"""

import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any, Union

import websockets
from websockets.exceptions import ConnectionClosed

from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate


# 设置日志记录器
logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    NexTalk WebSocket 客户端类。
    
    负责与服务器建立WebSocket连接，发送音频数据，
    以及接收和处理服务器响应（转录、错误和状态消息）。
    """
    
    def __init__(self):
        """初始化WebSocket客户端。"""
        self.connection = None
        self.listening_task = None
        self.connected = False
        self.message_callback = None
        self.error_callback = None
        self.status_callback = None
        self.disconnect_callback = None
    
    async def connect(self, url: str) -> bool:
        """
        连接到WebSocket服务器。
        
        Args:
            url: WebSocket服务器URL（例如 ws://127.0.0.1:8000/ws/stream）
            
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"正在连接到服务器: {url}")
            self.connection = await websockets.connect(url)
            self.connected = True
            logger.info("WebSocket连接已建立")
            return True
        except Exception as e:
            logger.error(f"连接到服务器失败: {str(e)}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开与WebSocket服务器的连接。"""
        try:
            if self.listening_task and not self.listening_task.done():
                self.listening_task.cancel()
                try:
                    await self.listening_task
                except asyncio.CancelledError:
                    logger.debug("监听任务已取消")
                
            if self.connection:
                await self.connection.close()
                logger.info("WebSocket连接已关闭")
            
            self.connected = False
            
            # 调用断开连接回调（如果有）
            if self.disconnect_callback:
                self.disconnect_callback()
                
        except Exception as e:
            logger.error(f"断开连接时出错: {str(e)}")
    
    async def send_audio(self, data: bytes) -> bool:
        """
        发送音频数据到服务器。
        
        Args:
            data: 音频二进制数据
            
        Returns:
            bool: 发送是否成功
        """
        if not self.connected or not self.connection:
            logger.warning("尝试发送音频数据但未连接到服务器")
            return False
        
        try:
            await self.connection.send(data)
            return True
        except Exception as e:
            logger.error(f"发送音频数据失败: {str(e)}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
            return False
    
    async def send_json(self, data: Union[Dict[str, Any], str]) -> bool:
        """
        发送JSON数据到服务器。
        
        用于发送命令消息，如模型切换请求。
        
        Args:
            data: 要发送的JSON数据（字典或已序列化的JSON字符串）
            
        Returns:
            bool: 发送是否成功
        """
        if not self.connected or not self.connection:
            logger.warning("尝试发送JSON数据但未连接到服务器")
            return False
        
        try:
            # 如果是字典，先转换为JSON字符串
            if isinstance(data, dict):
                json_data = json.dumps(data)
            else:
                json_data = data
                
            logger.debug(f"发送JSON数据: {json_data[:100]}...")
            await self.connection.send(json_data)
            return True
        except Exception as e:
            logger.error(f"发送JSON数据失败: {str(e)}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
            return False
    
    def register_callbacks(self, 
                           message_callback: Optional[Callable[[TranscriptionResponse], None]] = None,
                           error_callback: Optional[Callable[[ErrorMessage], None]] = None,
                           status_callback: Optional[Callable[[StatusUpdate], None]] = None,
                           disconnect_callback: Optional[Callable[[], None]] = None) -> None:
        """
        注册接收消息的回调函数。
        
        Args:
            message_callback: 接收到转录消息时调用的函数
            error_callback: 接收到错误消息时调用的函数
            status_callback: 接收到状态更新时调用的函数
            disconnect_callback: 连接断开时调用的函数
        """
        self.message_callback = message_callback
        self.error_callback = error_callback
        self.status_callback = status_callback
        self.disconnect_callback = disconnect_callback
    
    async def listen(self) -> None:
        """
        持续监听来自服务器的消息。
        
        启动一个异步任务来接收和处理服务器发送的JSON消息，
        根据消息类型调用相应的回调函数。
        """
        if not self.connected or not self.connection:
            logger.warning("尝试监听服务器消息但未连接到服务器")
            return
        
        async def _listen():
            try:
                logger.debug("开始监听服务器消息")
                while self.connected:
                    try:
                        # 接收消息
                        message = await self.connection.recv()
                        
                        # 处理消息 - 可能是文本(JSON)或二进制数据
                        try:
                            # 如果接收到的是字符串，则解析为JSON
                            if isinstance(message, str):
                                data = json.loads(message)
                            # 如果服务器直接发送了JSON对象
                            elif isinstance(message, bytes):
                                data = json.loads(message.decode('utf-8'))
                            else:
                                logger.warning(f"收到未知类型的消息: {type(message)}")
                                continue
                                
                            # 获取消息类型
                            message_type = data.get('type')
                            
                            # 根据消息类型处理并使用Pydantic模型验证
                            if message_type == 'transcription' and self.message_callback:
                                # 转录消息
                                try:
                                    response = TranscriptionResponse(**data)
                                    logger.debug(f"接收到转录: {response.text[:30]}...")
                                    logger.info(f"接收到完整转录结果，长度: {len(response.text)}, 内容: {response.text}")
                                    logger.debug(f"转录消息完整内容: {data}")
                                    self.message_callback(response)
                                    logger.debug("转录消息回调函数已调用")
                                except Exception as e:
                                    logger.error(f"处理转录消息失败: {str(e)}")
                                    logger.error(f"转录消息处理异常详情: {e}", exc_info=True)
                                    logger.error(f"原始数据: {data}")
                                
                            elif message_type == 'error' and self.error_callback:
                                # 错误消息
                                try:
                                    error = ErrorMessage(**data)
                                    logger.warning(f"接收到错误: {error.message}")
                                    self.error_callback(error)
                                except Exception as e:
                                    logger.error(f"处理错误消息失败: {str(e)}")
                                
                            elif message_type == 'status' and self.status_callback:
                                # 状态更新
                                try:
                                    status = StatusUpdate(**data)
                                    logger.debug(f"接收到状态更新: {status.state}")
                                    self.status_callback(status)
                                except Exception as e:
                                    logger.error(f"处理状态消息失败: {str(e)}")
                                
                            elif message_type == 'command_result' and self.message_callback:
                                # 命令结果消息
                                try:
                                    logger.debug(f"接收到命令结果: {data}")
                                    # 创建一个具有类型属性的简单对象
                                    class CommandResult:
                                        def __init__(self, **kwargs):
                                            for key, value in kwargs.items():
                                                setattr(self, key, value)
                                    
                                    result = CommandResult(**data)
                                    self.message_callback(result)
                                except Exception as e:
                                    logger.error(f"处理命令结果消息失败: {str(e)}")
                                
                            else:
                                logger.warning(f"接收到未知消息类型: {message_type}")
                                
                        except json.JSONDecodeError:
                            logger.error(f"解析JSON消息失败: {message[:100] if isinstance(message, str) else '非文本数据'}")
                        except Exception as e:
                            logger.error(f"处理消息时出错: {str(e)}")
                            
                    except ConnectionClosed:
                        logger.info("WebSocket连接已关闭")
                        self.connected = False
                        break
                    except Exception as e:
                        logger.error(f"接收消息时出错: {str(e)}")
                        
                # 连接已断开，调用回调
                if self.disconnect_callback:
                    self.disconnect_callback()
                    
            except asyncio.CancelledError:
                logger.debug("监听任务已取消")
                raise
            except Exception as e:
                logger.error(f"监听任务出错: {str(e)}")
                self.connected = False
                
                # 调用断开连接回调
                if self.disconnect_callback:
                    self.disconnect_callback()
        
        # 启动监听任务
        self.listening_task = asyncio.create_task(_listen())
        
    def is_connected(self) -> bool:
        """
        检查是否已连接到服务器。
        
        Returns:
            bool: 是否已连接
        """
        return self.connected 