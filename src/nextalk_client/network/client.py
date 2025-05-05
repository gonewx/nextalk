"""
NexTalk WebSocket 客户端。

该模块提供了一个异步WebSocket客户端，用于与NexTalk服务器通信，
发送音频数据并接收转录结果。
"""

import json
import logging
import asyncio
from typing import Callable, Optional, Dict, Any, Union
import numpy as np

import websockets
from websockets.exceptions import ConnectionClosed

from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate
from nextalk_shared.constants import AUDIO_SILENCE_THRESHOLD, AUDIO_INIT_FRAME_COUNT

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
        
        # 音频包计数器（用于日志记录）
        self._audio_packet_counter = 0
    
    async def connect(self, url: str, use_ssl: bool = False) -> bool:
        """
        连接到WebSocket服务器。
        
        Args:
            url: WebSocket服务器URL（例如 ws://127.0.0.1:8000/ws
            use_ssl: 是否使用SSL连接
            
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"正在连接到服务器: {url}")
            
            if use_ssl:
                ssl_context = websockets.ssl.SSLContext()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = websockets.ssl.CERT_NONE
                self.connection = await websockets.connect(
                    url, 
                    subprotocols=["binary"], 
                    ping_interval=None, 
                    ssl=ssl_context
                )
            else:
                self.connection = await websockets.connect(
                    url,
                    subprotocols=["binary"],
                    ping_interval=None
                )
                
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
        发送音频数据到服务器。按照官方实现的简单发送方式。
        
        Args:
            data: 音频二进制数据
            
        Returns:
            bool: 发送是否成功
        """
        if not self.connected or not self.connection:
            logger.warning("尝试发送音频数据但未连接到服务器")
            return False
        
        try:
            # 直接发送数据，不做额外检查
            await self.connection.send(data)
            return True
        except ConnectionClosed as cc:
            logger.error(f"发送音频数据时WebSocket连接已关闭: {cc}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
            return False
            
        except Exception as e:
            logger.error(f"发送音频数据失败: {str(e)}")
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
        注册回调函数。
        
        Args:
            message_callback: 处理转录消息的回调函数
            error_callback: 处理错误消息的回调函数
            status_callback: 处理状态更新的回调函数
            disconnect_callback: 处理连接断开的回调函数
        """
        self.message_callback = message_callback
        self.error_callback = error_callback
        self.status_callback = status_callback
        self.disconnect_callback = disconnect_callback
    
    async def listen(self) -> None:
        """启动消息监听任务。"""
        if self.listening_task and not self.listening_task.done():
            logger.warning("消息监听任务已在运行")
            return
        
        self.listening_task = asyncio.create_task(self._listen())
    
    async def _listen(self) -> None:
        """
        监听并处理从服务器接收到的消息。
        
        持续监听WebSocket连接并处理接收到的消息。
        当收到消息时，会调用相应的回调函数。
        """
        if not self.connected or not self.connection:
            logger.error("未连接到服务器，无法监听消息")
            return
        
        try:
            logger.info("开始监听服务器消息")
            
            async for message in self.connection:
                try:
                    # 处理二进制消息或文本消息
                    if isinstance(message, bytes):
                        logger.warning("收到二进制消息，当前不支持处理")
                    else:
                        # 尝试解析JSON消息
                        try:
                            data = json.loads(message)
                            logger.debug(f"收到JSON消息: {str(data)[:100]}...")
                            
                            # 判断消息类型并调用相应的回调函数
                            if "type" in data:
                                message_type = data["type"]
                                
                                if message_type == "transcription" and self.message_callback:
                                    # 创建转录响应对象
                                    response = TranscriptionResponse(
                                        text=data.get("text", ""),
                                        is_final=data.get("is_final", True),
                                        mode=data.get("mode", ""),
                                        type="transcription"
                                    )
                                    self.message_callback(response)
                                    
                                elif message_type == "error" and self.error_callback:
                                    # 创建错误消息对象
                                    error = ErrorMessage(
                                        message=data.get("message", "未知错误"),
                                        code=data.get("code", 0),
                                        type="error"
                                    )
                                    self.error_callback(error)
                                    
                                elif message_type == "status" and self.status_callback:
                                    # 检查状态是否为空
                                    state = data.get("state", "")
                                    if not state:
                                        logger.warning("收到空状态消息，跳过回调")
                                        continue
                                        
                                    # 创建状态更新对象
                                    status = StatusUpdate(
                                        state=state,
                                        type="status"
                                    )
                                    self.status_callback(status)
                                    
                                else:
                                    logger.warning(f"未知消息类型: {message_type}")
                            else:
                                logger.warning(f"消息缺少类型字段: {str(data)[:100]}...")
                                
                        except json.JSONDecodeError:
                            logger.warning(f"收到无效的JSON消息: {message[:100]}...")
                        
                except Exception as e:
                    logger.error(f"处理服务器消息时出错: {str(e)}")
                    
        except ConnectionClosed as cc:
            logger.error(f"WebSocket连接已关闭: {str(cc)}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
        except Exception as e:
            logger.error(f"监听消息时出错: {str(e)}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到服务器。
        
        Returns:
            bool: 如果已连接则为True，否则为False
        """
        return self.connected
    
    async def start_recognition(self) -> bool:
        """
        开始进行语音识别。
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not self.connection:
            logger.error("无法开始语音识别：WebSocket未连接")
            return False
            
        try:
            logger.info("开始进行语音识别")
            # 发送开始命令
            await self.connection.send(json.dumps({
                "command": "start"
            }))
            
            return True
        except ConnectionClosed as cc:
            logger.error(f"开始语音识别时WebSocket连接已关闭: {str(cc)}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
            return False
        except Exception as e:
            logger.error(f"开始语音识别失败: {str(e)}")
            return False
    
    async def stop_recognition(self) -> bool:
        """
        停止语音识别。
        
        Returns:
            bool: 如果成功发送停止请求则为True，否则为False
        """
        logger.info("停止语音识别")
        # 由于简化后只要停止发送音频即可，无需额外操作
        return True
    
    async def send_stop_speaking_signal(self) -> bool:
        """
        发送停止说话信号。
        
        向服务器发送{"is_speaking": false}信号，通知服务器客户端已停止说话，
        这将促使服务器处理所有已发送的音频数据并生成最终结果。
        
        Returns:
            bool: 如果成功发送停止信号则为True，否则为False
        """
        if not self.connected or not self.connection:
            logger.warning("尝试发送停止说话信号但未连接到服务器")
            return False
        
        try:
            logger.info("发送停止说话信号")
            await self.connection.send(json.dumps({
                "is_speaking": False
            }))
            
            return True
        except ConnectionClosed as cc:
            logger.error(f"发送停止说话信号时WebSocket连接已关闭: {cc}")
            self.connected = False
            
            # 如果有断开连接回调，则调用
            if self.disconnect_callback:
                self.disconnect_callback()
                
            return False
            
        except Exception as e:
            logger.error(f"发送停止说话信号失败: {e}")
            return False 