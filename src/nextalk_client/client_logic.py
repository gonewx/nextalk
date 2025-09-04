"""
NexTalk客户端核心逻辑。

该模块实现了客户端的主要功能逻辑，包括：
- 音频捕获和处理
- WebSocket通信
- 服务器消息处理
- 状态管理
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Dict, Any, Callable
import numpy as np
import os

from .audio.capture import AudioCapturer
from .network.client import WebSocketClient
from .config.loader import load_config, get_client_bool_config
from .injection.injector_base import get_injector, BaseInjector
from .hotkey.listener import HotkeyListener
from .ui.tray_icon import SystemTrayIcon
from .ui.notifications import show_notification

# 导入简单窗口作为唯一的文本显示方法
from .ui.simple_window import show_text

from nextalk_shared.constants import (
    STATUS_IDLE,
    STATUS_LISTENING,
    STATUS_PROCESSING,
    STATUS_ERROR,
    STATUS_DISCONNECTED,
    STATUS_CONNECTED,
    STATUS_READY,
)
from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate


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

        # 状态锁定标志，用于防止意外状态切换
        self._listening_state_locked = False

        # 添加等待最终结果的标志
        self._waiting_for_final_result = False
        
        # 添加等待服务器就绪的标志
        self._waiting_for_server_ready = False
        self._server_ready_event = None  # 将在start()方法中初始化

        # 状态同步任务
        self._state_sync_task = None

        # 加载配置
        self.config = load_config()
        self.client_config = self.config.get("Client", {})
        self.server_config = self.config.get("Server", {})
        logger.debug("已加载客户端配置")

        # 初始化组件
        self.audio_capturer = AudioCapturer()
        self.websocket_client = WebSocketClient()

        # 初始化文本注入器
        injector_type = self.client_config.get("injector_type", "smart").lower()
        fallback_method = self.client_config.get("fallback_method", "auto").lower()
        
        # 根据配置选择注入器类型
        if injector_type == "legacy":
            self.injector: Optional[BaseInjector] = get_injector(use_smart=False, legacy=True)
            logger.info("使用旧版注入器")
        elif injector_type == "fallback":
            # 使用后备注入器
            from .injection.injector_fallback import FallbackInjector
            method = fallback_method if fallback_method != "auto" else None
            self.injector = FallbackInjector(method=method)
            logger.info(f"使用后备注入器，方法: {fallback_method}")
        else:  # 默认使用智能注入器
            self.injector = get_injector(use_smart=True, legacy=False)
            logger.info("使用智能注入器")
            
        if self.injector is None:
            logger.warning("无法初始化文本注入器，文本注入功能将不可用")
        else:
            logger.debug("文本注入器初始化成功")

        # 初始化热键监听器
        self.hotkey_listener = HotkeyListener()
        logger.debug("热键监听器初始化成功")

        # 初始化系统托盘图标
        self.tray_icon = SystemTrayIcon(name="NexTalk")
        logger.debug("系统托盘图标初始化成功")

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
        self.websocket_client.register_callbacks(
            message_callback=self._handle_server_message,
            error_callback=self._handle_error,
            status_callback=self._handle_status_update,
            disconnect_callback=self._handle_disconnect,
        )

    async def start(self):
        """
        启动NexTalk客户端。

        连接到服务器并准备好开始处理音频。
        """
        logger.info("正在启动NexTalk客户端...")

        # 保存当前事件循环的引用
        self.loop = asyncio.get_event_loop()
        
        # 初始化服务器就绪事件（需要在事件循环中创建）
        self._server_ready_event = asyncio.Event()

        # 启动系统托盘图标
        tray_started = self.tray_icon.start(on_quit=self._handle_quit_request)
        if not tray_started:
            logger.warning("无法启动系统托盘图标，但客户端仍会继续运行")
        else:
            logger.debug("系统托盘图标已启动")

        # 连接到服务器
        server_url = self.client_config.get("server_url", "ws://127.0.0.1:8000/ws/stream")
        use_ssl = get_client_bool_config("use_ssl", False)
        logger.info(f"正在连接到服务器: {server_url}")

        connected = await self.websocket_client.connect(server_url, use_ssl=use_ssl)
        if not connected:
            logger.error("无法连接到服务器，客户端启动失败")
            self._update_state(STATUS_ERROR)
            return False

        # 连接成功，开始监听服务器消息
        self.is_connected = True
        await self.websocket_client.listen()

        # 更新状态
        self._update_state(STATUS_CONNECTED)
        logger.debug("NexTalk客户端已启动并连接到服务器")

        # 启动热键监听器
        hotkey = self.client_config.get("hotkey", "ctrl+shift+space")
        logger.debug(f"正在启动热键监听器，热键组合: {hotkey}")
        hotkey_started = self.hotkey_listener.start(
            hotkey_combination=hotkey,
            on_activate=self._activate_listening,
            on_deactivate=self._deactivate_listening,
        )

        if not hotkey_started:
            logger.error(f"无法启动热键监听器，但客户端仍会继续运行")
        else:
            logger.debug(f"热键监听器已启动，使用 {hotkey} 可以切换音频识别状态")

        # 重置关闭事件
        self._shutdown_event.clear()

        return True

    async def stop(self):
        """
        停止NexTalk客户端。

        停止所有正在进行的处理并断开与服务器的连接。
        """
        # 防止重复停止
        if hasattr(self, "_stopping") and self._stopping:
            logger.debug("客户端已在停止过程中，跳过重复停止请求")
            return True

        # 设置停止标志
        self._stopping = True
        logger.info("正在停止NexTalk客户端...")

        # 停止热键监听
        try:
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                logger.debug("热键监听器已停止")
        except Exception as e:
            logger.error(f"停止热键监听器时出错: {str(e)}")

        # 停止音频捕获
        try:
            if self.is_listening:
                self.audio_capturer.stop_stream()
                logger.debug("音频捕获器已停止")
                self.is_listening = False
        except Exception as e:
            logger.error(f"停止音频捕获时出错: {str(e)}")

        # 断开WebSocket连接
        try:
            if self.websocket_client:
                await self.websocket_client.disconnect()
                logger.debug("WebSocket客户端已断开连接")
                self.is_connected = False
        except Exception as e:
            logger.error(f"断开WebSocket连接时出错: {str(e)}")

        # 停止系统托盘图标
        try:
            if self.tray_icon:
                self.tray_icon.stop()
                logger.debug("系统托盘图标已停止")
        except Exception as e:
            logger.error(f"停止系统托盘图标时出错: {str(e)}")

        # 清除停止标志
        self._stopping = False
        logger.info("NexTalk客户端已完全停止")

        return True

    def _activate_listening(self):
        """
        激活音频监听。

        首先发送开始命令给服务器，等待就绪确认后再开始音频捕获。
        """
        logger.debug("正在激活音频监听...")

        # 检查是否已经在等待最终结果
        if getattr(self, "_waiting_for_final_result", False):
            logger.warning("当前正在等待最终结果，无法重新激活音频监听")
            return False

        # 如果已经在监听，不需要重新启动音频捕获
        if self.is_listening:
            logger.debug("已经在监听音频，继续当前会话")
            return True

        if not self.is_connected:
            logger.error("未连接到服务器，无法激活音频监听")
            self._show_notification_if_enabled(
                title="NexTalk无法激活监听",
                message="未连接到服务器，请确保服务器正在运行",
                urgency="normal",
            )
            return False

        # 启动语音识别过程
        try:
            # 重置所有相关状态
            self._waiting_for_final_result = False
            self._stop_signal_sent = False
            self._waiting_for_server_ready = True
            self._server_ready_event.clear()

            # 取消任何可能存在的超时任务
            if hasattr(self, "_stop_timeout_task") and not self._stop_timeout_task.done():
                logger.debug("取消现有的超时任务")
                self._stop_timeout_task.cancel()

            # 锁定状态为LISTENING，阻止任何尝试将其更改为IDLE的操作
            self._listening_state_locked = True
            logger.debug("状态已锁定为LISTENING")

            # 先标记状态为正在监听，使UI立即响应
            logger.debug("立即更新状态为正在监听...")
            self.is_listening = True
            self._update_state(STATUS_LISTENING)

            # 启动状态同步任务
            if self.loop and self.loop.is_running():
                # 先取消已有的任务（如果存在）
                if self._state_sync_task and not self._state_sync_task.done():
                    self._state_sync_task.cancel()

                # 创建新的状态同步任务
                self._state_sync_task = asyncio.run_coroutine_threadsafe(
                    self._sync_listening_state(), self.loop
                )
                logger.debug("状态同步任务已启动")

                # 创建握手任务
                handshake_task = asyncio.run_coroutine_threadsafe(
                    self._perform_recognition_handshake(), self.loop
                )

                # 添加握手完成回调
                def handshake_callback(fut):
                    try:
                        success = fut.result()
                        if success:
                            logger.debug("握手成功，音频监听已激活")
                        else:
                            logger.error("握手失败，重置状态")
                            # 恢复状态
                            self.is_listening = False
                            self._listening_state_locked = False
                            self._update_state(STATUS_IDLE)
                    except Exception as e:
                        logger.error(f"握手过程出错: {str(e)}")
                        # 出现错误时重置状态
                        self.is_listening = False
                        self._listening_state_locked = False
                        self._update_state(STATUS_ERROR)

                handshake_task.add_done_callback(handshake_callback)
            else:
                logger.error("事件循环未运行，无法启动识别")
                # 恢复状态
                self.is_listening = False
                self._listening_state_locked = False
                self._update_state(STATUS_IDLE)
                return False

            logger.debug("音频监听激活流程已启动")
            return True
        except Exception as e:
            logger.error(f"激活音频监听时出错: {str(e)}")
            # 确保在出错时清理资源
            self.is_listening = False
            self._listening_state_locked = False
            self._update_state(STATUS_ERROR)
            return False

    async def _perform_recognition_handshake(self) -> bool:
        """
        执行识别握手流程：发送开始命令，等待服务器就绪，然后启动音频捕获。
        
        Returns:
            bool: 握手是否成功
        """
        logger.info("🤝 ===== 开始执行识别握手流程 =====")
        handshake_start_time = time.time()
        
        try:
            # 1. 发送开始识别命令
            logger.info("📤 步骤1: 发送开始识别命令给服务器...")
            cmd_send_time = time.time()
            start_result = await self.websocket_client.start_recognition()
            cmd_send_duration = (time.time() - cmd_send_time) * 1000
            
            if not start_result:
                logger.error("❌ 发送开始识别命令失败")
                return False
            
            logger.info(f"✅ 开始命令发送成功，耗时: {cmd_send_duration:.1f}ms")
            
            # 2. 等待服务器就绪确认，设置超时
            logger.info("⏳ 步骤2: 等待服务器就绪确认...")
            wait_start_time = time.time()
            
            try:
                await asyncio.wait_for(self._server_ready_event.wait(), timeout=10.0)
                wait_duration = (time.time() - wait_start_time) * 1000
                logger.info(f"✅ 收到服务器就绪确认，等待耗时: {wait_duration:.1f}ms")
            except asyncio.TimeoutError:
                wait_duration = (time.time() - wait_start_time) * 1000
                logger.error(f"❌ 等待服务器就绪超时（10秒），等待时间: {wait_duration:.1f}ms")
                return False
            
            # 3. 服务器就绪后，启动音频捕获
            logger.info("🎤 步骤3: 服务器已就绪，正在启动音频捕获...")
            capture_start_time = time.time()
            
            capture_started = self.audio_capturer.start_stream(self._handle_audio_chunk)
            capture_duration = (time.time() - capture_start_time) * 1000
            
            if not capture_started:
                logger.error("❌ 无法启动音频捕获")
                return False
            
            total_handshake_duration = (time.time() - handshake_start_time) * 1000
            logger.info(f"✅ 音频捕获已启动，耗时: {capture_duration:.1f}ms")
            logger.info(f"🎉 握手完成! 总耗时: {total_handshake_duration:.1f}ms")
            
            # 显示已激活通知
            self._show_notification_if_enabled(
                title="NexTalk已激活", message="正在监听", urgency="normal"
            )
            
            return True
            
        except Exception as e:
            total_duration = (time.time() - handshake_start_time) * 1000
            logger.error(f"❌ 执行识别握手时出错: {str(e)}, 总耗时: {total_duration:.1f}ms")
            return False
        finally:
            # 重置握手状态
            self._waiting_for_server_ready = False

    async def _deactivate_listening(self) -> None:
        """
        停用音频监听。

        当热键释放时发送停止说话信号，但保持音频捕获直到收到最终结果。
        """
        logger.debug("正在处理音频监听停用请求...")

        if not self.is_listening:
            logger.warning("未在监听音频，忽略停用请求")
            return

        # 检查是否应该立即停止监听
        # 情况1: 通过菜单或API显式停止 (force=True)
        # 情况2: 热键释放 (简化处理，直接处理热键释放)
        force_stop = getattr(self, "_force_stop_listening", False)

        # 如果是强制停止，直接完全停止
        if force_stop:
            logger.debug("强制停止监听，立即停止音频捕获")
            await self._complete_stop_listening()
            # 重置强制停止标志
            self._force_stop_listening = False
            return

        # 检查是否已经在等待最终结果 - 如果是，直接返回，防止重复处理
        if getattr(self, "_waiting_for_final_result", False):
            logger.debug("已经在等待最终结果，跳过重复处理")
            return

        # 设置等待最终结果标志
        self._waiting_for_final_result = True

        # 使用超时机制确保即使没收到最终结果也会停止
        timeout_seconds = 3.0
        logger.debug(f"设置{timeout_seconds}秒超时，确保即使没有收到最终结果也会停止")

        # 创建一个定时任务，在超时后强制停止音频捕获
        if hasattr(self, "_stop_timeout_task") and not self._stop_timeout_task.done():
            logger.debug("取消现有的超时任务")
            self._stop_timeout_task.cancel()

        # 创建新的超时任务
        self._stop_timeout_task = asyncio.create_task(self._delayed_stop_listening(timeout_seconds))

        # 设置一个状态变量，标记发送信号的结果
        self._stop_signal_sent = False

        try:
            # 直接异步发送停止说话信号
            logger.debug("发送停止说话信号并等待最终结果")
            result = await self.websocket_client.send_stop_speaking_signal()

            if result:
                logger.debug("已成功发送停止说话信号，等待服务器返回最终结果")
                self._stop_signal_sent = True
            else:
                logger.error("发送停止说话信号失败，立即停止音频捕获")
                await self._complete_stop_listening()
        except Exception as e:
            logger.error(f"发送停止说话信号时出错: {str(e)}")
            await self._complete_stop_listening()

    async def _delayed_stop_listening(self, timeout_seconds: float):
        """
        延迟停止音频捕获的辅助方法。

        在等待最终结果的情况下，如果超过指定时间未收到结果，则强制停止。

        Args:
            timeout_seconds: 等待的超时时间(秒)
        """
        try:
            logger.debug(f"延迟停止任务开始，将在{timeout_seconds}秒后自动停止")
            # 使用asyncio.sleep而不是time.sleep，避免阻塞事件循环
            await asyncio.sleep(timeout_seconds)

            # 检查是否仍在等待最终结果
            if getattr(self, "_waiting_for_final_result", False):
                logger.warning(f"等待最终结果超时({timeout_seconds}秒)，强制停止音频捕获")
                # 检查是否发送了停止信号但没有收到最终结果
                stop_signal_sent = getattr(self, "_stop_signal_sent", False)
                if stop_signal_sent:
                    logger.warning("已发送停止信号但未收到最终结果，可能服务器未响应")
                else:
                    logger.warning("未成功发送停止信号或尚未收到响应")

                # 无论如何，超时后一定要停止
                await self._complete_stop_listening()
            else:
                logger.debug("定时任务完成，但等待标志已被重置，不需要额外处理")
        except asyncio.CancelledError:
            # 任务被取消(可能是因为已经收到了最终结果)
            logger.debug("延迟停止任务被取消")
        except Exception as e:
            logger.error(f"延迟停止任务出错: {str(e)}")
            # 发生错误时，确保停止音频捕获
            await self._complete_stop_listening()

    async def _complete_stop_listening(self):
        """
        完全停止音频监听和识别。

        停止音频捕获、清理状态并更新UI。
        """
        logger.debug("正在完全停止音频监听...")

        # 重置等待最终结果标志
        self._waiting_for_final_result = False
        self._stop_signal_sent = False

        # 取消超时任务（如果存在）
        try:
            if hasattr(self, "_stop_timeout_task") and not self._stop_timeout_task.done():
                logger.debug("取消已有的停止超时任务")
                self._stop_timeout_task.cancel()
        except Exception as e:
            logger.error(f"取消超时任务时出错: {str(e)}")

        # 取消状态同步任务
        try:
            if self._state_sync_task and not self._state_sync_task.done():
                logger.debug("取消状态同步任务")
                self._state_sync_task.cancel()
        except Exception as e:
            logger.error(f"取消状态同步任务时出错: {str(e)}")

        # 停止音频捕获 - 添加重试逻辑
        max_retries = 3
        retry_count = 0
        stop_success = False

        while retry_count < max_retries and not stop_success:
            try:
                # 重置状态标志，确保我们在重新尝试时有正确的状态
                if retry_count > 0:
                    logger.debug(f"重试停止音频捕获 (尝试 {retry_count + 1}/{max_retries})")

                # 检查捕获器是否正在捕获
                if self.audio_capturer.is_capturing():
                    self.audio_capturer.stop_stream()
                    logger.debug("音频捕获器已停止")
                    stop_success = True
                else:
                    logger.warning("音频捕获器已经不在捕获状态，不需要停止")
                    stop_success = True
            except Exception as e:
                retry_count += 1
                logger.error(f"停止音频捕获时出错(尝试 {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(0.2)  # 延长等待时间，给系统更多恢复时间

        if not stop_success:
            logger.error("无法停止音频捕获器，达到最大重试次数")

        # 停止识别
        try:
            await self.websocket_client.stop_recognition()
        except Exception as e:
            logger.error(f"停止识别时出错: {str(e)}")

        # 解除状态锁定，必须在更新状态前设置
        logger.debug("解除状态锁定")
        self._listening_state_locked = False

        # 更新状态 - 确保即使出现异常也会更新状态
        logger.debug("更新标志和状态为IDLE")
        self.is_listening = False
        self._update_state(STATUS_IDLE)

        # 强制验证状态正确设置为IDLE
        if self.current_state != STATUS_IDLE:
            logger.warning(f"状态未正确设置为IDLE，当前为{self.current_state}，强制设置")
            with self._state_lock:
                self.current_state = STATUS_IDLE
                self.is_listening = False
            self._update_ui_state(STATUS_IDLE)

        # 显示通知
        try:
            self._show_notification_if_enabled(
                title="NexTalk已停用", message="不再监听", urgency="low"
            )
        except Exception as e:
            logger.error(f"发送监听停用通知时出现异常: {str(e)}")

    def _handle_audio_chunk(self, data: bytes):
        """
        处理音频数据块。

        将捕获的音频数据发送到服务器进行处理。

        Args:
            data: 从音频捕获器接收的音频数据块
        """
        if not self.is_connected or not self.is_listening:
            return

        # 记录收到的音频数据信息
        try:
            # 初始化音频块计数器和时间戳
            if not hasattr(self, "_audio_chunk_counter"):
                self._audio_chunk_counter = 0
                self._first_audio_time = time.time()
                logger.info(f"🎵 首个音频块接收，时间戳: {self._first_audio_time:.3f}")
                
            self._audio_chunk_counter += 1
            current_time = time.time()

            # 检查音频数据质量
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            non_zero_ratio = np.count_nonzero(audio_int16) / len(audio_int16) if len(audio_int16) > 0 else 0
            max_amplitude = np.max(np.abs(audio_int16)) if len(audio_int16) > 0 else 0

            # 前5个音频块总是记录详细信息
            if self._audio_chunk_counter <= 5:
                elapsed_since_first = (current_time - self._first_audio_time) * 1000
                logger.info(
                    f"🎤 音频块 #{self._audio_chunk_counter}: "
                    f"时间戳={current_time:.3f}, "
                    f"距首块={elapsed_since_first:.1f}ms, "
                    f"大小={len(data)}字节, "
                    f"非零比例={non_zero_ratio:.4f}, "
                    f"最大振幅={max_amplitude}"
                )
            elif self._audio_chunk_counter % 10 == 0:
                # 后续每10个数据块记录一次
                elapsed_since_first = (current_time - self._first_audio_time) * 1000
                logger.debug(
                    f"🎤 音频块 #{self._audio_chunk_counter}: "
                    f"距首块={elapsed_since_first:.1f}ms, "
                    f"大小={len(data)}字节, "
                    f"非零比例={non_zero_ratio:.4f}, "
                    f"最大振幅={max_amplitude}"
                )
        except Exception as e:
            logger.warning(f"音频数据分析失败: {str(e)}")

        # 检查数据是否为空
        if not data or len(data) == 0:
            logger.warning("收到空的音频数据块，跳过发送")
            return

        try:
            # 创建异步任务发送音频数据
            send_start_time = time.time()
            send_task = asyncio.run_coroutine_threadsafe(
                self.websocket_client.send_audio(data), self.loop
            )

            # 前5个音频块记录发送时间
            if self._audio_chunk_counter <= 5:
                logger.info(f"📤 音频块 #{self._audio_chunk_counter} 发送任务已创建，时间戳: {send_start_time:.3f}")

            # 每10个数据块检查一次发送结果
            if self._audio_chunk_counter % 10 == 0:
                try:
                    # 等待发送完成并获取结果(最多等待0.1秒)
                    result = send_task.result(timeout=0.1)
                    send_duration = (time.time() - send_start_time) * 1000
                    logger.debug(f"📤 音频数据发送结果: {'成功' if result else '失败'}, 耗时: {send_duration:.1f}ms")
                except asyncio.TimeoutError:
                    logger.debug("获取音频发送结果超时，发送可能仍在进行")
                except Exception as e:
                    logger.debug(f"获取音频发送结果时出错: {str(e)}")
        except Exception as e:
            logger.error(f"创建音频发送任务时出错: {str(e)}")

    def _handle_server_message(self, message):
        """
        处理从服务器接收到的消息。

        解析消息并分发到对应的处理函数。

        Args:
            message: 服务器发送的消息
        """
        if not message:
            logger.warning("收到空消息")
            return

        try:
            if isinstance(message, str):
                message_str = message
            else:
                # 假设是对象，尝试转换为字符串
                message_str = str(message)

            logger.debug(f"收到服务器消息: {message_str[:100]}")

            # 检查消息是否有type字段
            if hasattr(message, "type"):
                message_type = message.type
                logger.debug(f"处理类型为'{message_type}'的消息")

                if message_type == "transcription" and hasattr(message, "text"):
                    # 处理转录文本
                    text = message.text
                    # 检查是否有is_final字段
                    is_final = getattr(message, "is_final", False)
                    # 获取识别模式
                    mode = getattr(message, "mode", "online")

                    # 添加相关日志
                    if is_final:
                        logger.debug(f"接收到最终转录结果: '{text}', 模式: {mode}")
                    else:
                        logger.debug(f"接收到中间转录结果: '{text}', 模式: {mode}")

                    # 将转录结果传递给专门的处理函数
                    self._handle_transcription(text, is_final, mode)

                elif message_type == "error" and hasattr(message, "message"):
                    # 处理错误消息
                    error_message = message.message
                    logger.error(f"接收到错误消息: {error_message}")
                    self._handle_error(error_message)

                elif message_type == "status" and hasattr(message, "state"):
                    # 处理状态更新
                    logger.debug(f"处理状态更新: type='{message_type}' state='{message.state}'")
                    # 将整个消息对象传递给状态处理函数
                    self._handle_status_update(message)

                else:
                    logger.warning(f"收到未知类型或不完整的消息: {message_str[:100]}")
            else:
                logger.warning(f"消息缺少类型字段: {message_str[:100]}")
        except Exception as e:
            logger.error(f"处理服务器消息时出错: {str(e)}")

    def _handle_transcription(self, text: str, is_final: bool = False, mode: str = "online"):
        """
        处理转录结果。

        根据转录结果进行相应的处理，包括文本注入和状态更新。

        Args:
            text: 转录文本
            is_final: 是否为最终结果
            mode: 转录模式(online, offline, 2pass-online, 2pass-offline)
        """
        logger.debug(f"处理类型为'transcription'的消息, 模式={mode}")

        # 检查转录文本是否有效
        if not text or len(text.strip()) == 0:
            logger.debug(f"收到无效的转录文本: '{text}'")
            return

        # 记录转录结果日志
        if is_final:
            logger.debug(f"接收到转录结果: '{text}', is_final={is_final}, mode={mode}")
        else:
            logger.debug(f"接收到转录结果: '{text}', is_final={is_final}, mode={mode}")

        # 确保文本缓存初始化
        if not hasattr(self, "_text_cache"):
            logger.debug("初始化文本缓存")
            self._text_cache = {
                "online": "",
                "offline": "",
                "last_injected": "",  # 记录最后注入的文本，避免重复注入
            }

        # 根据不同模式处理文本缓存
        if "2pass" in mode:
            logger.debug(f"使用2pass模式处理文本: {mode}")

            if mode == "2pass-online":
                # 保存在线结果，但不直接注入，只在2pass模式下缓存
                self._text_cache["online"] = text
                logger.debug(f"缓存在线结果: '{text}'")

                # 合并在线和离线结果用于显示
                combined_text = self._text_cache["offline"] + self._text_cache["online"]
                logger.debug(f"合并离线和在线结果: '{combined_text}'")

                # 显示在UI中
                if get_client_bool_config("show_text", False):
                    try:
                        show_text(combined_text, is_final)
                    except Exception as e:
                        logger.error(f"显示文本窗口时出错: {str(e)}")

                # 在线模式下不直接注入文本，只在最终离线结果出来时注入
                return

            elif mode == "2pass-offline":
                # 离线模式下，使用新结果替换而不是累加，避免重复问题
                logger.debug(
                    f"接收到离线结果: '{text}'，替换之前的离线结果: '{self._text_cache['offline']}'"
                )
                self._text_cache["offline"] = text
                # 在线缓存清空
                self._text_cache["online"] = ""

                # 最终文本是离线结果
                text_to_inject = self._text_cache["offline"]
                logger.debug(f"使用离线结果作为最终注入文本: '{text_to_inject}'")
        else:
            # 普通模式
            logger.debug(f"使用{mode}模式处理文本")
            text_to_inject = text

        # 检查是否重复注入相同的文本
        if text_to_inject == self._text_cache.get("last_injected", "") and mode != "2pass-offline":
            logger.debug(f"跳过重复文本注入: '{text_to_inject}'")
            return

        # 记录本次注入的文本
        self._text_cache["last_injected"] = text_to_inject

        # 文本注入功能
        if self.injector and text_to_inject:
            logger.info(f"正在注入文本: '{text_to_inject}', 模式: {mode}")
            success = self.injector.inject_text(text_to_inject)
            if success:
                logger.debug("文本注入成功")
            else:
                logger.error("文本注入失败")
                # 如果注入失败且已配置，则显示文本窗口
                if get_client_bool_config("show_text_on_error", False):
                    try:
                        show_text(text_to_inject, is_final)
                    except Exception as e:
                        logger.error(f"显示文本窗口时出错: {str(e)}")

        # 显示文本窗口（如果已配置）
        try:
            if get_client_bool_config("show_text", False):
                # 这里我们使用一个简单的独立窗口显示文本
                show_text(text_to_inject, is_final)
        except Exception as e:
            logger.error(f"显示文本窗口时出错: {str(e)}")

        # 处理等待最终结果的情况
        waiting_for_final = getattr(self, "_waiting_for_final_result", False)
        stop_signal_sent = getattr(self, "_stop_signal_sent", False)

        # 记录当前状态详情，帮助调试
        if waiting_for_final:
            logger.debug(
                f"等待最终结果: {waiting_for_final}, 已发送停止信号: {stop_signal_sent}, 当前结果是最终结果: {is_final}"
            )

        if waiting_for_final and is_final:
            logger.debug("收到等待中的最终结果，准备停止音频捕获")

            # 取消超时任务（如果存在）
            try:
                if hasattr(self, "_stop_timeout_task") and not self._stop_timeout_task.done():
                    logger.debug("取消停止超时任务")
                    self._stop_timeout_task.cancel()
            except Exception as e:
                logger.error(f"取消超时任务时出错: {str(e)}")

            # 使用asyncio.run_coroutine_threadsafe来正确运行异步方法
            try:
                # 确保只创建一次停止任务
                if not hasattr(self, "_complete_stop_task") or self._complete_stop_task.done():
                    logger.debug("创建完全停止音频捕获任务")
                    self._complete_stop_task = asyncio.run_coroutine_threadsafe(
                        self._complete_stop_listening(), self.loop
                    )

                    # 添加完成回调以处理可能的异常
                    def callback(fut):
                        try:
                            fut.result()  # 获取结果，如果有异常会抛出
                            logger.debug("停止音频捕获任务完成")
                        except Exception as e:
                            logger.error(f"停止音频捕获时出错: {str(e)}")

                    self._complete_stop_task.add_done_callback(callback)
                else:
                    logger.debug("停止任务已经在进行中，不再创建新任务")
            except Exception as e:
                logger.error(f"创建停止任务时出错: {str(e)}")
                # 出错时尝试直接停止，确保不会卡在监听状态
                try:
                    self.is_listening = False
                    self._update_state(STATUS_IDLE)
                except Exception as stop_err:
                    logger.error(f"紧急停止失败: {stop_err}")

    def _handle_error(self, error_message: str):
        """
        处理从服务器接收到的错误消息。

        更新UI状态并显示错误通知。

        Args:
            error_message: 错误消息
        """
        logger.error(f"处理错误消息: {error_message}")

        # 更新状态
        self._update_state(STATUS_ERROR)

        # 显示错误通知
        try:
            self._show_notification_if_enabled(
                title="NexTalk错误", message=error_message, urgency="critical"
            )
        except Exception as e:
            logger.error(f"发送错误通知时出现异常: {e}")

        # 短暂延迟后恢复状态
        try:
            # 延迟5秒后恢复状态
            threading.Timer(
                5.0,
                self._delayed_state_restore,
                args=([STATUS_CONNECTED if self.is_connected else STATUS_DISCONNECTED]),
            ).start()
        except Exception as e:
            logger.error(f"创建延时任务时出错: {e}")

    def _delayed_state_restore(self, state: str):
        """
        延迟恢复状态。

        用于错误状态显示一段时间后恢复正常状态。

        Args:
            state: 要恢复的状态
        """
        if self.current_state == STATUS_ERROR:
            logger.debug(f"延迟恢复状态: {state}")
            self._update_state(state)

    def _handle_status_update(self, status: str):
        """
        处理状态更新消息。

        更新内部状态和UI显示。

        Args:
            status: 状态字符串或StatusUpdate对象
        """
        logger.debug(f"处理状态更新: {status}")

        # 检查status是否为StatusUpdate对象
        if isinstance(status, StatusUpdate):
            # 从StatusUpdate对象中提取state字段
            status = status.state
            logger.debug(f"从StatusUpdate提取状态: {status}")

        # 空状态处理 - 如果收到空状态，则跳过处理
        if not status:
            logger.warning("收到空状态消息，忽略此状态更新")
            return

        # 检查状态锁定 - 如果当前状态锁定为LISTENING，则忽略IDLE状态更新
        if hasattr(self, "_listening_state_locked") and self._listening_state_locked:
            if status == STATUS_IDLE:
                logger.debug("状态锁定为LISTENING，忽略来自服务器的IDLE状态更新")
                return

        # 更新对应的状态标志
        if status == STATUS_CONNECTED:
            self.is_connected = True
        elif status == STATUS_DISCONNECTED:
            self.is_connected = False
            # 断开连接时解除状态锁定
            self._listening_state_locked = False
        elif status == STATUS_READY:
            # 服务器就绪状态 - 触发ready事件
            ready_time = time.time()
            logger.info(f"🟢 收到服务器就绪状态，时间戳: {ready_time:.3f}")
            if hasattr(self, '_server_ready_event') and self._server_ready_event:
                logger.info("🚨 触发ready事件，唤醒等待的握手流程")
                self._server_ready_event.set()
            else:
                logger.warning("⚠️ ready事件对象不存在，无法触发")
        elif status == STATUS_LISTENING:
            self.is_listening = True
            # 设置为LISTENING状态时自动锁定状态
            self._listening_state_locked = True
        elif status == STATUS_IDLE:
            # 如果状态锁定，则不更新listening标志
            if not (hasattr(self, "_listening_state_locked") and self._listening_state_locked):
                self.is_listening = False
        elif status == STATUS_PROCESSING:
            self.is_processing = True
            # 处理状态不解除listening锁定
        elif status == STATUS_ERROR:
            # 错误状态解除锁定
            self._listening_state_locked = False

        # 更新状态
        self._update_state(status)

    def _handle_disconnect(self):
        """
        处理WebSocket连接断开。

        更新状态和UI显示。
        """
        logger.info("处理WebSocket连接断开")

        # 更新连接状态
        self.is_connected = False

        # 如果正在监听，则停止音频捕获
        if self.is_listening:
            try:
                logger.debug("正在停止音频捕获...")
                self.audio_capturer.stop_stream()
                self.is_listening = False
            except Exception as e:
                logger.error(f"停止音频捕获时出错: {str(e)}")

        # 更新状态
        self._update_state(STATUS_DISCONNECTED)

        # 显示通知
        try:
            self._show_notification_if_enabled(
                title="NexTalk连接断开", message="与服务器的连接已断开", urgency="normal"
            )
        except Exception as e:
            logger.error(f"发送连接断开通知时出现异常: {e}")

    def _update_state(self, new_state: str):
        """
        更新客户端状态。

        线程安全地更新内部状态并更新UI。

        Args:
            new_state: 新状态
        """
        with self._state_lock:
            # 空状态处理 - 如果收到空状态，改为IDLE状态
            if not new_state:
                logger.warning("尝试设置空状态，改为设置为IDLE状态")
                new_state = STATUS_IDLE

            # 检查状态锁定
            if hasattr(self, "_listening_state_locked") and self._listening_state_locked:
                # 如果状态被锁定，且尝试设置为任何非LISTENING的状态（除了ERROR），则拒绝
                if (
                    self.current_state == STATUS_LISTENING
                    and new_state != STATUS_LISTENING
                    and new_state != STATUS_ERROR
                ):
                    logger.debug(f"状态锁定为LISTENING，忽略切换到{new_state}的请求")
                    return

            # 如果状态没有变化，不执行操作
            if self.current_state == new_state:
                logger.debug(f"状态未变化，保持为 {new_state}")
                return

            logger.debug(f"状态更新: {self.current_state} -> {new_state}")
            old_state = self.current_state
            self.current_state = new_state

            # 根据状态更新其他内部标志
            if new_state == STATUS_LISTENING:
                self.is_listening = True
                logger.debug("已设置监听标志为True")
            elif new_state == STATUS_IDLE:
                # 如果状态锁定，则不更新listening标志
                if not (hasattr(self, "_listening_state_locked") and self._listening_state_locked):
                    self.is_listening = False
                    logger.debug("已设置监听标志为False")
                else:
                    logger.debug("状态锁定，保持监听标志为True")
            elif new_state == STATUS_CONNECTED:
                self.is_connected = True
                logger.debug("已设置连接标志为True")
            elif new_state == STATUS_DISCONNECTED:
                self.is_connected = False
                self.is_listening = False
                self._listening_state_locked = False
                logger.debug("已设置连接标志为False，监听标志为False")
            elif new_state == STATUS_ERROR:
                # 错误状态可以解除状态锁定
                self._listening_state_locked = False
                logger.debug("错误状态，已解除状态锁定")

        # 更新UI状态（在锁外执行，避免死锁）
        self._update_ui_state(new_state)

        # 记录更新完成日志
        logger.debug(f"状态更新完成: {old_state} -> {new_state}")

    def _update_ui_state(self, new_state: str):
        """
        更新UI状态。

        根据当前状态更新系统托盘图标等UI元素。

        Args:
            new_state: 新状态
        """
        if self.tray_icon:
            try:
                logger.debug(f"开始更新托盘图标状态为: {new_state}")
                self.tray_icon.update_state(new_state)
                logger.debug(f"托盘图标状态已更新为: {new_state}")
            except Exception as e:
                logger.error(f"更新托盘图标状态时出错: {e}")
        else:
            logger.warning("托盘图标未初始化，无法更新状态")

    def toggle_listening(self):
        """
        切换音频监听状态。

        如果当前正在监听，则停止监听；否则开始监听。
        """
        if not self.is_connected:
            logger.warning("未连接到服务器，无法切换监听状态")
            return

        if self.is_listening:
            logger.debug("切换：强制停止监听")

            # 手动切换时，强制停止监听
            self._force_stop_listening = True

            # 创建任务来停止监听
            task = asyncio.run_coroutine_threadsafe(self._deactivate_listening(), self.loop)

            # 添加完成回调
            def callback(fut):
                try:
                    fut.result()  # 获取结果，可能会引发异常
                except Exception as e:
                    logger.error(f"停止监听时出错: {str(e)}")

            task.add_done_callback(callback)
        else:
            logger.debug("切换：开始监听")
            self._activate_listening()

    def _handle_quit_request(self):
        """
        处理退出请求。

        停止客户端并退出应用程序。
        """
        logger.info("接收到退出请求")

        # 创建任务来停止客户端
        if self.loop:
            task = asyncio.run_coroutine_threadsafe(self.stop(), self.loop)

            # 添加完成回调
            def callback(fut):
                try:
                    fut.result()  # 获取结果，可能会引发异常
                    logger.debug("客户端已停止，准备退出")

                    # 发送关闭事件
                    self._shutdown_event.set()
                except Exception as e:
                    logger.error(f"停止客户端时出错: {str(e)}")

                    # 尽管出错，仍然发送关闭事件
                    self._shutdown_event.set()

            task.add_done_callback(callback)

    async def _sync_listening_state(self):
        """
        定期同步状态，确保当状态锁定为LISTENING时，UI状态保持为LISTENING。

        这个方法会每隔一段时间检查一次，如果发现状态不一致，会进行修复。
        例如，当热键激活后但托盘图标显示为idle时，会将状态强制设回listening。
        """
        try:
            logger.debug("状态同步任务开始运行")

            # 继续运行直到状态解锁
            while self._listening_state_locked:
                # 如果状态锁定为LISTENING，但当前状态不是LISTENING，则强制修复
                if self._listening_state_locked and self.current_state != STATUS_LISTENING:
                    logger.debug(
                        f"检测到状态不一致：当前状态为{self.current_state}，但状态锁定为LISTENING，正在修复"
                    )
                    with self._state_lock:
                        self.current_state = STATUS_LISTENING
                        self.is_listening = True
                    self._update_ui_state(STATUS_LISTENING)
                    logger.debug("状态已修复为LISTENING")

                # 休眠一段时间后再次检查
                await asyncio.sleep(1.0)

            logger.debug("状态锁定已解除，状态同步任务结束")
        except asyncio.CancelledError:
            logger.debug("状态同步任务被取消")
        except Exception as e:
            logger.error(f"状态同步任务出错: {str(e)}")

    def _show_notification_if_enabled(self, title: str, message: str, urgency: str = "normal"):
        """
        根据配置决定是否显示通知。

        只有当配置项show_notifications为true时才会显示通知。

        Args:
            title: 通知标题
            message: 通知内容
            urgency: 紧急程度，可以是'low', 'normal', 或 'critical'
        """
        # 检查是否启用了通知
        if get_client_bool_config("show_notifications", True):
            try:
                show_notification(title, message, urgency)
            except Exception as e:
                logger.error(f"发送通知时出现异常: {e}")
        else:
            logger.debug(f"通知已禁用，跳过显示通知: {title} - {message}")
