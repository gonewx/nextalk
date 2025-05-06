"""
WebSocket处理器模块

处理WebSocket连接，接收音频数据并使用FunASR进行语音识别。
简化实现，专注于FunASR模型的支持。
"""

import logging
import asyncio
import json
import time
import os
import numpy as np
import wave  # 添加wave模块用于保存音频文件
from typing import Dict, Any, Optional, List, Tuple
from fastapi import WebSocket, WebSocketDisconnect

from .funasr_model import FunASRModel
from .config import get_config
from nextalk_shared.data_models import FunASRConfig
from nextalk_shared.constants import STATUS_LISTENING, STATUS_PROCESSING, STATUS_ERROR

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
        if not hasattr(self.model, '_initialized') or not self.model._initialized:
            logger.warning("WebSocket处理器接收到未初始化的模型实例，这可能导致问题")
        
        self.connection_closed = False
        self.config = get_config()
        
        # 创建VAD状态字典，与官方实现一致
        self.vad_status_dict = {"cache": {}, "is_final": False}
        
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
        if hasattr(self.config, 'encoder_chunk_look_back') and self.config.encoder_chunk_look_back is not None:
            self.funasr_config.encoder_chunk_look_back = self.config.encoder_chunk_look_back
            logger.info(f"从配置中加载encoder_chunk_look_back: {self.funasr_config.encoder_chunk_look_back}")
        
        if hasattr(self.config, 'decoder_chunk_look_back') and self.config.decoder_chunk_look_back is not None:
            self.funasr_config.decoder_chunk_look_back = self.config.decoder_chunk_look_back
            logger.info(f"从配置中加载decoder_chunk_look_back: {self.funasr_config.decoder_chunk_look_back}")
        
        # 音频帧缓存 - 与官方示例一致的命名
        self.frames = []  # 所有收到的帧
        self.frames_asr = []  # 用于离线ASR的帧
        self.frames_asr_online = []  # 用于在线ASR的帧
        
        # VAD状态
        self.speech_start_flag = False  # 表示检测到语音开始
        self.speech_end_flag = False  # 表示检测到语音结束
        self.vad_pre_idx = 0  # 当前VAD处理的位置索引，与官方示例一致
        self.is_speaking = True  # 客户端手动控制的说话状态
        
        # 会话ID
        self.session_id = int(time.time())
        self.wav_name = f"session_{self.session_id}"
        self.funasr_config.wav_name = self.wav_name
        
        logger.info(f"初始化WebSocket处理器，会话ID: {self.session_id}, 识别模式: {self.funasr_config.mode}")
    
    async def accept(self) -> None:
        """接受WebSocket连接"""
        try:
            await self.websocket.accept()
            logger.info("WebSocket连接已接受")
        except Exception as e:
            logger.error(f"接受WebSocket连接时出错: {str(e)}")
            raise
    
    async def send_json(self, data: Dict[str, Any]) -> None:
        """发送JSON消息"""
        if self.connection_closed:
            logger.warning("尝试向已关闭的连接发送消息")
            return
            
        try:
            await self.websocket.send_json(data)
        except Exception as e:
            logger.error(f"发送JSON消息时出错: {str(e)}")
            self.connection_closed = True
            raise
    
    async def handle_json_message(self, message: Dict[str, Any]) -> None:
        """处理JSON消息，用于控制识别行为"""
        logger.info(f"接收JSON控制消息: {message}")
        
        # 处理识别模式
        if "mode" in message:
            mode = message["mode"]
            if mode in ["2pass", "online", "offline"]:
                self.funasr_config.mode = mode
                logger.info(f"设置识别模式为: {mode}")
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
                logger.info(f"调试 - speech_start_flag: {self.speech_start_flag}, speech_end_flag: {self.speech_end_flag}")
                print(f"调试 - VAD状态: speech_start_flag={self.speech_start_flag}, speech_end_flag={self.speech_end_flag}", flush=True)
                print(f"调试 - 帧数信息: frames={len(self.frames)}帧, frames_asr={len(self.frames_asr)}帧, frames_asr_online={len(self.frames_asr_online)}帧", flush=True)
                
                # 新条件：只要停止说话就处理，无论是否检测到语音
                self.speech_end_flag = True
                logger.info("客户端停止说话，强制结束当前语音段 (不考虑VAD状态)")
                
                # 如果没有检测到语音开始，我们为了调试也设置它为True
                if not self.speech_start_flag:
                    self.speech_start_flag = True
                    logger.info("调试 - 强制设置speech_start_flag=True用于调试")
                
                # 核心修复：确保frames_asr包含完整的语音数据
                # 之前的问题是VAD失效导致frames_asr没有积累有效语音
                if not self.frames_asr or len(self.frames_asr) < 5:  # 如果frames_asr为空或太少
                    if len(self.frames) > 0:
                        # 关键改进：使用所有历史帧，而不仅仅是最近的frames_asr_online
                        # 过滤开头可能的静音帧
                        print(f"使用完整的历史帧数据替代VAD累积的frames_asr", flush=True)
                        logger.info(f"使用完整的历史帧数据替代VAD累积的frames_asr")
                        
                        # 计算音频特征以找到有效语音起始
                        valid_frames = []
                        for frame in self.frames:
                            frame_np = np.frombuffer(frame, dtype=np.int16)
                            max_amp = np.max(np.abs(frame_np)) if len(frame_np) > 0 else 0
                            # 只保留有效声音的帧（振幅大于阈值）
                            if max_amp > 500:
                                valid_frames.append(frame)
                        
                        if valid_frames:
                            print(f"找到 {len(valid_frames)} 个有效音频帧（振幅>500）", flush=True)
                            logger.info(f"找到 {len(valid_frames)} 个有效音频帧（振幅>500）")
                            self.frames_asr = valid_frames
                        else:
                            # 如果没有找到有效声音帧，使用所有帧
                            print("未找到有效声音帧，使用所有历史帧", flush=True)
                            logger.info("未找到有效声音帧，使用所有历史帧")
                            self.frames_asr = self.frames.copy()
                    elif len(self.frames_asr_online) > 0:
                        # 备选方案：使用在线ASR的帧
                        logger.info("调试 - frames_asr为空，正在从frames_asr_online复制")
                        self.frames_asr = self.frames_asr_online.copy()
                
                await self._process_speech_end()
                
        # 处理热词
        if "hotwords" in message:
            self.funasr_config.hotwords = message["hotwords"]
            # 同时设置到离线和在线模型的状态字典中
            if hasattr(self.model, 'status_dict_asr'):
                self.model.status_dict_asr["hotword"] = message["hotwords"]
            if hasattr(self.model, 'status_dict_asr_online'):
                self.model.status_dict_asr_online["hotword"] = message["hotwords"]
            logger.info(f"设置热词: {self.funasr_config.hotwords}")
            
        # 处理分块大小
        if "chunk_size" in message:
            chunk_size = message["chunk_size"]
            if isinstance(chunk_size, list):
                self.funasr_config.chunk_size = chunk_size
            elif isinstance(chunk_size, str):
                self.funasr_config.chunk_size = [int(x) for x in chunk_size.split(",")]
            logger.info(f"设置分块大小为: {self.funasr_config.chunk_size}")
            
        # 处理分块间隔
        if "chunk_interval" in message:
            self.funasr_config.chunk_interval = int(message["chunk_interval"])
            logger.info(f"设置分块间隔为: {self.funasr_config.chunk_interval}")
            
        # 处理音频名称
        if "wav_name" in message:
            self.funasr_config.wav_name = message["wav_name"]
            self.wav_name = message["wav_name"]
            logger.info(f"设置音频名称为: {self.wav_name}")
            
        # 处理ITN设置
        if "itn" in message:
            self.funasr_config.itn = bool(message["itn"])
            logger.info(f"设置ITN为: {self.funasr_config.itn}")
            
        # 返回当前设置状态
        await self.send_status(STATUS_LISTENING, {"config": self.funasr_config.dict()})
    
    async def handle_binary_message(self, binary_data: bytes) -> None:
        """处理二进制音频数据"""
        # 检查数据有效性
        if not binary_data or len(binary_data) == 0:
            logger.warning("收到空的二进制数据")
            return
            
        # 日志记录接收到的音频数据
        data_len = len(binary_data)
        logger.debug(f"处理二进制音频数据: {data_len} 字节")
        
        # 将音频数据转换为numpy数组并计算基本信息
        audio_np = np.frombuffer(binary_data, dtype=np.int16)
        samples = len(audio_np)
        non_zero = np.count_nonzero(audio_np)
        non_zero_ratio = non_zero / samples if samples > 0 else 0
        max_amp = np.max(np.abs(audio_np)) if samples > 0 else 0
        
        # 只在音频数据有实质内容时详细记录
        if max_amp > 500:
            logger.debug(f"音频数据: 样本数={samples}, 非零样本={non_zero}, "
                      f"非零比例={non_zero_ratio:.4f}, 最大振幅={max_amp}")
        
        # 添加到所有帧列表，用于历史上下文
        self.frames.append(binary_data)
        
        # 计算帧持续时间，用于VAD预处理
        duration_ms = len(binary_data) // 32  # 16kHz 16bit = 32字节/毫秒
        self.vad_pre_idx += duration_ms
        
        # 同时添加到在线ASR帧列表，用于流式处理
        self.frames_asr_online.append(binary_data)
        
        # 使用FunASR VAD模型进行语音检测
        try:
            # 调用FunASR VAD模型进行语音检测
            vad_result = await self.model.process_vad(binary_data, self.vad_status_dict)
            
            # 调试：输出原始VAD结果
            print(f"调试 - 原始VAD结果: {vad_result}", flush=True)
            
            # 解析VAD结果，获取语音起止点
            speech_start_i = -1
            speech_end_i = -1
            
            if "segments" in vad_result and vad_result["segments"]:
                segment = vad_result["segments"][0]  # 获取第一个语音段
                print(f"调试 - VAD检测到语音段: {segment}", flush=True)
                
                if len(segment) >= 2:
                    speech_start_i = segment[0] if segment[0] != -1 else -1
                    speech_end_i = segment[1] if segment[1] != -1 else -1
                    print(f"调试 - 提取语音点: 起始={speech_start_i}, 结束={speech_end_i}", flush=True)
            else:
                print(f"调试 - VAD未检测到语音段, 当前帧振幅: {max_amp}", flush=True)
            
            # 调试点2: 记录VAD的准确性信息
            if speech_start_i != -1 or speech_end_i != -1:
                logger.info(f"VAD检测结果: 起始点={speech_start_i}ms, 结束点={speech_end_i}ms, vad_pre_idx={self.vad_pre_idx}ms")
                if speech_start_i != -1:
                    # 计算相对于当前帧的偏移量
                    relative_start = speech_start_i - (self.vad_pre_idx - duration_ms)
                    logger.info(f"VAD语音起始点相对于当前帧起始的偏移量: {relative_start}ms")
                    print(f"调试 - VAD语音起始点相对于当前帧起始的偏移量: {relative_start}ms", flush=True)
            
            # 更新VAD状态字典缓存
            if "cache" in vad_result:
                self.vad_status_dict["cache"] = vad_result.get("cache", {})
            
            # 处理语音开始
            if speech_start_i != -1 and not self.speech_start_flag:
                self.speech_start_flag = True
                logger.info(f"VAD检测到语音开始，帧位置: {speech_start_i}ms，当前vad_pre_idx: {self.vad_pre_idx}ms")
                print(f"调试 - VAD检测到语音开始！帧位置: {speech_start_i}ms, 当前vad_pre_idx: {self.vad_pre_idx}ms", flush=True)
                await self.send_status(STATUS_PROCESSING)
                
                self.frames_asr = [] # 首先清空，确保从干净的状态开始

                # 定义希望保留的前导音频时长（毫秒）或帧数
                # 例如，保留最多约200ms的前导音频 (16kHz, 16bit，每毫秒2*16=32字节)
                # 200ms * 32 bytes/ms = 6400 bytes
                # 假设WebSocket接收的每个binary_data块大致对应一个chunk_interval (e.g., 60ms for paraformer default)
                # 200ms / 60ms_per_chunk ~= 3-4 chunks/frames
                # 或者简单地取最后 N 帧
                num_prefix_frames_to_keep = 3  # 例如，保留最后3帧作为前导
                
                # self.frames 已经包含了当前的 binary_data (在函数的开头 append 的)
                # 取 self.frames[:-1] 是为了获取 binary_data 之前的历史帧
                historical_frames_before_current = self.frames[:-1] 
                
                if historical_frames_before_current:
                    actual_prefix_frames = historical_frames_before_current[-num_prefix_frames_to_keep:]
                    self.frames_asr.extend(actual_prefix_frames)
                    logger.info(f"已添加 {len(actual_prefix_frames)} 帧 (共 {sum(len(f) for f in actual_prefix_frames)} 字节) 作为前导帧到 frames_asr。")
                    print(f"调试 - 已添加 {len(actual_prefix_frames)} 帧作为前导帧", flush=True)
                
            # 如果语音已开始且未结束，添加当前帧到离线ASR列表
            if self.speech_start_flag and not self.speech_end_flag:
                self.frames_asr.append(binary_data)
                
            # 手动停止时强制设置结束点    
            if not self.is_speaking and self.speech_start_flag and not self.speech_end_flag:
                speech_end_i = 0
                logger.info("检测到客户端停止录音，强制设置语音结束")
                
            # 处理在线ASR
            if len(self.frames_asr_online) >= self.funasr_config.chunk_interval or speech_end_i != -1:
                is_final_online = speech_end_i != -1 or not self.is_speaking
                self.model.status_dict_asr_online["is_final"] = is_final_online
                
                # 只在支持的模式下处理在线ASR
                if self.funasr_config.mode in ["2pass", "online"]:
                    audio_in = b"".join(self.frames_asr_online)
                    try:
                        await self._process_online_audio(audio_in, is_final_online)
                    except Exception as e:
                        logger.error(f"在线ASR处理出错: {str(e)}")
                
                # 处理完后清空在线帧缓存
                self.frames_asr_online = []
            
            # 语音结束处理
            if speech_end_i != -1 and self.speech_start_flag and not self.speech_end_flag:
                self.speech_end_flag = True
                logger.info(f"VAD检测到语音结束，帧位置: {speech_end_i}ms")
                print(f"调试 - VAD检测到语音结束！帧位置: {speech_end_i}ms", flush=True)
                await self._process_speech_end()
                
            # 调试VAD状态
            if len(self.frames) % 10 == 0:  # 每10帧打印一次
                print(f"调试 - 当前状态: frames={len(self.frames)}帧, speech_start_flag={self.speech_start_flag}, speech_end_flag={self.speech_end_flag}", flush=True)
                
        except Exception as e:
            logger.error(f"处理音频数据时出错: {str(e)}")
            logger.exception(e)
    
    async def _process_speech_end(self) -> None:
        """处理语音段结束时的逻辑"""
        print("===== 开始处理语音段结束逻辑 =====", flush=True)
        logger.info("开始处理语音段结束逻辑")
        
        # 处理离线ASR - 在语音结束时
        if self.funasr_config.mode in ["2pass", "offline"] and self.frames_asr:
            print(f"检测到frames_asr非空，长度为: {len(self.frames_asr)}帧", flush=True)
            logger.info(f"检测到frames_asr非空，长度为: {len(self.frames_asr)}帧")
            
            audio_in = b"".join(self.frames_asr)
            
            # 强化调试：将音频保存到临时文件
            try:
                # 保存音频文件到固定目录
                debug_dir = "/tmp/nextalk_debug"
                os.makedirs(debug_dir, exist_ok=True)
                
                # 生成唯一文件名
                timestamp = int(time.time())
                audio_file = os.path.join(debug_dir, f'offline_audio_{self.session_id}_{timestamp}.wav')
                
                # 保存为WAV文件
                with wave.open(audio_file, 'wb') as wf:
                    wf.setnchannels(1)  # 单声道
                    wf.setsampwidth(2)  # 16位
                    wf.setframerate(16000)  # 16kHz采样率
                    audio_np = np.frombuffer(audio_in, dtype=np.int16)
                    wf.writeframes(audio_np.tobytes())
                
                # 强制输出到标准输出
                print(f"调试: 已保存离线处理音频到: {audio_file}", flush=True)
                logger.info(f"调试: 已保存离线处理音频到: {audio_file}")
                
                # 计算音频信息并记录，方便分析
                duration_s = len(audio_np) / 16000
                max_amp = np.max(np.abs(audio_np))
                non_zero = np.count_nonzero(audio_np)
                non_zero_ratio = non_zero / len(audio_np) if len(audio_np) > 0 else 0
                
                print(f"调试: 离线音频信息: 长度={duration_s:.3f}秒, 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}", flush=True)
                logger.info(f"调试: 离线音频信息: 长度={duration_s:.3f}秒, 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}")
            except Exception as e:
                print(f"调试: 保存离线音频文件失败: {str(e)}", flush=True)
                logger.error(f"保存离线音频文件失败: {str(e)}")
            
            try:
                print("开始调用离线音频处理...", flush=True)
                logger.info("开始调用离线音频处理...")
                await self._process_offline_audio(audio_in)
            except Exception as e:
                print(f"离线ASR处理出错: {str(e)}", flush=True)
                logger.error(f"离线ASR处理出错: {str(e)}")
        else:
            print(f"未处理离线音频 - 模式: {self.funasr_config.mode}, frames_asr是否为空: {not bool(self.frames_asr)}", flush=True)
            logger.info(f"未处理离线音频 - 模式: {self.funasr_config.mode}, frames_asr是否为空: {not bool(self.frames_asr)}")
        
        # 重置状态
        logger.info("重置所有状态和缓存")
        self.frames_asr = []
        self.speech_start_flag = False
        self.speech_end_flag = False
        self.frames_asr_online = []
        
        # 清理模型缓存
        await self.model.reset()
        
        # 如果是手动停止，完全重置
        if not self.is_speaking:
            self.vad_pre_idx = 0
            self.frames = []
            self.vad_status_dict["cache"] = {}
        else:
            # 保留最近的帧做为上下文
            self.frames = self.frames[-20:] if len(self.frames) > 20 else self.frames
        
        # 更新状态
        await self.send_status(STATUS_LISTENING)
    
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
        if self.funasr_config.mode == "2pass" and self.speech_end_flag:
            return
            
        start_time = time.time()
            
        # 将FunASR配置转换为模型可接受的格式
        self.model.status_dict_asr_online["is_final"] = is_final
        self.model.status_dict_asr_online["chunk_size"] = self.funasr_config.chunk_size
        
        # 确保添加 encoder_chunk_look_back 和 decoder_chunk_look_back 参数到模型状态字典
        if self.funasr_config.encoder_chunk_look_back is not None:
            self.model.status_dict_asr_online["encoder_chunk_look_back"] = self.funasr_config.encoder_chunk_look_back
            logger.debug(f"设置在线ASR encoder_chunk_look_back: {self.funasr_config.encoder_chunk_look_back}")
        
        if self.funasr_config.decoder_chunk_look_back is not None:
            self.model.status_dict_asr_online["decoder_chunk_look_back"] = self.funasr_config.decoder_chunk_look_back
            logger.debug(f"设置在线ASR decoder_chunk_look_back: {self.funasr_config.decoder_chunk_look_back}")
        
        # 处理音频
        result = await self.model.process_audio_chunk(audio_data, is_final)
        
        # 检查结果有效性
        if not result or "text" not in result:
            logger.warning("在线ASR返回无效结果")
            return
            
        # 日志记录
        process_time = time.time() - start_time
        logger.info(f"在线ASR处理完成，耗时: {process_time:.3f}秒, 结果长度: {len(result.get('text', ''))}")
        
        # 记录转录文本内容
        text = result.get("text", "")
        if text:
            logger.info(f"在线ASR转录内容 [{'最终' if is_final else '临时'}]: '{text}'")
        
        # 添加模式和会话标识符
        result["mode"] = "2pass-online" if self.funasr_config.mode == "2pass" else "online"
        result["wav_name"] = self.wav_name
        result["is_final"] = is_final
        result["session_id"] = self.session_id
        result["timestamp"] = int(time.time())
        
        # 发送结果 - 使用transcription类型而不是recognition类型
        await self.send_json({
            "type": "transcription",  # 改为客户端期望的类型
            "text": result.get("text", ""),
            "is_final": is_final,
            "mode": result["mode"],
            "wav_name": self.wav_name,
            "session_id": self.session_id,
            "timestamp": int(time.time())
        })
    
    async def _process_offline_audio(self, audio_data: bytes) -> None:
        """
        处理离线音频数据
        
        Args:
            audio_data: 原始音频数据
        """
        if not audio_data or len(audio_data) == 0:
            logger.warning("离线处理收到空音频数据，跳过处理")
            return
        
        # 检查音频数据基本情况
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        duration_s = len(audio_np) / 16000
        max_amp = np.max(np.abs(audio_np))
        non_zero = np.count_nonzero(audio_np)
        non_zero_ratio = non_zero / len(audio_np) if len(audio_np) > 0 else 0
        
        logger.info(f"离线ASR处理音频长度: {len(audio_np)} 样本({duration_s:.2f}秒), 最大振幅: {max_amp}, 非零比例: {non_zero_ratio:.4f}")
        
        # 音频短于250ms且振幅低，可能不是有效语音，跳过处理
        if duration_s < 0.25 and max_amp < 500:
            logger.warning(f"音频太短且振幅太低，跳过离线处理: {duration_s:.2f}秒, 振幅: {max_amp}")
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
                logger.info(f"离线ASR处理完成，耗时: {process_time:.3f}秒，标点前: '{original_text}'，标点后: '{text}'")
            else:
                logger.info(f"离线ASR处理完成，耗时: {process_time:.3f}秒, 结果: '{result.get('text', '')}'")
            
            # 添加模式和会话标识符
            mode = "2pass-offline" if self.funasr_config.mode == "2pass" else "offline"
            
            # 准备结果数据
            response_data = {
                "type": "transcription",  # 改为客户端期望的类型
                "text": result.get("text", ""),
                "is_final": True,  # 离线结果总是最终的
                "mode": mode,
                "wav_name": self.wav_name,
                "session_id": self.session_id,
                "timestamp": int(time.time()),
                "audio_duration": duration_s
            }
            
            # 如果有标点前的原始ASR结果，也一并发送
            if original_text:
                response_data["original_text"] = original_text
                
                # 如果标点前后差异大，特别记录
                if len(original_text) > 0 and len(text) > 0 and abs(len(original_text) - len(text)) / max(len(original_text), len(text)) > 0.5:
                    logger.warning(f"标点前后文本长度差异巨大，标点前: [{len(original_text)}字] '{original_text}'，标点后: [{len(text)}字] '{text}'")
                    response_data["text_difference_warning"] = True
                
            # 发送结果
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
                        logger.info("客户端断开连接")
                        break
                    elif message["type"] == "websocket.receive":
                        if "bytes" in message:
                            await self.handle_message(message["bytes"])
                        elif "text" in message:
                            await self.handle_message(message["text"])
                else:
                    logger.warning(f"未知的消息格式: {message}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket连接断开")
        except asyncio.CancelledError:
            logger.info("WebSocket处理任务被取消")
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
            
            logger.info("WebSocket处理完成")
    
    async def send_status(self, status: str, extra_data: Dict[str, Any] = None) -> None:
        """发送状态消息"""
        data = {
            "type": "status",
            "status": status,
            "timestamp": int(time.time())
        }
        
        if extra_data:
            data.update(extra_data)
            
        await self.send_json(data) 