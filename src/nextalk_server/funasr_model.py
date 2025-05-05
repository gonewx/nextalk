"""
FunASR模型模块

提供FunASR模型封装，负责模型的加载和音频处理。
"""

import os
import logging
import asyncio
import time
import numpy as np
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from .config import get_config
from nextalk_shared.constants import (
    FUNASR_OFFLINE_MODEL,
    FUNASR_ONLINE_MODEL,
    FUNASR_VAD_MODEL,
    FUNASR_PUNC_MODEL,
    FUNASR_MODEL_REVISION,
    FUNASR_DISABLE_LOG,
    FUNASR_DISABLE_PBAR
)

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.funasr_model")

# 异步执行器 - 用于在不阻塞事件循环的情况下运行FunASR模型
_executor = ThreadPoolExecutor(max_workers=2)

# 检查FunASR是否可用
try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except ImportError:
    logger.warning("FunASR模块不可用，请安装FunASR依赖")
    FUNASR_AVAILABLE = False


class FunASRModel:
    """FunASR模型封装类，提供语音识别功能"""
    
    def __init__(self, config):
        """
        初始化FunASR模型
        
        Args:
            config: 模型配置
        """
        self.config = config
        self._initialized = False
        self._model_asr = None         # 离线ASR模型
        self._model_asr_streaming = None  # 在线ASR模型
        self._model_vad = None         # VAD模型
        self._model_punc = None        # 标点模型
        
        # ASR状态字典（stream模式）
        self.status_dict_asr_online = {"cache": {}, "is_final": False}
        
        # 标点模型状态字典
        self.status_dict_punc = {"cache": {}}
        
        # 创建临时目录
        os.makedirs(getattr(config, 'temp_dir', '/tmp/nextalk'), exist_ok=True)
        
        # 使用线程执行初始化，不阻塞主线程
        threading.Thread(target=self._init_model_sync).start()
    
    def _init_model_sync(self):
        """同步方式初始化模型（在单独线程中运行）"""
        try:
            logger.info("开始初始化FunASR模型...")
            start_time = time.time()
            
            # 获取基本配置
            ngpu = getattr(self.config, "ngpu", 1)
            ncpu = getattr(self.config, "ncpu", 4)
            device = getattr(self.config, "device", "cuda")
            
            # 通用参数，与官方示例保持一致
            common_params = {
                "ngpu": ngpu,
                "ncpu": ncpu,
                "device": device,
                "disable_pbar": FUNASR_DISABLE_PBAR,
                "disable_log": FUNASR_DISABLE_LOG
            }
            
            # 离线ASR模型
            asr_model = getattr(self.config, "asr_model", FUNASR_OFFLINE_MODEL)
            asr_model_revision = getattr(self.config, "asr_model_revision", FUNASR_MODEL_REVISION)
            if asr_model:
                logger.info(f"加载离线ASR模型: {asr_model}")
                self._model_asr = AutoModel(
                    model=asr_model,
                    model_revision=asr_model_revision,
                    **common_params
                )
            
            # 在线ASR模型
            asr_model_streaming = getattr(self.config, "asr_model_streaming", FUNASR_ONLINE_MODEL)
            asr_model_streaming_revision = getattr(self.config, "asr_model_streaming_revision", FUNASR_MODEL_REVISION)
            if asr_model_streaming:
                logger.info(f"加载在线ASR模型: {asr_model_streaming}")
                self._model_asr_streaming = AutoModel(
                    model=asr_model_streaming,
                    model_revision=asr_model_streaming_revision,
                    **common_params
                )
            
            # VAD模型
            vad_model = getattr(self.config, "vad_model", FUNASR_VAD_MODEL)
            vad_model_revision = getattr(self.config, "vad_model_revision", FUNASR_MODEL_REVISION)
            if vad_model:
                logger.info(f"加载VAD模型: {vad_model}")
                self._model_vad = AutoModel(
                    model=vad_model,
                    model_revision=vad_model_revision,
                    **common_params
                )
                
            # 标点模型
            punc_model = getattr(self.config, "punc_model", FUNASR_PUNC_MODEL)
            punc_model_revision = getattr(self.config, "punc_model_revision", FUNASR_MODEL_REVISION)
            if punc_model:
                logger.info(f"加载标点模型: {punc_model}")
                self._model_punc = AutoModel(
                    model=punc_model,
                    model_revision=punc_model_revision,
                    **common_params
                )
            else:
                self._model_punc = None
            
            self._initialized = True
            elapsed_time = time.time() - start_time
            logger.info(f"FunASR模型初始化完成，耗时: {elapsed_time:.2f}秒")
        except Exception as e:
            logger.error(f"初始化FunASR模型失败: {str(e)}")
            logger.exception(e)
            self._initialized = False
    
    async def initialize(self) -> bool:
        """
        为兼容现有代码提供的初始化方法
        
        Returns:
            bool: 模型是否成功初始化
        """
        # 如果已经初始化完成，直接返回成功
        if self._initialized:
            logger.info("模型已初始化完成")
            return True
            
        # 等待初始化完成或超时
        start_time = time.time()
        timeout = 60  # 最多等待60秒
        
        while not self._initialized and time.time() - start_time < timeout:
            logger.debug("等待模型初始化完成...")
            await asyncio.sleep(0.5)
            
        if self._initialized:
            logger.info("模型初始化完成")
            return True
        else:
            logger.error("模型初始化超时或失败")
            return False
    
    async def process_audio_chunk(self, audio_data: bytes, is_final: bool = False) -> Dict[str, Any]:
        """
        处理音频数据块
        
        Args:
            audio_data: 音频数据（PCM格式）
            is_final: 是否为最后一帧
            
        Returns:
            Dict[str, Any]: 识别结果
        """
        if not self._initialized:
            logger.error("模型未初始化，无法处理音频")
            return {"error": "模型未初始化，服务器可能启动不正确", "text": ""}
        
        try:
            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._process_audio_sync,
                audio_data,
                is_final
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理音频出错: {str(e)}")
            return {"error": str(e), "text": ""}
    
    def _process_audio_sync(self, audio_data: bytes, is_final: bool) -> Dict[str, Any]:
        """
        同步处理音频数据
        
        Args:
            audio_data: 音频数据
            is_final: 是否为最后一帧
            
        Returns:
            Dict[str, Any]: 识别结果
        """
        try:
            config = get_config()
            mode = "2pass"  # 默认使用2pass模式
            
            # 将音频数据转换为NumPy数组
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 获取模型实例
            if not self._model_asr_streaming or not self._model_asr:
                return {"text": "", "error": "模型未加载"}
            
            result = {}
            # 添加识别模式
            result["mode"] = mode
            
            if mode == "online" or mode == "2pass":
                # 初始化状态字典，如果为None
                if not hasattr(self, 'status_dict_asr_online') or self.status_dict_asr_online is None:
                    self.status_dict_asr_online = {"cache": {}, "is_final": False}
                
                # 确保cache键存在
                if "cache" not in self.status_dict_asr_online:
                    self.status_dict_asr_online["cache"] = {}
                
                # 设置is_final状态 - 但不会在流式处理时设置
                if is_final:
                    self.status_dict_asr_online["is_final"] = is_final
                    logger.debug("标记为最终帧")
                
                # 安全获取cache
                cache = self.status_dict_asr_online.get("cache", {})
                
                # 使用在线模型进行识别（流式）
                try:
                    logger.debug(f"使用在线模型处理音频，音频长度: {len(audio_np)}，是否最终: {is_final}")
                    logger.debug(f"cache类型: {type(cache)}, cache为空: {not bool(cache)}")
                    
                    # 检查音频数据长度，避免处理空数据
                    if len(audio_np) == 0:
                        logger.warning("在线模型收到空音频数据，跳过处理")
                        result["text"] = ""
                        result["error"] = "空音频数据"
                        result["is_final"] = is_final
                        return result
                    
                    # 把is_final信息也传递给模型 - 仅在真正结束时
                    online_result = self._model_asr_streaming.generate(
                        input=audio_np, 
                        cache=cache,
                        is_final=is_final
                    )
                    
                    # 处理返回结果，处理列表类型的结果
                    if isinstance(online_result, list):
                        if len(online_result) > 0:
                            if isinstance(online_result[0], dict) and "text" in online_result[0]:
                                # 获取文本并处理重复
                                online_text = online_result[0]["text"]
                                online_text = self._remove_duplicates(online_text)
                                result["text"] = online_text
                                
                                # 当结果是列表而不是字典时，处理缓存
                                if is_final:
                                    # 仅在最终帧时重置缓存
                                    logger.info("最终帧处理完成，重置缓存")
                                    self.status_dict_asr_online["cache"] = {}
                            else:
                                result["text"] = str(online_result[0])
                        else:
                            result["text"] = ""
                            logger.warning("在线模型返回空列表结果")
                    # 原来的字典类型处理
                    elif isinstance(online_result, dict) and "text" in online_result:
                        # 获取文本并处理重复
                        online_text = online_result["text"]
                        online_text = self._remove_duplicates(online_text)
                        result["text"] = online_text
                        
                        # 安全更新在线模型状态
                        if "cache" in online_result:
                            # 更新缓存，但不重置
                            self.status_dict_asr_online["cache"] = online_result["cache"]
                            if is_final:
                                # 仅在最终帧时重置缓存
                                logger.info("最终帧处理完成，重置缓存")
                                self.status_dict_asr_online["cache"] = {}
                    else:
                        logger.warning(f"在线模型结果格式异常: {type(online_result)}")
                        result["text"] = ""
                    
                    # 设置结果的最终状态 - 通常不会在流式处理中设置为final
                    result["is_final"] = is_final
                    
                except Exception as e:
                    logger.error(f"在线模型处理错误: {str(e)}")
                    result["text"] = ""
                    result["error"] = f"在线模型处理错误: {str(e)}"
            
            # 离线模型处理 - 仅在最终帧时执行
            if (mode == "offline" or mode == "2pass") and is_final:
                try:
                    # 检查音频数据长度，避免处理空数据
                    if len(audio_np) == 0:
                        logger.warning("离线模型收到空音频数据，跳过处理")
                        if "text" not in result:
                            result["text"] = ""
                        result["error_offline"] = "空音频数据"
                        result["is_final"] = True
                        return result
                        
                    # 确保音频数据是float32类型，避免"normal_kernel_cpu" not implemented for 'Short'错误
                    audio_float = audio_np.astype(np.float32) / 32768.0  # 转换为float32并归一化到[-1,1]
                    
                    logger.info("使用离线模型处理最终音频...")
                    # 使用离线模型进行识别（更高精度，仅在最后一帧使用）
                    offline_result = self._model_asr.generate(input=audio_float)
                    
                    # 安全获取文本
                    offline_text = ""
                    if isinstance(offline_result, dict) and "text" in offline_result:
                        offline_text = offline_result["text"]
                    elif isinstance(offline_result, list):
                        # 如果结果是列表，检查列表是否为空
                        if len(offline_result) > 0:
                            # 尝试获取第一个元素
                            if isinstance(offline_result[0], dict) and "text" in offline_result[0]:
                                offline_text = offline_result[0]["text"]
                            else:
                                offline_text = str(offline_result[0])
                        else:
                            logger.warning("离线模型返回空列表结果")
                    else:
                        logger.warning(f"离线模型结果格式异常: {type(offline_result)}")
                    
                    # 处理可能的重复字词问题
                    offline_text = self._remove_duplicates(offline_text)
                    
                    if mode == "2pass":
                        # 2pass模式：如果离线模型有结果，使用离线模型结果
                        if offline_text.strip():
                            logger.info(f"离线模型最终结果: {offline_text}")
                            result["text"] = offline_text
                    else:
                        # 离线模式：直接使用离线模型结果
                        result["text"] = offline_text
                        
                    # 设置最终标志
                    result["is_final"] = True
                    
                except Exception as e:
                    logger.error(f"离线模型处理错误: {str(e)}")
                    # 不覆盖在线模型的结果
                    if "text" not in result:
                        result["text"] = ""
                    result["error_offline"] = f"离线模型处理错误: {str(e)}"
            
            return result
            
        except Exception as e:
            logger.error(f"同步处理音频时出错: {str(e)}")
            return {"text": "", "error": str(e)}
    
    def _remove_duplicates(self, text: str) -> str:
        """
        移除文本中的重复片段，更强大的版本
        
        Args:
            text: 输入文本
            
        Returns:
            移除重复后的文本
        """
        if not text:
            return text
            
        # 1. 简单重复字符去重
        result = []
        prev_char = None
        repeat_count = 0
        max_repeats = 2  # 允许最多重复次数
        
        for char in text:
            if char == prev_char:
                repeat_count += 1
                if repeat_count < max_repeats:
                    result.append(char)
            else:
                result.append(char)
                prev_char = char
                repeat_count = 0
                
        # 2. 处理重复双字词，如"你好你好"
        text = ''.join(result)
        for length in range(4, 1, -1):  # 从长到短处理，避免处理子串
            i = 0
            while i <= len(text) - length * 2:
                chunk1 = text[i:i+length]
                chunk2 = text[i+length:i+length*2]
                if chunk1 == chunk2:
                    # 找到重复，去除第二个重复部分
                    text = text[:i+length] + text[i+length*2:]
                else:
                    i += 1
                    
        # 3. 过滤掉常见噪音词
        noise_words = ["嗯", "啊", "呃", "额"]
        for word in noise_words:
            if len(text) > 4:  # 只在较长文本中过滤噪音词，避免过度过滤
                text = text.replace(word, "")
                
        return text.strip()
    
    async def reset(self) -> None:
        """
        重置模型状态
        """
        # 完全重置在线状态字典，确保缓存是空的
        self.status_dict_asr_online = {"cache": {}, "is_final": True}
        self.status_dict_punc = {"cache": {}}
        
        # 确保再次明确清空缓存
        if hasattr(self, 'status_dict_asr_online'):
            self.status_dict_asr_online["cache"] = {}
            self.status_dict_asr_online["is_final"] = True
        
        if hasattr(self, 'status_dict_punc'):
            self.status_dict_punc["cache"] = {}
            
        logger.info("已重置模型状态和所有缓存")
    
    async def release(self) -> None:
        """
        释放模型资源
        """
        self._model_asr = None
        self._model_asr_streaming = None
        self._model_vad = None
        self._model_punc = None
        self._initialized = False
        logger.info("已释放模型资源")
    
    async def process_vad(self, audio_data: bytes, status_dict=None) -> Dict[str, Any]:
        """
        处理VAD音频检测
        
        Args:
            audio_data: 音频数据（PCM格式）
            status_dict: VAD处理状态字典
            
        Returns:
            Dict[str, Any]: VAD检测结果
        """
        if not self._initialized:
            logger.error("模型未初始化，无法处理VAD")
            return {"error": "模型未初始化", "segments": []}
        
        # 确保VAD模型可用
        if not hasattr(self, '_model_vad') or self._model_vad is None:
            logger.warning("VAD模型未加载，使用内置VAD代替")
            return await self._process_vad_fallback(audio_data, status_dict)
        
        try:
            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._process_vad_sync,
                audio_data,
                status_dict or {}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理VAD出错: {str(e)}")
            return {"error": str(e), "segments": []}
            
    def _process_vad_sync(self, audio_data: bytes, status_dict: Dict) -> Dict[str, Any]:
        """
        同步处理VAD
        
        Args:
            audio_data: 音频数据
            status_dict: VAD处理状态字典
            
        Returns:
            Dict[str, Any]: VAD检测结果
        """
        try:
            # 确保status_dict包含cache
            if not status_dict:
                status_dict = {"cache": {}, "is_final": False}
            elif "cache" not in status_dict:
                status_dict["cache"] = {}
            
            # 将音频数据转换为NumPy数组
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 使用VAD模型进行检测
            vad_result = self._model_vad.generate(input=audio_np, **status_dict)
            
            # 解析结果
            if isinstance(vad_result, list) and len(vad_result) > 0:
                segments = []
                
                # 获取第一个元素
                first_result = vad_result[0]
                
                # 处理不同格式的结果
                if "value" in first_result:
                    segments = first_result["value"]
                elif isinstance(first_result, list):
                    segments = first_result
                
                # 返回结果
                return {
                    "segments": segments,
                    "cache": status_dict.get("cache", {})
                }
            else:
                return {"segments": [], "cache": status_dict.get("cache", {})}
                
        except Exception as e:
            logger.error(f"VAD处理出错: {str(e)}")
            return {"error": str(e), "segments": []}
    
    async def _process_vad_fallback(self, audio_data: bytes, status_dict=None) -> Dict[str, Any]:
        """
        当FunASR VAD模型不可用时的后备VAD处理
        
        Args:
            audio_data: 音频数据
            status_dict: VAD处理状态字典
            
        Returns:
            Dict[str, Any]: VAD检测结果
        """
        try:
            # 直接分析音频数据而不是使用VADFilter类
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 计算一些基本的音频特征
            amplitude = np.abs(audio_np)
            max_amp = np.max(amplitude)
            non_zero = np.count_nonzero(audio_np)
            non_zero_ratio = non_zero / len(audio_np) if len(audio_np) > 0 else 0
            
            # 简单规则判断是否有语音
            # 如果振幅大于一定阈值并且非零比例较高，则认为是语音
            is_speech = max_amp > 500 and non_zero_ratio > 0.3
            
            # 处理结果
            if is_speech:
                # 检测到语音
                speech_start = 0  # 假设从开始就是语音
                speech_end = -1   # 未检测到结束
                logger.debug(f"后备VAD检测到语音: 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}")
                return {"segments": [[speech_start, speech_end]], "cache": {}}
            else:
                # 没有检测到语音
                logger.debug(f"后备VAD未检测到语音: 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}")
                return {"segments": [], "cache": {}}
                
        except Exception as e:
            logger.error(f"后备VAD处理出错: {str(e)}")
            return {"error": str(e), "segments": []}
            
    async def process_audio_offline(self, audio_data: bytes) -> Dict[str, Any]:
        """
        处理离线音频数据
        
        Args:
            audio_data: 音频数据（PCM格式）
            
        Returns:
            Dict[str, Any]: 离线识别结果
        """
        if not self._initialized:
            logger.error("模型未初始化，无法处理离线音频")
            return {"error": "模型未初始化", "text": ""}
        
        try:
            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._process_audio_offline_sync,
                audio_data
            )
            
            return result
            
        except Exception as e:
            logger.error(f"处理离线音频出错: {str(e)}")
            return {"error": str(e), "text": ""}
            
    def _process_audio_offline_sync(self, audio_data: bytes) -> Dict[str, Any]:
        """
        同步处理离线音频数据
        
        Args:
            audio_data: 音频数据
            
        Returns:
            Dict[str, Any]: 离线识别结果
        """
        try:
            # 确保离线模型可用
            if not self._model_asr:
                return {"text": "", "error": "离线模型未加载"}
            
            # 将音频数据转换为NumPy数组
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 检查音频数据长度
            if len(audio_np) == 0:
                logger.warning("离线模型收到空音频数据，跳过处理")
                return {"text": "", "error": "空音频数据"}
            
            # 确保音频数据是float32类型
            audio_float = audio_np.astype(np.float32) / 32768.0  # 转换为float32并归一化到[-1,1]
            
            logger.info("使用离线模型处理音频...")
            
            # 使用离线模型进行识别
            asr_result = self._model_asr.generate(input=audio_float)
            
            # 提取文本结果
            if isinstance(asr_result, list):
                if len(asr_result) == 0:
                    return {"text": "", "error": "空结果"}
                
                if isinstance(asr_result[0], dict) and "text" in asr_result[0]:
                    text = asr_result[0]["text"]
                else:
                    text = str(asr_result[0])
            
            elif isinstance(asr_result, dict) and "text" in asr_result:
                text = asr_result["text"]
            else:
                logger.warning(f"未知的结果格式: {type(asr_result)}")
                return {"text": "", "error": "未知的结果格式"}
            
            # 处理文本中的重复内容
            text = self._remove_duplicates(text)
            
            return {
                "text": text,
                "is_final": True,
                "mode": "offline"
            }
            
        except Exception as e:
            logger.error(f"离线音频处理出错: {str(e)}")
            return {"text": "", "error": str(e)} 