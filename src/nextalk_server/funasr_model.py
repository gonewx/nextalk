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

# 预加载的模型实例
_PRELOADED_MODEL = None

# 检查FunASR是否可用
try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except ImportError:
    logger.warning("FunASR模块不可用，请安装FunASR依赖")
    FUNASR_AVAILABLE = False


def set_preloaded_model(model):
    """
    设置预加载的模型实例到全局变量
    
    Args:
        model: 预加载的FunASRModel实例
    """
    global _PRELOADED_MODEL
    _PRELOADED_MODEL = model
    logger.info("已设置预加载模型实例到全局变量")


def get_preloaded_model():
    """
    获取预加载的模型实例
    
    Returns:
        FunASRModel或None: 预加载的模型实例，如果没有则返回None
    """
    return _PRELOADED_MODEL


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
        
        # 离线ASR状态字典
        self.status_dict_asr = {}
        
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
                
                # 预热离线ASR模型
                logger.info("预热离线ASR模型...")
                try:
                    # 创建一个短的测试音频数据 (16kHz, 16位, 100ms)
                    test_audio = np.zeros(1600, dtype=np.int16).tobytes()
                    self._model_asr.generate(input=test_audio, **self.status_dict_asr)
                    logger.info("离线ASR模型预热完成")
                except Exception as e:
                    logger.warning(f"离线ASR模型预热失败: {str(e)}")
            
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
                
                # 预热在线ASR模型
                logger.info("预热在线ASR模型...")
                try:
                    test_audio = np.zeros(1600, dtype=np.int16)
                    self._model_asr_streaming.generate(
                        input=test_audio, 
                        cache=self.status_dict_asr_online.get("cache", {})
                    )
                    logger.info("在线ASR模型预热完成")
                except Exception as e:
                    logger.warning(f"在线ASR模型预热失败: {str(e)}")
            
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
                
                # 预热VAD模型
                logger.info("预热VAD模型...")
                try:
                    test_audio = np.zeros(1600, dtype=np.int16).tobytes()
                    vad_status = {"cache": {}, "is_final": False}
                    self._model_vad.generate(input=test_audio, **vad_status)
                    logger.info("VAD模型预热完成")
                except Exception as e:
                    logger.warning(f"VAD模型预热失败: {str(e)}")
                
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
                
                # 预热标点模型，避免懒加载
                logger.info("预热标点模型，避免懒加载...")
                try:
                    # 使用简单文本触发模型真正加载
                    test_text = "测试句子预热标点模型"
                    self._model_punc.generate(input=test_text, **self.status_dict_punc)
                    logger.info("标点模型预热完成")
                except Exception as e:
                    logger.warning(f"标点模型预热失败: {str(e)}")
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
        处理音频块数据（流式）
        
        Args:
            audio_data: 音频数据（PCM格式）
            is_final: 是否为最终帧
            
        Returns:
            Dict[str, Any]: 识别结果
        """
        if not self._initialized:
            logger.error("模型未初始化，无法处理音频块")
            return {"error": "模型未初始化"}
        
        try:
            # 检查音频数据
            if not audio_data or len(audio_data) == 0:
                logger.warning("收到空音频数据")
                return {"text": "", "error": "空音频数据"}
            
            # 在线程池中处理音频，避免阻塞
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._process_audio_sync,
                audio_data,
                is_final
            )
            
            # 为结果添加额外信息
            if "error" not in result:
                result["timestamp"] = int(time.time())
                
            return result
            
        except Exception as e:
            logger.error(f"处理音频块出错: {str(e)}")
            return {"error": str(e), "text": ""}
    
    def _process_audio_sync(self, audio_data: bytes, is_final: bool) -> Dict[str, Any]:
        """
        同步处理音频数据
        
        Args:
            audio_data: 音频数据
            is_final: 是否最终帧
            
        Returns:
            Dict[str, Any]: 识别结果
        """
        # 检查模型是否可用
        if not FUNASR_AVAILABLE or not self._model_asr_streaming:
            logger.error("FunASR在线模型不可用")
            return {"error": "FunASR在线模型不可用"}
        
        try:
            # 将二进制音频数据转换为NumPy数组
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # 直接使用状态字典中的参数，不做手动修改
            if "chunk_size" not in self.status_dict_asr_online:
                # 设置默认值 [5, 10, 5] 与官方示例一致
                self.status_dict_asr_online["chunk_size"] = [5, 10, 5]
            
            # 使用在线ASR模型处理音频
            start_time = time.time()
            
            # 调用FunASR模型
            # 注意：这里使用了**self.status_dict_asr_online将所有状态参数传递给模型
            # 包括cache, is_final, chunk_size及其他可能的参数
            result = self._model_asr_streaming.generate(
                input=audio_np,
                **self.status_dict_asr_online
            )
            
            process_time = time.time() - start_time
            logger.debug(f"在线ASR处理耗时: {process_time:.3f}秒, 第一层结果类型: {type(result)}")
            
            # 更新缓存状态
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "cache" in result[0]:
                    self.status_dict_asr_online["cache"] = result[0].get("cache", {})
                
                # 提取文本结果
                text = ""
                if isinstance(result[0], dict) and "text" in result[0]:
                    text = result[0].get("text", "")
                elif isinstance(result[0], str):
                    text = result[0]
                
                return {"text": text}
            
            # 处理空结果或异常格式
            logger.warning(f"无法解析在线ASR结果: {result}")
            return {"text": ""}
            
        except Exception as e:
            logger.error(f"处理在线音频出错: {str(e)}")
            print(f"处理在线音频出错: {str(e)}", flush=True)
            return {"error": str(e)}
    
    async def reset(self) -> None:
        """
        重置模型状态
        """
        try:
            # 完全重置在线状态字典
            self.status_dict_asr_online = {"cache": {}, "is_final": True}
            
            # 重置标点状态字典
            self.status_dict_punc = {"cache": {}}
            
            # 重置离线ASR状态字典 - 完全清空
            self.status_dict_asr = {}
            
            # 记录日志
            logger.info("已重置模型状态和所有缓存")
        except Exception as e:
            logger.error(f"重置模型状态时出错: {str(e)}")
            logger.exception(e)
    
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
        
        # 确保状态字典包含必要的字段
        if status_dict is None:
            status_dict = {"cache": {}}
        elif "cache" not in status_dict:
            status_dict["cache"] = {}
        
        # 打印VAD状态字典（debug）
        print(f"VAD状态字典: {status_dict.keys()}, cache是否为空: {not bool(status_dict.get('cache'))}", flush=True)
        
        try:
            # 计算音频基本特征用于调试
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            max_amp = np.max(np.abs(audio_np)) if len(audio_np) > 0 else 0
            
            print(f"VAD输入数据: 长度={len(audio_np)}样本, 最大振幅={max_amp}", flush=True)
            
            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                self._process_vad_sync,
                audio_data,
                status_dict or {}
            )
            
            # 调试输出VAD结果
            if "segments" in result and result["segments"]:
                print(f"VAD返回语音段: {result['segments']}", flush=True)
            else:
                print(f"VAD未检测到语音段", flush=True)
                
            return result
            
        except Exception as e:
            logger.error(f"处理VAD出错: {str(e)}")
            print(f"处理VAD出错: {str(e)}", flush=True)
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
            # 添加chunk_size参数，与官方示例一致（每60秒检测一次）
            if "chunk_size" not in status_dict:
                # 使用默认参数
                vad_result = self._model_vad.generate(input=audio_np, **status_dict)
            else:
                # 使用传入的参数
                vad_result = self._model_vad.generate(input=audio_np, **status_dict)
            
            # 解析结果
            if isinstance(vad_result, list) and len(vad_result) > 0:
                segments = []
                
                # 获取第一个元素
                first_result = vad_result[0]
                
                # 处理不同格式的结果
                if "value" in first_result:
                    segments = first_result["value"]
                    print(f"VAD结果使用value字段: {segments}", flush=True)
                elif isinstance(first_result, list):
                    segments = first_result
                    print(f"VAD结果是列表类型: {segments}", flush=True)
                else:
                    print(f"VAD结果格式异常: {type(first_result)}", flush=True)
                
                # 检查segments内容并打印
                if segments:
                    print(f"VAD检测到语音段: {segments}", flush=True)
                else:
                    print("VAD返回空segments列表", flush=True)
                
                # 更新cache并返回
                if "cache" in status_dict:
                    # 返回结果
                    return {
                        "segments": segments,
                        "cache": status_dict.get("cache", {})
                    }
            
            # 默认结果 - 无语音段
            return {"segments": [], "cache": status_dict.get("cache", {})}
                
        except Exception as e:
            logger.error(f"VAD处理出错: {str(e)}")
            print(f"VAD同步处理异常: {str(e)}", flush=True)
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
        # 检查初始化状态，如果未初始化则等待
        if not self._initialized:
            logger.warning("模型尚未初始化完成，等待初始化...")
            timeout = 60  # 最多等待60秒
            start_time = time.time()
            
            while not self._initialized and time.time() - start_time < timeout:
                await asyncio.sleep(0.5)
                
            if not self._initialized:
                logger.error("模型未初始化，超时等待，无法处理离线音频")
                return {"error": "模型未初始化，超时等待", "text": ""}
            
            logger.info("模型初始化已完成，继续处理离线音频")
        
        try:
            # 记录音频基本信息
            logger.info(f"准备离线处理音频数据，长度: {len(audio_data)} 字节")
            
            # 确保状态字典初始化
            if not hasattr(self, 'status_dict_asr') or self.status_dict_asr is None:
                self.status_dict_asr = {}
                logger.debug("重新初始化离线ASR状态字典")
                
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
            logger.exception(e)
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
            logger.info("准备离线处理音频数据，长度: {0} 字节".format(len(audio_data)))
            
            # 检查音频数据长度，避免处理空数据
            if len(audio_data) == 0:
                logger.warning("离线模型收到空音频数据，跳过处理")
                return {"text": "", "error": "空音频数据"}
                
            # 将音频数据转换为NumPy数组用于分析
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            samples = len(audio_np)
            duration_s = samples / 16000
            
            logger.info(f"离线处理音频: 长度={samples}样本，{duration_s:.3f}秒")
            
            # 确保状态字典已初始化
            if not hasattr(self, 'status_dict_asr') or self.status_dict_asr is None:
                self.status_dict_asr = {}
            
            # 如果在线ASR配置中有这些参数，复用它们
            if hasattr(self, 'status_dict_asr_online'):
                if "encoder_chunk_look_back" in self.status_dict_asr_online:
                    self.status_dict_asr["encoder_chunk_look_back"] = self.status_dict_asr_online["encoder_chunk_look_back"]
                    logger.debug(f"离线ASR使用encoder_chunk_look_back={self.status_dict_asr['encoder_chunk_look_back']}")
                
                if "decoder_chunk_look_back" in self.status_dict_asr_online:
                    self.status_dict_asr["decoder_chunk_look_back"] = self.status_dict_asr_online["decoder_chunk_look_back"]
                    logger.debug(f"离线ASR使用decoder_chunk_look_back={self.status_dict_asr['decoder_chunk_look_back']}")
            
            # 使用离线模型处理
            logger.info("使用离线模型处理最终音频...")
            
            # 标记是否使用了标点模型
            used_punctuation = False
            original_text = ""
                
            try:
                # 调用离线ASR模型
                print("调用离线ASR模型...", flush=True)
                offline_result = self._model_asr.generate(
                    input=audio_data,  # 使用原始字节数据
                    **self.status_dict_asr
                )
                
                # 获取ASR结果
                if isinstance(offline_result, list) and len(offline_result) > 0:
                    first_result = offline_result[0]
                    
                    # 获取文本结果
                    if isinstance(first_result, dict) and "text" in first_result:
                        offline_text = first_result["text"]
                    elif isinstance(first_result, str):
                        offline_text = first_result
                    else:
                        offline_text = str(first_result)
                        
                    # 保存原始文本结果
                    original_text = offline_text
                    print(f"【重要调试信息】离线ASR原始结果 (标点处理前): '{offline_text}'", flush=True)
                    logger.info(f"离线ASR原始结果 (标点处理前): '{offline_text}'")
                    
                    # 应用标点模型（如果有）
                    if self._model_punc is not None and offline_text.strip():
                        try:
                            print("应用标点模型...", flush=True)
                            punc_result = self._model_punc.generate(
                                input=offline_text,
                                **self.status_dict_punc
                            )
                            
                            if isinstance(punc_result, list) and len(punc_result) > 0:
                                if isinstance(punc_result[0], dict) and "text" in punc_result[0]:
                                    offline_text = punc_result[0]["text"]
                                elif isinstance(punc_result[0], str):
                                    offline_text = punc_result[0]
                            
                            logger.info(f"已应用标点模型，结果: {offline_text}")
                            print(f"【重要调试信息】已应用标点模型，结果: '{offline_text}'", flush=True)
                            used_punctuation = True
                            
                            # 如果标点前后文本有明显差异，记录下来
                            if original_text and original_text != offline_text:
                                diff_ratio = abs(len(original_text) - len(offline_text)) / max(len(original_text), len(offline_text))
                                if diff_ratio > 0.3:  # 差异超过30%
                                    logger.info(f"标点处理前后的文本差异较大: '{original_text}' -> '{offline_text}'")
                                    print(f"【重要调试信息】标点处理前后的文本差异较大: '{original_text}' -> '{offline_text}'", flush=True)
                                    
                        except Exception as e:
                            logger.warning(f"标点模型处理失败，使用原始文本: {str(e)}")
                    
                    logger.info(f"离线模型最终结果: {offline_text}")
                    print(f"【重要调试信息】离线模型最终结果: '{offline_text}'", flush=True)
                    
                    # 构造结果
                    result = {"text": offline_text}
                    
                    # 如果使用了标点模型，并且有原始文本，也返回原始文本
                    if used_punctuation and original_text:
                        result["original_text"] = original_text
                        
                    return result
                else:
                    logger.warning("离线ASR模型未返回有效结果")
                    return {"text": "", "error": "未获取到有效结果"}
                
            except Exception as e:
                logger.error(f"离线ASR处理出错: {str(e)}")
                return {"text": "", "error": str(e)}
                
        except Exception as e:
            logger.error(f"离线音频处理出错: {str(e)}")
            logger.exception(e)
            return {"text": "", "error": str(e)} 