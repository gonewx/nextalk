"""
WebSocket处理器模块

直接移植官方funasr_wss_server.py的ws_serve函数逻辑到FastAPI WebSocket，
保持官方示例的处理流程，同时支持多客户端并发。
"""

import asyncio
import json
import logging

from fastapi import WebSocket, WebSocketDisconnect

from .funasr_model import async_vad, async_asr, async_asr_online

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.websocket_handler")


async def handle_websocket(websocket: WebSocket):
    """
    直接移植官方funasr_wss_server.py的ws_serve函数逻辑到FastAPI
    保持官方示例的变量命名、状态管理和处理流程，支持多客户端并发
    """
    # 移植官方示例的变量结构
    frames = []
    frames_asr = []
    frames_asr_online = []
    
    # 官方的状态字典结构（每连接独立，支持并发）
    websocket.status_dict_asr = {}
    websocket.status_dict_asr_online = {"cache": {}, "is_final": False}
    websocket.status_dict_vad = {"cache": {}, "is_final": False}
    websocket.status_dict_punc = {"cache": {}}
    websocket.chunk_interval = 10
    websocket.vad_pre_idx = 0
    speech_start = False
    speech_end_i = -1
    websocket.wav_name = "microphone"
    websocket.mode = "2pass"
    websocket.is_speaking = True
    
    logger.info("new user connected")
    
    try:
        while True:
            # 接收消息 (可能是文本或字节)
            message = await websocket.receive()
            
            if message["type"] == "websocket.disconnect":
                break
            elif message["type"] == "websocket.receive":
                if "text" in message:
                    # 处理JSON配置消息
                    try:
                        messagejson = json.loads(message["text"])
                        
                        # 按照官方示例处理JSON配置消息
                        if "is_speaking" in messagejson:
                            websocket.is_speaking = messagejson["is_speaking"]
                            websocket.status_dict_asr_online["is_final"] = not websocket.is_speaking
                            websocket.status_dict_vad["is_final"] = not websocket.is_speaking
                            # 设置websocket属性用于VAD cache处理
                            websocket.is_final_chunk = not websocket.is_speaking
                            
                            # 纯离线模式：在停止说话时立即处理累积的音频
                            if not websocket.is_speaking and websocket.mode == "offline" and len(frames) > 0:
                                logger.info(f"📄 离线模式处理完整音频: {len(frames)}块, 总计{sum(len(f) for f in frames)}字节")
                                complete_audio = b"".join(frames)
                                try:
                                    from .funasr_model import async_asr
                                    await async_asr(websocket, complete_audio)
                                except Exception as e:
                                    logger.error(f"离线ASR处理错误: {e}")
                                # 清空缓冲区
                                frames = []
                                logger.debug(f"📄 离线模式处理完成，缓冲区已清空")
                            
                            # 2pass模式：在停止说话时触发离线ASR（如果有累积的语音）
                            elif not websocket.is_speaking and websocket.mode == "2pass" and len(frames_asr) > 0:
                                asr_audio_len = sum(len(frame) for frame in frames_asr) // 32 if frames_asr else 0
                                logger.info(f"🤐 触发离线ASR: 用户停止说话, 累积帧数={len(frames_asr)}, 音频时长={asr_audio_len}ms")
                                
                                audio_in = b"".join(frames_asr)
                                try:
                                    from .funasr_model import async_asr
                                    await async_asr(websocket, audio_in)
                                except Exception as e:
                                    logger.error(f"error in asr offline: {e}")
                                
                                # 清理状态
                                frames_asr = []
                                frames_asr_online = []
                                websocket.status_dict_asr_online["cache"] = {}
                                websocket.vad_pre_idx = 0
                                frames = []
                                websocket.status_dict_vad["cache"] = {}
                                logger.info(f"🔄 重置所有缓冲区（用户停止说话）")
                        if "chunk_interval" in messagejson:
                            websocket.chunk_interval = messagejson["chunk_interval"]
                        if "wav_name" in messagejson:
                            websocket.wav_name = messagejson.get("wav_name")
                        if "chunk_size" in messagejson:
                            chunk_size = messagejson["chunk_size"]
                            if isinstance(chunk_size, str):
                                chunk_size = chunk_size.split(",")
                            websocket.status_dict_asr_online["chunk_size"] = [int(x) for x in chunk_size]
                        if "encoder_chunk_look_back" in messagejson:
                            websocket.status_dict_asr_online["encoder_chunk_look_back"] = messagejson[
                                "encoder_chunk_look_back"
                            ]
                        if "decoder_chunk_look_back" in messagejson:
                            websocket.status_dict_asr_online["decoder_chunk_look_back"] = messagejson[
                                "decoder_chunk_look_back"
                            ]
                        if "hotwords" in messagejson:
                            # 协议要求hotwords为字符串格式
                            hotwords_str = messagejson["hotwords"]
                            if isinstance(hotwords_str, str):
                                try:
                                    import ast
                                    hotwords_dict = ast.literal_eval(hotwords_str)
                                    websocket.status_dict_asr["hotword"] = hotwords_dict
                                except (ValueError, SyntaxError):
                                    logger.warning(f"热词格式解析失败: {hotwords_str}")
                            else:
                                websocket.status_dict_asr["hotword"] = hotwords_str
                        if "mode" in messagejson:
                            websocket.mode = messagejson["mode"]
                        if "wav_format" in messagejson:
                            websocket.wav_format = messagejson["wav_format"]
                        if "audio_fs" in messagejson:
                            websocket.audio_fs = messagejson["audio_fs"] 
                        if "itn" in messagejson:
                            websocket.itn = messagejson["itn"]
                            
                        # 设置VAD chunk_size（仅在配置阶段）
                        if "chunk_size" in websocket.status_dict_asr_online:
                            websocket.status_dict_vad["chunk_size"] = int(
                                websocket.status_dict_asr_online["chunk_size"][1] * 60 / websocket.chunk_interval
                            )
                        
                        logger.info(f"📋 处理JSON配置消息: {messagejson}")
                        logger.info(f"📋 配置后状态: asr_online={websocket.status_dict_asr_online}, vad={websocket.status_dict_vad}")
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"JSON解析错误: {e}")
                        
                elif "bytes" in message:
                    # 处理音频字节数据
                    audio_data = message["bytes"]
                    
                    # 调试：记录音频数据接收
                    audio_len_ms = len(audio_data) // 32  # 16kHz, 16-bit = 32 bytes per ms  
                    frame_count = len(frames_asr_online)
                    logger.info(f"📡 收到音频数据: {len(audio_data)}字节 ({audio_len_ms}ms), 在线帧数: {frame_count}")
                    logger.info(f"📡 当前模式: {websocket.mode}, 将判断处理分支")
                    
                    # 纯离线模式：直接累积音频，不进行流式处理
                    if websocket.mode == "offline":
                        frames.append(audio_data)
                        logger.info(f"📄 离线模式累积音频: {len(frames)}块, 总计{sum(len(f) for f in frames)}字节")
                    # 流式模式（2pass/online）：按照官方示例的条件判断
                    else:
                        logger.info(f"⚡ 进入流式处理分支: mode={websocket.mode}")
                        # 按照官方示例，在每次音频处理时确保VAD chunk_size正确设置
                        if "chunk_size" in websocket.status_dict_asr_online:
                            websocket.status_dict_vad["chunk_size"] = int(
                                websocket.status_dict_asr_online["chunk_size"][1] * 60 / websocket.chunk_interval
                            )
                        
                        frames.append(audio_data)
                        duration_ms = len(audio_data) // 32
                        websocket.vad_pre_idx += duration_ms

                        # asr online - 移植官方逻辑
                        frames_asr_online.append(audio_data)
                        websocket.status_dict_asr_online["is_final"] = speech_end_i != -1
                        if (
                            len(frames_asr_online) % websocket.chunk_interval == 0
                            or websocket.status_dict_asr_online["is_final"]
                        ):
                            if websocket.mode == "2pass" or websocket.mode == "online":
                                audio_in = b"".join(frames_asr_online)
                                try:
                                    await async_asr_online(websocket, audio_in)
                                except Exception as e:
                                    logger.error(f"error in asr streaming: {e}, {websocket.status_dict_asr_online}")
                            frames_asr_online = []
                            
                        if speech_start:
                            frames_asr.append(audio_data)
                            
                        # vad online - 按照官方示例，直接对每个音频块进行VAD
                        speech_start_i, speech_end_i = -1, -1
                        logger.info(f"🎙️  开始VAD处理: {len(audio_data)}字节")
                        try:
                            speech_start_i, speech_end_i = await async_vad(websocket, audio_data)
                            logger.info(f"🎙️  VAD结果: start={speech_start_i}, end={speech_end_i}")
                        except Exception as e:
                            logger.error(f"error in vad: {e}")
                            
                        if speech_start_i != -1:
                            speech_start = True
                            beg_bias = (websocket.vad_pre_idx - speech_start_i) // duration_ms
                            frames_pre = frames[-beg_bias:] if beg_bias > 0 and beg_bias <= len(frames) else frames
                            frames_asr = []
                            frames_asr.extend(frames_pre)
                            
                            logger.info(f"🎤 语音开始检测: vad_pre_idx={websocket.vad_pre_idx}, speech_start_i={speech_start_i}, beg_bias={beg_bias}, 预存帧数={len(frames_pre)}")
                            
                        # asr punc offline - 移植官方逻辑，添加最小语音段长度限制
                        if speech_end_i != -1 or not websocket.is_speaking:
                            reason = "语音结束VAD检测" if speech_end_i != -1 else "用户停止说话"
                            asr_frames_count = len(frames_asr)
                            asr_audio_len = sum(len(frame) for frame in frames_asr) // 32 if frames_asr else 0
                            
                            # 只有语音段足够长（>=300ms）或用户明确停止说话时才处理
                            MIN_SPEECH_DURATION_MS = 300  # 300ms，避免过短片段但不过于严格
                            should_process = (asr_audio_len >= MIN_SPEECH_DURATION_MS) or (not websocket.is_speaking)
                            
                            if should_process:
                                logger.info(f"🤐 触发离线ASR: {reason}, 累积帧数={asr_frames_count}, 音频时长={asr_audio_len}ms")
                                
                                if websocket.mode == "2pass" or websocket.mode == "offline":
                                    audio_in = b"".join(frames_asr)
                                    try:
                                        await async_asr(websocket, audio_in)
                                    except Exception as e:
                                        logger.error(f"error in asr offline: {e}")
                                frames_asr = []
                            else:
                                logger.debug(f"⏸️  语音段太短，跳过ASR: {asr_audio_len}ms < {MIN_SPEECH_DURATION_MS}ms")
                            speech_start = False
                            frames_asr_online = []
                            websocket.status_dict_asr_online["cache"] = {}
                            if not websocket.is_speaking:
                                websocket.vad_pre_idx = 0
                                frames = []
                                websocket.status_dict_vad["cache"] = {}
                                logger.debug(f"🔄 重置所有缓冲区（用户停止说话）")
                            else:
                                frames = frames[-20:]
                                logger.debug(f"🔄 保留最近20帧，当前帧数={len(frames)}")
                                
    except WebSocketDisconnect:
        logger.info("WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket处理错误: {e}")
    finally:
        # 清理连接状态
        try:
            websocket.status_dict_asr_online["cache"] = {}
            websocket.status_dict_asr_online["is_final"] = True
            websocket.status_dict_vad["cache"] = {}
            websocket.status_dict_vad["is_final"] = True
            websocket.status_dict_punc["cache"] = {}
            logger.info("WebSocket连接状态已清理")
        except Exception as e:
            logger.error(f"清理WebSocket状态时出错: {e}")


# 保持向后兼容的WebSocketHandler类（如果其他地方还在使用）
class WebSocketHandler:
    """WebSocket处理器类（向后兼容）"""

    def __init__(self, websocket: WebSocket, model=None):
        """初始化WebSocket处理器"""
        self.websocket = websocket
        logger.debug("初始化WebSocket处理器（兼容模式）")

    async def accept(self) -> None:
        """接受WebSocket连接"""
        await self.websocket.accept()
        logger.debug("WebSocket连接已接受")

    async def handle(self) -> None:
        """处理WebSocket连接"""
        await handle_websocket(self.websocket)