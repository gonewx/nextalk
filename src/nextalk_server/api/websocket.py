"""
WebSocket API for real-time audio streaming and transcription.

This module implements the WebSocket endpoint that clients connect to for streaming
audio data and receiving transcription results.
"""

import logging
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np

from ..audio.vad import VADFilter
from ..audio.buffer import AudioBuffer
from ..asr.recognizer import ASRRecognizer
from ..config.settings import settings
from ..models.manager import ModelManager
from . import control
from nextalk_shared.data_models import TranscriptionResponse, ErrorMessage, StatusUpdate, CommandMessage
from nextalk_shared.constants import STATUS_LISTENING, STATUS_PROCESSING, STATUS_ERROR

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter()

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点，用于接收客户端音频流并返回转录结果。
    
    接收音频数据流，使用VAD检测语音，只处理包含语音的音频帧，
    并将语音帧添加到音频缓冲区以进行后续处理。
    启动一个异步任务来处理缓冲区中的音频并返回转录结果。
    
    同时支持接收JSON格式的命令消息，用于控制服务器行为，如切换模型。
    """
    # 接受WebSocket连接
    await websocket.accept()
    
    logger.info("WebSocket连接已建立")
    
    # 实例化VAD过滤器
    vad_filter = VADFilter(sensitivity=settings.vad_sensitivity)
    logger.info(f"VAD过滤器已初始化，灵敏度级别：{settings.vad_sensitivity}")
    
    # 实例化音频缓冲区
    audio_buffer = AudioBuffer(max_size=300)  # 300帧约等于9秒音频（每帧30ms）
    logger.info("音频缓冲区已初始化")
    
    # 实例化ASR识别器
    asr_recognizer = ASRRecognizer(
        model_size=settings.model_size,
        model_path=settings.model_path,
        device=settings.device,
        compute_type=settings.compute_type
    )
    logger.info(f"ASR识别器已初始化，模型：{settings.model_size}，设备：{settings.device}")
    
    # 创建模型管理器实例
    model_manager = ModelManager(settings)
    logger.info("模型管理器已初始化")
    
    # 发送初始状态消息
    status_update = StatusUpdate(state=STATUS_LISTENING)
    await websocket.send_json(status_update.dict())
    logger.debug(f"已发送状态更新：{STATUS_LISTENING}")
    
    # 标记ASR处理是否正在进行
    processing_active = True
    
    # 创建ASR处理任务取消的事件
    stop_processing = asyncio.Event()
    
    # 跟踪统计信息
    total_frames = 0
    speech_frames = 0
    buffered_frames = 0
    
    # 定义ASR处理循环
    async def process_audio():
        """定期检查缓冲区，处理音频并发送转录结果。"""
        transcriptions_sent = 0
        
        while processing_active and not stop_processing.is_set():
            try:
                # 获取一个至少1秒的音频段
                segment = audio_buffer.get_segment(min_duration_ms=1000)
                
                if segment is not None:
                    audio_data, sample_rate = segment
                    
                    # 通知客户端正在处理
                    proc_status = StatusUpdate(state=STATUS_PROCESSING)
                    await websocket.send_json(proc_status.dict())
                    logger.debug("正在处理音频段以进行转录")
                    
                    # 请求转录
                    try:
                        # 获取转录文本
                        transcription_text = asr_recognizer.transcribe(audio_data)
                        
                        # 只有在有实际文本时才发送
                        if transcription_text and len(transcription_text.strip()) > 0:
                            # 使用Pydantic模型创建转录响应
                            response = TranscriptionResponse(text=transcription_text)
                            
                            # 验证响应格式
                            response_dict = response.dict()
                            logger.debug(f"转录响应格式：{response_dict}")
                            
                            # 发送JSON响应
                            await websocket.send_json(response_dict)
                            transcriptions_sent += 1
                            logger.info(f"已发送转录结果（{transcriptions_sent}）：{transcription_text[:50]}...")
                        else:
                            logger.debug("转录结果为空，不发送")
                    except RuntimeError as re:
                        # 处理ASR识别器中的特定运行时错误
                        logger.error(f"转录运行时错误：{str(re)}")
                        error_msg = ErrorMessage(message=f"转录错误：{str(re)}")
                        await websocket.send_json(error_msg.dict())
                        
                        # 发送错误状态更新
                        error_status = StatusUpdate(state=STATUS_ERROR)
                        await websocket.send_json(error_status.dict())
                    except Exception as e:
                        # 处理其他转录过程中的错误
                        logger.error(f"转录过程中出错：{str(e)}", exc_info=True)
                        error_msg = ErrorMessage(message=f"转录过程失败：{str(e)}")
                        await websocket.send_json(error_msg.dict())
                        
                        # 发送错误状态更新
                        error_status = StatusUpdate(state=STATUS_ERROR)
                        await websocket.send_json(error_status.dict())
                    finally:
                        # 转回监听状态（无论是否成功）
                        listen_status = StatusUpdate(state=STATUS_LISTENING)
                        await websocket.send_json(listen_status.dict())
                
                # 等待一小段时间再检查缓冲区
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                # 处理任务取消
                logger.info("音频处理任务被取消")
                break
            except Exception as e:
                # 处理其他所有错误
                logger.error(f"音频处理循环错误：{str(e)}", exc_info=True)
                try:
                    error_msg = ErrorMessage(message=f"内部处理错误：{str(e)}")
                    await websocket.send_json(error_msg.dict())
                    
                    # 发送错误状态更新
                    error_status = StatusUpdate(state=STATUS_ERROR)
                    await websocket.send_json(error_status.dict())
                    
                    # 短暂暂停后恢复监听状态
                    await asyncio.sleep(1.0)
                    listen_status = StatusUpdate(state=STATUS_LISTENING)
                    await websocket.send_json(listen_status.dict())
                except Exception:
                    logger.exception("发送错误消息时遇到异常")
        
        logger.debug("音频处理循环已结束")
    
    # 启动ASR处理任务
    process_task = asyncio.create_task(process_audio())
    logger.debug("ASR处理任务已启动")
    
    try:
        # 创建一个任务来处理文本消息
        text_message_tasks = []
        
        # 持续监听来自客户端的消息
        while True:
            # 创建两个接收任务，一个用于二进制数据，一个用于文本数据
            receive_bytes_task = asyncio.create_task(websocket.receive_bytes())
            receive_text_task = asyncio.create_task(websocket.receive_text())
            
            # 等待任一任务完成
            done, pending = await asyncio.wait(
                [receive_bytes_task, receive_text_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 取消未完成的任务
            for task in pending:
                task.cancel()
            
            # 处理完成的任务
            for task in done:
                try:
                    result = task.result()
                    
                    if task == receive_bytes_task:
                        # 处理二进制数据（音频）
                        data = result
                        total_frames += 1
                        
                        # 使用VAD检测是否为语音
                        if vad_filter.is_speech(data):
                            speech_frames += 1
                            
                            # 将语音帧添加到音频缓冲区
                            if audio_buffer.add_frame(data):
                                buffered_frames += 1
                                logger.debug(f"检测到语音：第 {total_frames} 帧已添加到缓冲区，语音帧总数：{speech_frames}")
                            else:
                                logger.warning(f"无法将语音帧添加到缓冲区：第 {total_frames} 帧")
                        else:
                            logger.debug(f"未检测到语音：第 {total_frames} 帧")
                        
                        # 每100帧记录一次统计信息
                        if total_frames % 100 == 0:
                            speech_ratio = (speech_frames / total_frames) * 100
                            buffer_status = audio_buffer.get_buffer_status()
                            logger.info(f"处理统计：总帧数 {total_frames}，语音帧数 {speech_frames}，"
                                      f"语音比例 {speech_ratio:.1f}%，"
                                      f"缓冲区帧数 {buffer_status['current_size']}，"
                                      f"缓冲区音频时长 {buffer_status['duration_ms']}ms")
                    
                    elif task == receive_text_task:
                        # 处理文本数据（命令）
                        text_data = result
                        logger.debug(f"收到文本消息：{text_data}")
                        
                        try:
                            # 尝试解析JSON
                            json_data = json.loads(text_data)
                            
                            # 检查是否为命令消息
                            if json_data.get("type") == "command":
                                try:
                                    # 使用Pydantic验证命令消息格式
                                    command_message = CommandMessage(**json_data)
                                    
                                    # 处理命令
                                    await control.handle_command(command_message, model_manager, websocket)
                                except Exception as e:
                                    logger.error(f"处理命令时出错：{str(e)}", exc_info=True)
                                    error_msg = ErrorMessage(message=f"处理命令失败：{str(e)}")
                                    await websocket.send_json(error_msg.dict())
                            else:
                                logger.warning(f"收到未知类型的JSON消息：{json_data}")
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析接收到的文本消息为JSON：{text_data}")
                        except Exception as e:
                            logger.error(f"处理文本消息时出错：{str(e)}", exc_info=True)
                except Exception as e:
                    logger.error(f"处理WebSocket消息时出错：{str(e)}", exc_info=True)

    except WebSocketDisconnect:
        logger.info("WebSocket连接已关闭")
        
        # 停止处理任务
        processing_active = False
        stop_processing.set()
        
        # 等待处理任务完成
        try:
            await asyncio.wait_for(process_task, timeout=2.0)
        except asyncio.TimeoutError:
            process_task.cancel()
            logger.warning("ASR处理任务取消")
        
        # 获取并记录最终的缓冲区状态
        final_buffer_status = audio_buffer.get_buffer_status()
        
        logger.info(f"连接汇总：总帧数 {total_frames}，语音帧数 {speech_frames}，"
                   f"语音比例 {(speech_frames / max(1, total_frames)) * 100:.1f}%，"
                   f"缓冲区帧数 {final_buffer_status['current_size']}，"
                   f"缓冲区音频时长 {final_buffer_status['duration_ms']}ms")
        
        # 清空缓冲区
        audio_buffer.clear()
    except Exception as e:
        logger.error(f"WebSocket错误：{str(e)}", exc_info=True)
        # 停止处理任务
        processing_active = False
        stop_processing.set()
        
        # 尝试取消处理任务
        if not process_task.done():
            process_task.cancel()
        
        # 尝试关闭连接
        try:
            await websocket.close()
        except:
            pass 