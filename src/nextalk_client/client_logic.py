"""
NexTalk客户端核心逻辑。

该模块实现了客户端的主要功能逻辑，包括：
- 音频捕获和处理
- WebSocket通信
- 服务器消息处理
- 状态管理
- 模型切换请求
"""

import asyncio
import logging
import threading
from typing import Optional, Dict, Any, Callable
import json

from .audio.capture import AudioCapturer
from .network.client import WebSocketClient
from .config.loader import load_config
from .injection.injector_base import get_injector, BaseInjector
from .hotkey.listener import HotkeyListener
from .ui.tray_icon import SystemTrayIcon
from .ui.notifications import show_notification

from nextalk_shared.constants import (
    STATUS_IDLE,
    STATUS_LISTENING,
    STATUS_PROCESSING,
    STATUS_ERROR,
    STATUS_DISCONNECTED,
    STATUS_CONNECTED
)
from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate, CommandMessage


# 设置日志记录器
logger = logging.getLogger(__name__)


class NexTalkClient:
    """
    NexTalk客户端主类。
    
    整合音频捕获、WebSocket通信和配置管理，实现完整的客户端功能。
    """
    
    def __init__(self):
        """初始化NexTalk客户端。"""
        # 状态管理
        self.current_state = STATUS_IDLE
        self.is_listening = False
        self.is_connected = False
        self.is_processing = False
        
        # 加载配置
        self.config = load_config()
        self.client_config = self.config.get('Client', {})
        self.server_config = self.config.get('Server', {})
        logger.info("已加载客户端配置")
        
        # 获取音频后端设置
        audio_backend = self.client_config.get('audio_backend', 'pulse')
        
        # 初始化组件
        self.audio_capturer = AudioCapturer(audio_backend=audio_backend)
        self.websocket_client = WebSocketClient()
        
        # 初始化文本注入器
        self.injector: Optional[BaseInjector] = get_injector()
        if self.injector is None:
            logger.warning("无法初始化文本注入器，文本注入功能将不可用")
        else:
            logger.info("文本注入器初始化成功")
        
        # 初始化热键监听器
        self.hotkey_listener = HotkeyListener()
        logger.info("热键监听器初始化成功")
        
        # 初始化系统托盘图标
        self.tray_icon = SystemTrayIcon(name="NexTalk")
        logger.info("系统托盘图标初始化成功")
        
        # 设置WebSocket断开连接回调
        self._register_websocket_callbacks()
        
        # 异步事件循环和任务
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.main_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # 线程锁，用于线程安全的状态更新
        self._state_lock = threading.Lock()
    
    def _register_websocket_callbacks(self):
        """注册WebSocket客户端回调函数。"""
        self.websocket_client.message_callback = self._handle_server_message
        self.websocket_client.disconnect_callback = self._handle_disconnect
        self.websocket_client.error_callback = self._handle_error
        self.websocket_client.status_callback = self._handle_status_update
    
    async def start(self):
        """
        启动NexTalk客户端。
        
        连接到服务器并准备好开始处理音频。
        """
        logger.info("正在启动NexTalk客户端...")
        
        # 保存当前事件循环的引用
        self.loop = asyncio.get_event_loop()
        
        # 启动系统托盘图标
        tray_started = self.tray_icon.start(
            on_quit=self._handle_quit_request,
            model_select_callback=self._request_model_switch
        )
        if not tray_started:
            logger.warning("无法启动系统托盘图标，但客户端仍会继续运行")
        else:
            logger.info("系统托盘图标已启动")
        
        # 连接到服务器
        server_url = self.server_config.get('server_url', 'ws://127.0.0.1:8000/ws/stream')
        logger.info(f"正在连接到服务器: {server_url}")
        
        connected = await self.websocket_client.connect(server_url)
        if not connected:
            logger.error("无法连接到服务器，客户端启动失败")
            self._update_state(STATUS_ERROR)
            return False
        
        # 连接成功，开始监听服务器消息
        self.is_connected = True
        await self.websocket_client.listen()
        
        # 更新状态
        self._update_state(STATUS_CONNECTED)
        logger.info("NexTalk客户端已启动并连接到服务器")
        
        # 启动热键监听器
        hotkey = self.client_config.get('hotkey', 'ctrl+shift+space')
        logger.info(f"正在启动热键监听器，热键组合: {hotkey}")
        hotkey_started = self.hotkey_listener.start(
            hotkey_combination=hotkey,
            on_activate=self._activate_listening,
            on_deactivate=self._deactivate_listening
        )
        
        if not hotkey_started:
            logger.error(f"无法启动热键监听器，但客户端仍会继续运行")
        else:
            logger.info(f"热键监听器已启动，使用 {hotkey} 可以切换音频识别状态")
        
        # 重置关闭事件
        self._shutdown_event.clear()
        
        return True
    
    async def stop(self):
        """
        停止NexTalk客户端。
        
        停止所有正在进行的处理并断开与服务器的连接。
        """
        logger.info("正在停止NexTalk客户端...")
        
        # 停止系统托盘图标
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.stop()
            logger.info("系统托盘图标已停止")
        
        # 停止热键监听器
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            self.hotkey_listener.stop()
            logger.info("热键监听器已停止")
        
        # 如果正在录音，停止录音
        if self.is_listening:
            self._deactivate_listening()
        
        # 断开与服务器的连接
        if self.is_connected:
            await self.websocket_client.disconnect()
            self.is_connected = False
        
        # 更新状态
        self._update_state(STATUS_IDLE)
        
        # 设置关闭事件
        self._shutdown_event.set()
        
        logger.info("NexTalk客户端已停止")
        return True
    
    def _activate_listening(self):
        """
        激活音频监听。
        
        开始捕获音频并发送到服务器。
        """
        if self.is_listening:
            logger.warning("已经在监听音频，忽略激活请求")
            return False
        
        if not self.is_connected:
            logger.error("未连接到服务器，无法激活音频监听")
            
            # 显示连接错误通知
            try:
                show_notification(
                    title="NexTalk无法激活监听",
                    message="未连接到服务器，请确保服务器正在运行",
                    urgency="normal"
                )
            except Exception as e:
                logger.error(f"发送监听错误通知时出现异常: {e}")
                
            return False
        
        logger.info("正在激活音频监听...")
        
        # 开始音频捕获，设置回调
        started = self.audio_capturer.start_stream(self._handle_audio_chunk)
        if not started:
            logger.error("启动音频捕获失败")
            self._update_state(STATUS_ERROR)
            
            # 显示音频设备错误通知
            try:
                show_notification(
                    title="NexTalk音频设备错误",
                    message="无法启动音频捕获，请检查麦克风设置",
                    urgency="critical"
                )
            except Exception as e:
                logger.error(f"发送音频设备错误通知时出现异常: {e}")
                
            return False
        
        self.is_listening = True
        self._update_state(STATUS_LISTENING)
        logger.info("音频监听已激活")
        return True
    
    def _deactivate_listening(self):
        """
        停用音频监听。
        
        停止捕获并发送音频。
        """
        if not self.is_listening:
            logger.warning("未在监听音频，忽略停用请求")
            return False
        
        logger.info("正在停用音频监听...")
        
        # 停止音频捕获
        stopped = self.audio_capturer.stop_stream()
        if not stopped:
            logger.warning("停止音频捕获失败")
        
        self.is_listening = False
        
        if self.is_connected:
            self._update_state(STATUS_CONNECTED)
        else:
            self._update_state(STATUS_IDLE)
            
        logger.info("音频监听已停用")
        return True
    
    def _handle_audio_chunk(self, data: bytes):
        """
        处理音频数据块。
        
        将捕获的音频数据发送到服务器进行处理。
        
        Args:
            data: 从音频捕获器接收的音频数据块
        """
        if not self.is_connected or not self.is_listening:
            return
        
        # 创建异步任务发送音频数据
        asyncio.run_coroutine_threadsafe(
            self.websocket_client.send_audio(data),
            self.loop
        )
    
    def _handle_server_message(self, message):
        """
        处理从服务器接收到的消息。
        
        根据消息类型（transcription、error、status等）进行不同处理。
        
        Args:
            message: 从服务器接收到的消息对象
        """
        if not message:
            logger.warning("收到空消息")
            return
            
        # 根据消息类型分发处理
        try:
            if hasattr(message, 'type'):
                message_type = message.type
                
                if message_type == "transcription" and hasattr(message, 'text'):
                    # 处理转录结果
                    self._handle_transcription(message.text)
                    
                elif message_type == "error" and hasattr(message, 'message'):
                    # 处理错误消息
                    self._handle_error(message.message)
                    
                elif message_type == "status" and hasattr(message, 'state'):
                    # 处理状态更新
                    self._handle_status_update(message.state)
                    
                elif message_type == "command_result":
                    # 处理命令执行结果
                    self._handle_command_result(message)
                    
                else:
                    logger.warning(f"未知消息类型: {message_type}")
            else:
                logger.warning(f"消息缺少类型字段: {message}")
                
        except Exception as e:
            logger.error(f"处理服务器消息时出错: {e}")
            self._update_state(STATUS_ERROR)
    
    def _handle_transcription(self, text: str):
        """
        处理转录文本。
        
        接收转录文本并使用文本注入器将其注入到当前活动窗口。
        
        Args:
            text: 转录的文本
        """
        if not text or text.isspace():
            logger.debug("收到空白转录，忽略")
            return
            
        logger.info(f"转录结果: {text}")
        logger.info(f"转录结果字符数: {len(text)}, 类型: {type(text)}")
        print(f"语音识别结果: {text}")  # 在控制台打印转录结果
        
        # 调用文本注入器功能
        if self.injector:
            logger.info(f"开始文本注入, 注入器类型: {type(self.injector).__name__}")
            success = self.injector.inject_text(text)
            if success:
                logger.info(f"文本注入成功, 内容: {text[:30]}...")
            else:
                logger.error(f"文本注入失败, 尝试注入内容: {text[:30]}...")
                logger.error("请检查xdotool是否正确安装，或尝试在终端执行 'xdotool type \"test\"' 测试")
        else:
            logger.warning("文本注入器不可用，无法执行文本注入")
            logger.error("请检查xdotool是否已安装，可使用命令: sudo apt install xdotool")
    
    def _handle_error(self, error_message: str):
        """
        处理错误消息。
        
        更新状态并记录错误。
        
        Args:
            error_message: 错误消息内容
        """
        # 使用线程锁保护状态更新
        with self._state_lock:
            logger.error(f"处理错误: {error_message}")
            
            # 临时将状态设置为错误状态
            previous_state = self.current_state
            self._update_state(STATUS_ERROR)
            
            # 如果当前正在处理，重置处理状态
            if self.is_processing:
                self.is_processing = False
            
            # 打印错误消息到控制台
            print(f"错误: {error_message}")
            
            # 显示桌面通知
            try:
                notification_sent = show_notification(
                    title="NexTalk错误",
                    message=error_message,
                    urgency="critical"
                )
                if notification_sent:
                    logger.debug("错误通知已发送")
                else:
                    logger.warning("无法发送错误通知")
            except Exception as e:
                logger.error(f"发送错误通知时出现异常: {e}")
            
            # 短暂延迟后恢复之前的状态（如果是连接或监听状态）
            if self.is_listening:
                # 延迟2秒后恢复监听状态
                loop = asyncio.get_event_loop()
                loop.call_later(2, self._delayed_state_restore, STATUS_LISTENING)
            elif self.is_connected:
                # 延迟2秒后恢复连接状态
                loop = asyncio.get_event_loop()
                loop.call_later(2, self._delayed_state_restore, STATUS_CONNECTED)
    
    def _delayed_state_restore(self, state: str):
        """
        延迟恢复状态。
        
        用于错误状态短暂显示后恢复到正常状态。
        
        Args:
            state: 要恢复的状态
        """
        with self._state_lock:
            if self.current_state == STATUS_ERROR:
                self._update_state(state)
    
    def _handle_status_update(self, status: str):
        """
        处理状态更新消息。
        
        根据服务器报告的状态调整客户端状态。
        
        Args:
            status: 服务器报告的状态
        """
        logger.debug(f"处理状态更新: {status}")
        
        # 使用线程锁保护状态更新
        with self._state_lock:
            # 根据服务器状态进行客户端状态逻辑处理
            if status == STATUS_DISCONNECTED and self.is_connected:
                # 服务器报告断开连接
                self.is_connected = False
                self._handle_disconnect()
            elif status == STATUS_ERROR:
                # 服务器报告错误
                logger.warning("服务器报告错误状态")
                # 不直接将客户端状态设为错误，等待具体的错误消息
                # 错误状态应该是短暂的，所以不更新UI
            
            # 记录服务器状态，但不一定更新客户端UI状态
            # 客户端UI状态应反映客户端的实际状态而不仅是服务器状态
            logger.debug(f"服务器状态: {status}, 客户端状态: {self.current_state}")
    
    def _handle_disconnect(self):
        """处理与服务器的连接断开。"""
        logger.info("与服务器的连接已断开")
        self.is_connected = False
        
        # 如果正在监听，停止监听
        if self.is_listening:
            self._deactivate_listening()
        
        self._update_state(STATUS_DISCONNECTED)
        
        # 显示断开连接通知
        try:
            notification_sent = show_notification(
                title="NexTalk连接断开",
                message="与服务器的连接已断开，请检查网络连接或服务器状态",
                urgency="normal"
            )
            if notification_sent:
                logger.debug("断开连接通知已发送")
            else:
                logger.warning("无法发送断开连接通知")
        except Exception as e:
            logger.error(f"发送断开连接通知时出现异常: {e}")
    
    def _update_state(self, new_state: str):
        """
        更新客户端状态。
        
        使用线程锁确保状态更新的线程安全。
        
        Args:
            new_state: 新的状态字符串
        """
        with self._state_lock:
            if self.current_state == new_state:
                return
            
            logger.info(f"客户端状态从 {self.current_state} 变更为 {new_state}")
            self.current_state = new_state
            
            # 状态变更时的特殊处理
            if new_state == STATUS_PROCESSING:
                self.is_processing = True
            elif new_state == STATUS_LISTENING:
                self.is_processing = False
            
            # 更新UI状态
            self._update_ui_state(new_state)
    
    def _update_ui_state(self, new_state: str):
        """
        更新UI状态。
        
        将状态更新传递给系统托盘图标，以便更新图标显示。
        
        Args:
            new_state: 新的状态字符串
        """
        try:
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.update_state(new_state)
                logger.debug(f"已更新系统托盘图标状态为: {new_state}")
        except Exception as e:
            logger.error(f"更新系统托盘图标状态时出错: {e}")
    
    def toggle_listening(self):
        """
        切换监听状态。
        
        如果当前在监听，则停止；如果当前未监听，则开始。
        用于热键触发。
        
        Returns:
            bool: 新的监听状态
        """
        if self.is_listening:
            self._deactivate_listening()
        else:
            self._activate_listening()
        
        return self.is_listening
    
    def _handle_quit_request(self):
        """
        处理来自系统托盘的退出请求。
        
        创建异步任务调用stop()方法。
        """
        logger.info("收到来自系统托盘的退出请求")
        
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.stop(), self.loop)
        else:
            logger.error("无法处理退出请求：事件循环不可用或已关闭")
    
    def _request_model_switch(self, model_size: str):
        """
        请求切换语音识别模型。
        
        向服务器发送模型切换命令，可以通过WebSocket或REST API。
        
        Args:
            model_size: 要切换到的模型大小（例如 "tiny.en", "small.en", "base.en"）
        """
        if not self.is_connected:
            logger.error("未连接到服务器，无法请求模型切换")
            
            # 显示错误通知
            try:
                show_notification(
                    title="NexTalk模型切换失败",
                    message="未连接到服务器，无法切换模型",
                    urgency="normal"
                )
            except Exception as e:
                logger.error(f"发送模型切换错误通知时出现异常: {e}")
                
            return False
            
        logger.info(f"请求切换到模型: {model_size}")
        
        # 更新状态，表示正在处理
        old_state = self.current_state
        self._update_state(STATUS_PROCESSING)
        
        # 通过WebSocket发送命令消息
        try:
            # 创建命令消息
            command = CommandMessage(
                command="switch_model",
                payload=model_size
            )
            
            # 异步发送命令
            asyncio.run_coroutine_threadsafe(
                self.websocket_client.send_json(command.dict()),
                self.loop
            )
            
            # 更新托盘图标中的当前模型
            if hasattr(self, 'tray_icon') and self.tray_icon:
                self.tray_icon.update_current_model(model_size)
                
            logger.info(f"已发送模型切换命令: {model_size}")
            return True
            
        except Exception as e:
            logger.error(f"发送模型切换命令时出错: {e}")
            
            # 恢复之前的状态
            self._update_state(old_state)
            
            # 显示错误通知
            try:
                show_notification(
                    title="NexTalk模型切换失败",
                    message=f"发送切换命令时出错: {str(e)}",
                    urgency="normal"
                )
            except Exception as e2:
                logger.error(f"发送模型切换错误通知时出现异常: {e2}")
                
            return False
    
    def _handle_command_result(self, result):
        """
        处理命令执行结果消息。
        
        Args:
            result: 命令执行结果消息对象
        """
        if not hasattr(result, 'command') or not hasattr(result, 'status'):
            logger.warning("收到格式不正确的命令结果消息")
            return
            
        command = result.command
        status = result.status
        message = getattr(result, 'message', '')
        
        logger.info(f"收到命令执行结果: {command}, 状态: {status}, 消息: {message}")
        
        # 处理模型切换命令结果
        if command == "switch_model":
            if status == "success":
                logger.info(f"模型切换成功: {message}")
                
                # 恢复到IDLE状态
                self._update_state(STATUS_IDLE)
                
                # 显示成功通知
                try:
                    show_notification(
                        title="NexTalk模型切换成功",
                        message=message,
                        urgency="low"
                    )
                except Exception as e:
                    logger.error(f"发送模型切换成功通知时出现异常: {e}")
                    
            else:
                logger.error(f"模型切换失败: {message}")
                
                # 更新状态为错误
                self._update_state(STATUS_ERROR)
                
                # 显示错误通知
                try:
                    show_notification(
                        title="NexTalk模型切换失败",
                        message=message,
                        urgency="normal"
                    )
                except Exception as e:
                    logger.error(f"发送模型切换失败通知时出现异常: {e}")
        else:
            logger.debug(f"收到未处理的命令结果: {command}")
            
            # 恢复到IDLE状态
            self._update_state(STATUS_IDLE) 