"""
WebSocket处理器模块

处理WebSocket连接，接收音频数据并使用FunASR进行语音识别。
简化实现，专注于FunASR模型的支持。
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from nextalk_shared.constants import STATUS_LISTENING, STATUS_READY
from nextalk_shared.data_models import FunASRConfig

from .config import get_config
from .funasr_model import FunASRModel

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.websocket_handler")


class WebSocketHandler:
    """WebSocket处理器类，处理FunASR语音识别请求"""

    def __init__(self, websocket: WebSocket, model: FunASRModel):
        """
        初始化WebSocket处理器

        Args:
            websocket: WebSocket连接对象
            model: FunASR模型实例
        """
        self.websocket = websocket
        self.model = model
        # 确保模型已初始化，但不要在这里尝试重新初始化
        if not hasattr(self.model, "_initialized") or not self.model._initialized:
            logger.warning("WebSocket处理器接收到未初始化的模型实例，这可能导致问题")

        self.connection_closed = False
        self.config = get_config()

        # 创建VAD状态字典，与官方实现一致
        self.vad_status_dict = {
            "cache": {},
            "is_final": False,
        }

        # 任务控制
        self.processing_task = None
        self.stop_processing = asyncio.Event()
        self.processing_active = True

        # FunASR相关配置
        self.funasr_config = FunASRConfig()
        # 设置默认的chunk_interval为10，与官方示例一致
        self.funasr_config.chunk_interval = 10
        self.funasr_config.chunk_size = [5, 10, 5]  # 默认分块大小，与官方示例一致
        self.funasr_config.mode = "2pass"  # 默认使用2pass模式

        # 从全局配置中获取高级参数
        if (
            hasattr(self.config, "encoder_chunk_look_back")
            and self.config.encoder_chunk_look_back is not None
        ):
            self.funasr_config.encoder_chunk_look_back = self.config.encoder_chunk_look_back
            logger.debug(
                f"从配置中加载encoder_chunk_look_back: {self.funasr_config.encoder_chunk_look_back}"
            )

        if (
            hasattr(self.config, "decoder_chunk_look_back")
            and self.config.decoder_chunk_look_back is not None
        ):
            self.funasr_config.decoder_chunk_look_back = self.config.decoder_chunk_look_back
            logger.debug(
                f"从配置中加载decoder_chunk_look_back: {self.funasr_config.decoder_chunk_look_back}"
            )

        # 音频帧缓存 - 与官方示例一致的命名
        self.frames = []  # 所有收到的帧
        self.frames_asr = []  # 用于离线ASR的帧
        self.frames_asr_online = []  # 用于在线ASR的帧

        # VAD状态 - 按照官方funasr_wss_server.py逻辑
        self.speech_start = False  # 表示检测到语音开始，与官方命名一致
        self.speech_end_i = -1  # 语音结束时间戳，与官方命名一致
        self.vad_pre_idx = 0  # 当前VAD处理的位置索引，与官方示例一致
        self.is_speaking = True  # 客户端手动控制的说话状态

        # 会话ID和预热状态
        self.session_id = int(time.time())
        self.wav_name = f"session_{self.session_id}"
        self.funasr_config.wav_name = self.wav_name

        # 首次语音标志，用于判断是否需要额外预热
        self.first_speech_chunk = True

        logger.debug(
            f"初始化WebSocket处理器，会话ID: {self.session_id}, 识别模式: {self.funasr_config.mode}"
        )

    async def accept(self) -> None:
        """接受WebSocket连接"""
        try:
            await self.websocket.accept()
            logger.debug("WebSocket连接已接受")
        except Exception as e:
            logger.error(f"接受WebSocket连接时出错: {str(e)}")
            raise

    async def send_json(self, data: Dict[str, Any]) -> None:
        """发送JSON消息"""
        if self.connection_closed:
            logger.warning("尝试向已关闭的连接发送消息")
            return

        try:
            # 确保发送格式与官方实现一致
            if "type" in data and data["type"] == "transcription":
                # 从transcription类型转换为官方的格式，但添加类型字段以适配客户端
                send_data = {
                    "type": "transcription",  # 添加type字段以适配客户端
                    "mode": data.get("mode", "unknown"),
                    "text": data.get("text", ""),
                    "wav_name": data.get("wav_name", ""),
                    "is_final": data.get("is_final", False),
                }

                # 可选添加原始文本字段
                if "original_text" in data:
                    send_data["original_text"] = data["original_text"]

                await self.websocket.send_json(send_data)
            else:
                # 确保其他类型消息也包含type字段
                if "type" not in data and "status" in data:
                    data["type"] = "status"  # 添加状态消息的type字段

                # 其他类型消息保持原样
                await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"发送JSON消息时出错: {str(e)}")
            self.connection_closed = True
            raise

    async def handle_json_message(self, message: Dict[str, Any]) -> None:
        """处理JSON消息，用于控制识别行为"""
        logger.debug(f"接收JSON控制消息: {message}")

        # 处理命令消息
        if "command" in message:
            command = message["command"]
            if command == "start":
                start_cmd_time = time.time()
                logger.info(f"🚀 收到开始识别命令，时间戳: {start_cmd_time:.3f}")

                # 确保模型已经完全初始化
                if not hasattr(self.model, "_initialized") or not self.model._initialized:
                    logger.warning("⚠️ 模型尚未初始化，等待初始化完成...")
                    init_start = time.time()
                    await self.model.initialize()
                    init_duration = (time.time() - init_start) * 1000
                    logger.info(f"⚡ 模型初始化完成，耗时: {init_duration:.1f}ms")
                else:
                    logger.info("✅ 模型已初始化，跳过初始化步骤")

                # 重置模型状态以确保清洁的开始
                reset_start = time.time()
                await self.model.reset()
                reset_duration = (time.time() - reset_start) * 1000
                logger.info(f"🔄 模型状态重置完成，耗时: {reset_duration:.1f}ms")

                # 关键优化：在发送ready状态前进行流式模型预热
                warmup_start = time.time()
                await self._warmup_streaming_model()
                warmup_duration = (time.time() - warmup_start) * 1000
                logger.info(f"🔥 流式模型预热完成，耗时: {warmup_duration:.1f}ms")

                # 发送就绪状态，告知客户端可以开始发送音频
                ready_time = time.time()
                await self.send_status(STATUS_READY)
                total_prep_duration = (ready_time - start_cmd_time) * 1000
                logger.info(f"🟢 已发送就绪信号给客户端，总准备时间: {total_prep_duration:.1f}ms")
                return
            else:
                logger.debug(f"收到未知命令: {command}")

        # 处理识别模式
        if "mode" in message:
            mode = message["mode"]
            if mode in ["2pass", "online", "offline"]:
                self.funasr_config.mode = mode
                logger.debug(f"设置识别模式为: {mode}")
            else:
                logger.warning(f"无效的识别模式: {mode}, 使用默认模式: {self.funasr_config.mode}")

        # 处理说话状态控制
        if "is_speaking" in message:
            is_speaking = message["is_speaking"]
            self.is_speaking = bool(is_speaking)
            logger.info(f"设置说话状态为: {'说话中' if self.is_speaking else '停止说话'}")

            # 如果设置为不说话，处理结束当前语音段
            if not self.is_speaking:
                # 调试：输出当前的语音状态标志
                logger.info(
                    f"📊 VAD状态: speech_start={self.speech_start}, "
                    f"speech_end_i={self.speech_end_i}"
                )
                logger.info(
                    f"📊 帧数信息: frames={len(self.frames)}帧, frames_asr={len(self.frames_asr)}帧, "
                    f"frames_asr_online={len(self.frames_asr_online)}帧"
                )

                # 新条件：只要停止说话就处理，无论是否检测到语音
                # 按照官方实现，stop命令触发speech_end处理
                logger.info("🛑 客户端停止说话，强制结束当前语音段")

                # 如果没有检测到语音开始，我们为了调试也设置它为True
                if not self.speech_start:
                    self.speech_start = True
                    logger.info("强制设置speech_start=True用于调试")

                # 核心修复：确保frames_asr包含完整的语音数据
                # 之前的问题是VAD失效导致frames_asr没有积累有效语音
                if not self.frames_asr or len(self.frames_asr) < 5:  # 如果frames_asr为空或太少
                    if len(self.frames) > 0:
                        # 关键改进：使用所有历史帧，而不仅仅是最近的frames_asr_online
                        # 过滤开头可能的静音帧
                        logger.debug("使用完整的历史帧数据替代VAD累积的frames_asr")

                        # 计算音频特征以找到有效语音起始
                        valid_frames = []
                        for frame in self.frames:
                            frame_np = np.frombuffer(frame, dtype=np.int16)
                            max_amp = np.max(np.abs(frame_np)) if len(frame_np) > 0 else 0
                            # 只保留有效声音的帧（振幅大于阈值）
                            if max_amp > 500:
                                valid_frames.append(frame)

                        if valid_frames:
                            logger.debug(f"找到 {len(valid_frames)} 个有效音频帧（振幅>500）")
                            self.frames_asr = valid_frames
                        else:
                            # 如果没有找到有效声音帧，使用所有帧
                            logger.debug("未找到有效声音帧，使用所有历史帧")
                            self.frames_asr = self.frames.copy()
                    elif len(self.frames_asr_online) > 0:
                        # 备选方案：使用在线ASR的帧
                        logger.debug("frames_asr为空，正在从frames_asr_online复制")
                        self.frames_asr = self.frames_asr_online.copy()

                await self._process_speech_end()

        # 处理热词
        if "hotwords" in message:
            self.funasr_config.hotwords = message["hotwords"]
            # 同时设置到离线和在线模型的状态字典中
            if hasattr(self.model, "status_dict_asr"):
                self.model.status_dict_asr["hotword"] = message["hotwords"]
            if hasattr(self.model, "status_dict_asr_online"):
                self.model.status_dict_asr_online["hotword"] = message["hotwords"]
            logger.debug(f"设置热词: {self.funasr_config.hotwords}")

        # 处理分块大小
        if "chunk_size" in message:
            chunk_size = message["chunk_size"]
            if isinstance(chunk_size, list):
                self.funasr_config.chunk_size = chunk_size
            elif isinstance(chunk_size, str):
                self.funasr_config.chunk_size = [int(x) for x in chunk_size.split(",")]
            logger.debug(f"设置分块大小为: {self.funasr_config.chunk_size}")

        # 处理分块间隔
        if "chunk_interval" in message:
            self.funasr_config.chunk_interval = int(message["chunk_interval"])
            logger.debug(f"设置分块间隔为: {self.funasr_config.chunk_interval}")

        # 处理音频名称
        if "wav_name" in message:
            self.funasr_config.wav_name = message["wav_name"]
            self.wav_name = message["wav_name"]
            logger.debug(f"设置音频名称为: {self.wav_name}")

        # 处理ITN设置
        if "itn" in message:
            self.funasr_config.itn = bool(message["itn"])
            logger.debug(f"设置ITN为: {self.funasr_config.itn}")

        # 返回当前设置状态
        await self.send_status(STATUS_LISTENING, {"config": self.funasr_config.model_dump()})

    async def _async_vad(self, audio_in: bytes) -> tuple[int, int]:
        """
        按照官方funasr_wss_server.py逻辑实现的VAD函数
        
        Args:
            audio_in: 音频数据
            
        Returns:
            (speech_start_i, speech_end_i): 语音开始和结束位置，-1表示未检测到
        """
        try:
            # 初始化返回值
            speech_start_i = -1
            speech_end_i = -1
            
            # 调用VAD模型，使用累积的状态字典
            # 根据官方文档：VAD使用固定的200ms chunk_size（官方默认值）
            # 不需要基于ASR chunk_size计算，VAD有自己的处理节奏
            vad_chunk_size = 200  # ms，官方FSMN-VAD默认chunk_size
            self.vad_status_dict["chunk_size"] = vad_chunk_size
            
            vad_result = await self.model.process_vad(audio_in, self.vad_status_dict)
            segments_result = vad_result.get("segments", [])
            
            logger.info(f"VAD模型返回 {len(segments_result)} 个语音段 (chunk_size={vad_chunk_size}ms)")
            
            # 按照官方逻辑：处理所有返回的语音段
            if len(segments_result) > 0:
                # 遍历所有语音段，寻找有效的起始和结束点
                for segment in segments_result:
                    if len(segment) >= 2:
                        # 检查起始点
                        if segment[0] != -1 and speech_start_i == -1:
                            speech_start_i = segment[0]
                            logger.info(f"检测到语音段起始: {speech_start_i}ms")
                        # 检查结束点  
                        if segment[1] != -1:
                            speech_end_i = segment[1]
                            logger.info(f"检测到语音段结束: {speech_end_i}ms")
                            break  # 找到结束点就停止
                        
                    logger.debug(f"处理VAD段: [{segment[0] if len(segment) > 0 else 'N/A'}, {segment[1] if len(segment) > 1 else 'N/A'}]")
            else:
                logger.debug("VAD未检测到任何语音段")
                
            # 更新VAD缓存状态
            if "cache" in vad_result:
                self.vad_status_dict["cache"] = vad_result["cache"]
                
            return speech_start_i, speech_end_i
            
        except Exception as e:
            logger.error(f"VAD处理出错: {str(e)}")
            return -1, -1

    async def _warmup_streaming_model(self) -> None:
        """
        在会话开始前预热流式识别模型，解决首次识别不准的问题

        这个方法在发送ready状态之前被调用，确保客户端开始发送音频时
        模型已经完全预热并建立了内部cache状态
        """
        try:
            logger.info("开始预热流式识别模型...")

            # 计算chunk大小
            chunk_samples = self.funasr_config.chunk_size[1] * 960  # 默认10 * 960 = 9600样本

            # 创建静音音频数据用于预热
            silent_chunk = np.zeros(chunk_samples, dtype=np.int16).tobytes()

            # 进行多轮预热，建立模型内部状态和cache
            warmup_rounds = 3  # 增加预热轮数确保充分预热
            logger.info(f"进行{warmup_rounds}轮流式模型预热，chunk大小: {chunk_samples}样本")

            for i in range(warmup_rounds):
                warmup_start = time.time()

                # 前几轮为非最终状态，最后一轮为最终状态
                is_final = i == warmup_rounds - 1

                # 调用音频处理进行预热
                await self.model.process_audio_chunk(silent_chunk, is_final)

                warmup_round_duration = (time.time() - warmup_start) * 1000
                logger.info(
                    f"预热轮{i + 1}完成，耗时: {warmup_round_duration:.1f}ms, is_final: {is_final}"
                )

            logger.info("流式识别模型预热完成，模型已准备好处理真实音频")

        except Exception as e:
            logger.warning(f"流式模型预热失败，但会话将继续: {str(e)}")
            # 预热失败不应该阻止会话继续，只是可能影响初始识别质量

    async def handle_binary_message(self, binary_data: bytes) -> None:
        """处理二进制音频数据"""
        # 检查数据有效性
        if not binary_data or len(binary_data) == 0:
            logger.warning("收到空的二进制数据")
            return

        # 初始化音频数据计数器
        if not hasattr(self, "_audio_counter"):
            self._audio_counter = 0
            self._first_audio_server_time = time.time()
            logger.info(f"🎵 服务器首次接收音频数据，时间戳: {self._first_audio_server_time:.3f}")

        self._audio_counter += 1
        current_time = time.time()

        # 将音频数据转换为numpy数组并计算基本信息
        audio_np = np.frombuffer(binary_data, dtype=np.int16)
        samples = len(audio_np)
        duration_ms = samples / 16
        non_zero = np.count_nonzero(audio_np)
        non_zero_ratio = non_zero / samples if samples > 0 else 0
        max_amp = np.max(np.abs(audio_np)) if samples > 0 else 0

        # 前5个音频块详细记录
        if self._audio_counter <= 5:
            elapsed_since_first = (current_time - self._first_audio_server_time) * 1000
            logger.info(
                f"🎤 服务器音频块 #{self._audio_counter}: "
                f"时间戳={current_time:.3f}, "
                f"距首块={elapsed_since_first:.1f}ms, "
                f"大小={len(binary_data)}字节, "
                f"样本数={samples}, 非零比例={non_zero_ratio:.4f}, "
                f"最大振幅={max_amp}"
            )
        elif max_amp > 500:
            # 只在音频数据有实质内容时详细记录
            elapsed_since_first = (current_time - self._first_audio_server_time) * 1000
            logger.debug(
                f"🎤 服务器音频块 #{self._audio_counter}: "
                f"距首块={elapsed_since_first:.1f}ms, "
                f"样本数={samples}, 非零样本={non_zero}, "
                f"非零比例={non_zero_ratio:.4f}, 最大振幅={max_amp}"
            )

        # 添加到所有帧列表，用于历史上下文  
        self.frames.append(binary_data)

        # 计算帧持续时间，用于VAD预处理（与官方实现一致）
        duration_ms = len(binary_data) // 32  # 16kHz 16bit = 32字节/毫秒
        self.vad_pre_idx += duration_ms

        # 添加到在线ASR帧列表，用于流式处理
        self.frames_asr_online.append(binary_data)

        # 按照官方funasr_wss_server.py逻辑进行VAD处理
        # 关键优化：使用累积音频而不是单个chunk进行VAD检测，提高准确性
        try:
            # 使用最近的几个音频帧进行VAD，而不是单个帧，提高检测稳定性
            recent_frames_count = min(5, len(self.frames))  # 使用最近5帧，约300-500ms数据
            recent_audio_data = b"".join(self.frames[-recent_frames_count:])
            
            # 调用VAD获取语音段信息 - 使用累积的音频数据
            speech_start_i, speech_end_i = await self._async_vad(recent_audio_data)
            
            logger.info(f"VAD检测结果: speech_start_i={speech_start_i}, speech_end_i={speech_end_i}")

            # 处理语音开始 - 按照官方逻辑
            if speech_start_i != -1 and not self.speech_start:
                self.speech_start = True
                logger.info(f"🎯 语音开始检测到，位置: {speech_start_i}ms")

                # 计算前导偏移，添加语音开始前的音频帧
                beg_bias = (self.vad_pre_idx - speech_start_i) // duration_ms
                frames_pre = self.frames[-beg_bias:] if beg_bias > 0 else []
                
                self.frames_asr = []
                self.frames_asr.extend(frames_pre)
                logger.info(f"添加了 {len(frames_pre)} 个前导帧到frames_asr")

            # 如果语音已开始，添加当前帧到离线ASR列表
            if self.speech_start:
                self.frames_asr.append(binary_data)
                logger.info(f"语音累积中: frames_asr={len(self.frames_asr)}帧")

            # 更新语音结束状态
            if speech_end_i != -1:
                self.speech_end_i = speech_end_i
                logger.debug(f"语音结束检测到，位置: {speech_end_i}ms")

            # 手动停止时强制设置结束点
            if not self.is_speaking:
                self.model.status_dict_asr_online["is_final"] = True

            # 处理在线ASR - 按照官方条件判断
            if (
                len(self.frames_asr_online) >= self.funasr_config.chunk_interval
                or self.model.status_dict_asr_online["is_final"]
            ):
                # 只在支持的模式下处理在线ASR
                if self.funasr_config.mode in ["2pass", "online"]:
                    audio_in = b"".join(self.frames_asr_online)

                    # 移除首次语音预热逻辑，因为预热已在ready状态前完成
                    if self.first_speech_chunk:
                        logger.debug("首次语音处理，预热已在会话开始时完成")
                        self.first_speech_chunk = False

                    try:
                        await self._process_online_audio(
                            audio_in, self.model.status_dict_asr_online["is_final"]
                        )
                    except Exception as e:
                        logger.error(f"在线ASR处理出错: {str(e)}")

                # 处理完后清空在线帧缓存
                self.frames_asr_online = []

            # 语音结束处理 - 按照官方逻辑只在语音段真正结束时触发离线ASR
            if (self.speech_end_i != -1 or not self.is_speaking) and self.speech_start:
                logger.debug(f"触发语音段结束处理，speech_end_i={self.speech_end_i}, is_speaking={self.is_speaking}")
                await self._process_speech_end()

        except Exception as e:
            logger.error(f"处理音频数据时出错: {str(e)}")
            logger.exception(e)

    async def _process_speech_end(self) -> None:
        """按照官方funasr_wss_server.py逻辑处理语音段结束"""
        logger.info("🔄 开始处理语音段结束逻辑")

        # 在语音段结束前，先发送最后一个在线识别的最终结果
        if self.frames_asr_online:
            logger.info("📤 发送最后的在线识别最终结果")
            audio_in = b"".join(self.frames_asr_online)
            try:
                await self._process_online_audio(audio_in, is_final=True)
            except Exception as e:
                logger.error(f"发送最终在线结果出错: {str(e)}")

        # 处理离线ASR - 按照官方逻辑，只有在语音段结束时才触发
        if (self.funasr_config.mode in ["2pass", "offline"]) and self.frames_asr:
            logger.info(f"🎯 处理离线ASR，frames_asr长度: {len(self.frames_asr)}帧")

            audio_in = b"".join(self.frames_asr)
            audio_np = np.frombuffer(audio_in, dtype=np.int16)
            duration_s = len(audio_np) / 16000

            try:
                # 调用离线音频处理
                logger.info(f"🔊 开始调用离线ASR，音频长度: {duration_s:.2f}秒")
                await self._process_offline_audio(audio_in)
            except Exception as e:
                logger.error(f"离线ASR处理出错: {str(e)}")

        # 按照官方funasr_wss_server.py逻辑重置状态
        self.frames_asr = []
        self.speech_start = False  # 重置为官方变量名
        self.speech_end_i = -1     # 重置语音结束位置
        self.frames_asr_online = []

        # 重置模型缓存 - 与官方一致
        await self.model.reset()

        # 如果是手动停止，完全重置上下文
        if not self.is_speaking:
            self.vad_pre_idx = 0
            self.frames = []
            self.vad_status_dict["cache"] = {}
            self.first_speech_chunk = True
            logger.info("🧹 手动停止：完全重置VAD状态和音频缓存")
        else:
            # 保留最近的帧作为上下文
            self.frames = self.frames[-20:] if len(self.frames) > 20 else self.frames
            logger.info(f"📝 保留最近 {len(self.frames)} 帧作为上下文")

        # 更新状态
        await self.send_status(STATUS_LISTENING)
        logger.info("✅ 语音段结束处理完成")

    async def _process_online_audio(self, audio_data: bytes, is_final: bool = False) -> None:
        """
        处理在线音频数据

        Args:
            audio_data: 原始音频数据
            is_final: 是否为最终帧
        """
        if not audio_data or len(audio_data) == 0:
            return

        # 检查基本状态 - 如果已完成语音段且是2pass模式，不要处理
        # 但如果仍在说话（is_speaking=True），则继续处理
        if self.funasr_config.mode == "2pass" and self.speech_end_i > -1 and not self.is_speaking:
            return

        start_time = time.time()

        # 将FunASR配置转换为模型可接受的格式
        self.model.status_dict_asr_online["is_final"] = is_final
        self.model.status_dict_asr_online["chunk_size"] = self.funasr_config.chunk_size

        # 确保添加 encoder_chunk_look_back 和 decoder_chunk_look_back 参数到模型状态字典
        if self.funasr_config.encoder_chunk_look_back is not None:
            self.model.status_dict_asr_online["encoder_chunk_look_back"] = (
                self.funasr_config.encoder_chunk_look_back
            )
            logger.debug(
                f"设置在线ASR encoder_chunk_look_back: {self.funasr_config.encoder_chunk_look_back}"
            )

        if self.funasr_config.decoder_chunk_look_back is not None:
            self.model.status_dict_asr_online["decoder_chunk_look_back"] = (
                self.funasr_config.decoder_chunk_look_back
            )
            logger.debug(
                f"设置在线ASR decoder_chunk_look_back: {self.funasr_config.decoder_chunk_look_back}"
            )

        # 处理音频
        result = await self.model.process_audio_chunk(audio_data, is_final)

        # 检查结果有效性
        if not result or "text" not in result:
            logger.warning("在线ASR返回无效结果")
            return

        # 日志记录
        process_time = time.time() - start_time
        logger.debug(
            f"在线ASR处理完成，耗时: {process_time:.3f}秒, 结果长度: {len(result.get('text', ''))}"
        )

        # 记录转录文本内容
        text = result.get("text", "")
        if text:
            logger.debug(f"在线ASR转录内容 [{'最终' if is_final else '临时'}]: '{text}'")

        # 准备与官方格式一致的消息
        mode = "2pass-online" if self.funasr_config.mode == "2pass" else "online"

        # 发送结果
        await self.send_json(
            {
                "type": "transcription",  # 明确指定类型
                "text": text,
                "is_final": is_final,
                "mode": mode,
                "wav_name": self.wav_name,
            }
        )

    async def _process_offline_audio(self, audio_data: bytes) -> None:
        """
        处理离线音频数据

        Args:
            audio_data: 原始音频数据
        """
        if not audio_data or len(audio_data) == 0:
            logger.warning("离线处理收到空音频数据，跳过处理")
            return

        # 记录开始时间
        start_time = time.time()

        try:
            # 处理音频 - 离线最终结果，直接传递原始音频数据
            result = await self.model.process_audio_offline(audio_data)

            # 检查结果有效性
            if not result or "text" not in result:
                logger.warning("离线ASR返回无效结果")
                return

            # 获取文本结果
            text = result.get("text", "")
            if not text:
                logger.warning("离线ASR未返回有效文本内容")
                return

            # 获取标点前的原始ASR结果（如果可用）
            original_text = result.get("original_text", "")

            # 日志记录
            process_time = time.time() - start_time
            if original_text and original_text != text:
                logger.info(
                    f"📝 离线ASR处理完成，耗时: {process_time:.3f}秒，"
                    f"标点前: '{original_text}'，标点后: '{text}'"
                )
            else:
                logger.info(f"📝 离线ASR处理完成，耗时: {process_time:.3f}秒, 结果: '{text}'")

            # 准备与官方格式一致的消息
            mode = "2pass-offline" if self.funasr_config.mode == "2pass" else "offline"

            # 准备结果数据
            response_data = {
                "type": "transcription",  # 明确指定类型
                "text": text,
                "is_final": True,  # 离线结果总是最终的
                "mode": mode,
                "wav_name": self.wav_name,
            }

            # 如果有标点前的原始ASR结果，也一并发送
            if original_text:
                response_data["original_text"] = original_text

            # 发送结果
            logger.info(f"📤 发送离线ASR结果给客户端: '{text}'")
            await self.send_json(response_data)

        except Exception as e:
            logger.error(f"处理离线音频出错: {str(e)}")
            logger.exception(e)

    async def handle_message(self, message) -> None:
        """处理传入的WebSocket消息"""
        try:
            if isinstance(message, bytes):
                await self.handle_binary_message(message)
            elif isinstance(message, str):
                try:
                    json_data = json.loads(message)
                    await self.handle_json_message(json_data)
                except json.JSONDecodeError:
                    logger.error(f"无效的JSON消息: {message}")
            else:
                logger.warning(f"未知消息类型: {type(message)}")
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            logger.exception(e)

    async def listen(self) -> None:
        """监听传入的WebSocket消息"""
        try:
            while True:
                message = await self.websocket.receive()

                if "type" in message:
                    if message["type"] == "websocket.disconnect":
                        logger.debug("客户端断开连接")
                        break
                    elif message["type"] == "websocket.receive":
                        if "bytes" in message:
                            await self.handle_message(message["bytes"])
                        elif "text" in message:
                            await self.handle_message(message["text"])
                else:
                    logger.warning(f"未知的消息格式: {message}")

        except WebSocketDisconnect:
            logger.debug("WebSocket连接断开")
        except asyncio.CancelledError:
            logger.debug("WebSocket处理任务被取消")
        except Exception as e:
            logger.error(f"WebSocket监听出错: {str(e)}")
            logger.exception(e)
        finally:
            self.connection_closed = True

            # 停止处理并等待完成
            if self.processing_task and not self.processing_task.done():
                self.stop_processing.set()
                try:
                    await asyncio.wait_for(self.processing_task, timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("等待音频处理任务完成超时")

            # 释放模型资源
            await self.model.reset()

            logger.debug("WebSocket处理完成")

    async def send_status(self, status: str, extra_data: Dict[str, Any] = None) -> None:
        """发送状态消息"""
        data = {
            "type": "status",  # 明确指定消息类型
            "status": status,
            "state": status,  # 添加state字段以与客户端兼容
            "timestamp": int(time.time()),
        }

        if extra_data:
            data.update(extra_data)

        await self.send_json(data)
