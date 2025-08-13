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
    FUNASR_DISABLE_PBAR,
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
    logger.debug("已设置预加载模型实例到全局变量")


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
        self._model_asr = None  # 离线ASR模型
        self._model_asr_streaming = None  # 在线ASR模型
        self._model_vad = None  # VAD模型
        self._model_punc = None  # 标点模型

        # ASR状态字典（stream模式）
        self.status_dict_asr_online = {"cache": {}, "is_final": False}

        # 离线ASR状态字典
        self.status_dict_asr = {}

        # 标点模型状态字典
        self.status_dict_punc = {"cache": {}}

        # 使用线程执行初始化，不阻塞主线程
        threading.Thread(target=self._init_model_sync).start()

    def _init_model_sync(self):
        """同步方式初始化模型（在单独线程中运行）"""
        try:
            logger.debug("开始初始化FunASR模型...")
            start_time = time.time()

            # 获取基本配置
            ngpu = getattr(self.config, "ngpu", 1)
            ncpu = getattr(self.config, "ncpu", 4)
            device = getattr(self.config, "device", "cuda")
            use_fp16 = getattr(self.config, "use_fp16", False)

            # 通用参数，与官方示例保持一致
            common_params = {
                "ngpu": ngpu,
                "ncpu": ncpu,
                "device": device,
                "disable_pbar": FUNASR_DISABLE_PBAR,
                "disable_log": FUNASR_DISABLE_LOG,
            }

            # 根据设备类型和配置添加精度参数
            if device.startswith("cuda") and use_fp16:
                common_params["fp16"] = True
                logger.debug("GPU模式下启用FP16精度")
            elif device == "cpu":
                # CPU模式下不使用fp16参数，保持默认FP32精度
                logger.debug("CPU模式下使用默认FP32精度")

            # 离线ASR模型
            asr_model = getattr(self.config, "asr_model", FUNASR_OFFLINE_MODEL)
            asr_model_revision = getattr(self.config, "asr_model_revision", FUNASR_MODEL_REVISION)
            if asr_model:
                logger.debug(f"加载离线ASR模型: {asr_model}")
                self._model_asr = AutoModel(
                    model=asr_model,
                    model_revision=asr_model_revision,
                    log_level="ERROR",
                    **common_params,
                )

                # 预热离线ASR模型
                logger.debug("预热离线ASR模型...")
                try:
                    # 创建一个短的测试音频数据 (16kHz, 16位, 100ms)
                    test_audio = np.zeros(1600, dtype=np.int16).tobytes()
                    self._model_asr.generate(input=test_audio, **self.status_dict_asr)
                    logger.debug("离线ASR模型预热完成")
                except Exception as e:
                    logger.warning(f"离线ASR模型预热失败: {str(e)}")

            # 在线ASR模型
            asr_model_streaming = getattr(self.config, "asr_model_streaming", FUNASR_ONLINE_MODEL)
            asr_model_streaming_revision = getattr(
                self.config, "asr_model_streaming_revision", FUNASR_MODEL_REVISION
            )
            if asr_model_streaming:
                logger.debug(f"加载在线ASR模型: {asr_model_streaming}")
                self._model_asr_streaming = AutoModel(
                    model=asr_model_streaming,
                    model_revision=asr_model_streaming_revision,
                    log_level="ERROR",
                    **common_params,
                )

                # 预热在线ASR模型
                logger.debug("预热在线ASR模型...")
                try:
                    test_audio = np.zeros(1600, dtype=np.int16)
                    self._model_asr_streaming.generate(
                        input=test_audio, cache=self.status_dict_asr_online.get("cache", {})
                    )
                    logger.debug("在线ASR模型预热完成")
                except Exception as e:
                    logger.warning(f"在线ASR模型预热失败: {str(e)}")

            # VAD模型
            vad_model = getattr(self.config, "vad_model", FUNASR_VAD_MODEL)
            vad_model_revision = getattr(self.config, "vad_model_revision", FUNASR_MODEL_REVISION)
            if vad_model:
                logger.debug(f"加载VAD模型: {vad_model}")
                self._model_vad = AutoModel(
                    model=vad_model, model_revision=vad_model_revision, **common_params
                )

                # 预热VAD模型
                logger.debug("预热VAD模型...")
                try:
                    test_audio = np.zeros(1600, dtype=np.int16).tobytes()
                    vad_status = {"cache": {}, "is_final": False}
                    self._model_vad.generate(input=test_audio, **vad_status)
                    logger.debug("VAD模型预热完成")
                except Exception as e:
                    logger.warning(f"VAD模型预热失败: {str(e)}")

            # 标点模型
            punc_model = getattr(self.config, "punc_model", FUNASR_PUNC_MODEL)
            punc_model_revision = getattr(self.config, "punc_model_revision", FUNASR_MODEL_REVISION)
            if punc_model:
                logger.debug(f"加载标点模型: {punc_model}")
                self._model_punc = AutoModel(
                    model=punc_model, model_revision=punc_model_revision, **common_params
                )

                # 预热标点模型，避免懒加载
                logger.debug("预热标点模型，避免懒加载...")
                try:
                    # 使用简单文本触发模型真正加载
                    test_text = "测试句子预热标点模型"
                    self._model_punc.generate(input=test_text, **self.status_dict_punc)
                    logger.debug("标点模型预热完成")
                except Exception as e:
                    logger.warning(f"标点模型预热失败: {str(e)}")
            else:
                self._model_punc = None

            self._initialized = True
            elapsed_time = time.time() - start_time
            logger.debug(f"FunASR模型初始化完成，耗时: {elapsed_time:.2f}秒")
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
            logger.debug("模型已初始化完成")
            return True

        # 等待初始化完成或超时
        start_time = time.time()
        timeout = 60  # 最多等待60秒

        while not self._initialized and time.time() - start_time < timeout:
            logger.debug("等待模型初始化完成...")
            await asyncio.sleep(0.5)

        if self._initialized:
            logger.debug("模型初始化完成")
            return True
        else:
            logger.error("模型初始化超时或失败")
            return False

    async def process_audio_chunk(
        self, audio_data: bytes, is_final: bool = False
    ) -> Dict[str, Any]:
        """
        处理音频数据块（流式）

        Args:
            audio_data: 音频数据
            is_final: 是否为最终块

        Returns:
            Dict[str, Any]: 处理结果
        """
        # 检查初始化状态
        if not self._initialized:
            await self.initialize()

        try:
            # 日志记录
            logger.debug(f"处理音频数据块，大小: {len(audio_data)} 字节，是否最终: {is_final}")

            # 确保状态字典正确初始化
            if not hasattr(self, "status_dict_asr_online") or self.status_dict_asr_online is None:
                self.status_dict_asr_online = {"cache": {}, "is_final": False}

            # 设置最终标志
            self.status_dict_asr_online["is_final"] = is_final

            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor, self._process_audio_sync, audio_data, is_final
            )

            # 确保文本字段存在
            if "text" not in result:
                result["text"] = ""

            return result

        except Exception as e:
            logger.error(f"处理音频数据块出错: {str(e)}")
            logger.exception(e)
            return {"error": str(e), "text": ""}

    def _process_audio_sync(self, audio_data: bytes, is_final: bool) -> Dict[str, Any]:
        """
        同步处理音频数据（在线模式）

        Args:
            audio_data: 音频数据
            is_final: 是否为最终块

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 检查音频数据是否有效
            if not audio_data or len(audio_data) == 0:
                logger.warning("收到空音频数据，跳过在线处理")
                return {"text": "", "error": "空音频数据"}

            # 确保状态字典正确初始化
            if not hasattr(self, "status_dict_asr_online") or self.status_dict_asr_online is None:
                self.status_dict_asr_online = {"cache": {}, "is_final": False}

            # 设置是否为最终状态
            self.status_dict_asr_online["is_final"] = is_final

            # 记录处理时间
            start_time = time.time()

            # 直接调用流式模型处理音频
            result = self._model_asr_streaming.generate(
                input=audio_data, **self.status_dict_asr_online
            )

            # 处理结果
            if result and isinstance(result, list) and len(result) > 0:
                first_result = result[0]

                if isinstance(first_result, dict):
                    # 构造返回结果
                    return_result = {
                        "text": first_result.get("text", ""),
                        "timestamp": int(time.time() * 1000),
                        "latency": (time.time() - start_time) * 1000,
                    }

                    # 检查标点问题
                    if return_result["text"].startswith("，") or return_result["text"].startswith(
                        ","
                    ):
                        logger.warning("流式ASR结果中检测到不合理的开头逗号，自动修复")
                        return_result["text"] = return_result["text"][1:].strip()

                    return return_result
                else:
                    # 如果结果不是预期的字典格式，尝试简单地提取文本
                    text = str(first_result)
                    if text.startswith("，") or text.startswith(","):
                        text = text[1:].strip()
                    return {
                        "text": text,
                        "timestamp": int(time.time() * 1000),
                        "latency": (time.time() - start_time) * 1000,
                    }

            return {"text": "", "timestamp": int(time.time() * 1000)}

        except Exception as e:
            logger.error(f"在线ASR处理出错: {str(e)}")
            return {"error": str(e), "text": ""}

    async def reset(self) -> None:
        """
        重置模型状态
        """
        try:
            # 完全重置在线状态字典
            self.status_dict_asr_online = {"cache": {}, "is_final": False}

            # 重置标点状态字典
            self.status_dict_punc = {"cache": {}}

            # 重置离线ASR状态字典 - 完全清空
            self.status_dict_asr = {}

            # 记录日志
            logger.debug("已重置模型状态和所有缓存")
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
        logger.debug("已释放模型资源")

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
        if not hasattr(self, "_model_vad") or self._model_vad is None:
            logger.warning("VAD模型未加载，使用内置VAD代替")
            return await self._process_vad_fallback(audio_data, status_dict)

        # 确保状态字典包含必要的字段
        if status_dict is None:
            status_dict = {"cache": {}}
        elif "cache" not in status_dict:
            status_dict["cache"] = {}

        # 打印VAD状态字典（debug）
        logger.debug(
            f"VAD状态字典: {status_dict.keys()}, cache是否为空: {not bool(status_dict.get('cache'))}"
        )

        try:
            # 计算音频基本特征用于调试
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            max_amp = np.max(np.abs(audio_np)) if len(audio_np) > 0 else 0

            logger.debug(f"VAD输入数据: 长度={len(audio_np)}样本, 最大振幅={max_amp}")

            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor, self._process_vad_sync, audio_data, status_dict or {}
            )

            # 调试输出VAD结果
            if "segments" in result and result["segments"]:
                logger.debug(f"VAD返回语音段: {result['segments']}")
            else:
                logger.debug(f"VAD未检测到语音段")

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
                    logger.debug(f"VAD结果使用value字段: {segments}")
                elif isinstance(first_result, list):
                    segments = first_result
                    logger.debug(f"VAD结果是列表类型: {segments}")
                else:
                    logger.debug(f"VAD结果格式异常: {type(first_result)}")

                # 检查segments内容并打印
                if segments:
                    logger.debug(f"VAD检测到语音段: {segments}")
                else:
                    logger.debug("VAD返回空segments列表")

                # 更新cache并返回
                if "cache" in status_dict:
                    # 返回结果
                    return {"segments": segments, "cache": status_dict.get("cache", {})}

            # 默认结果 - 无语音段
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
                speech_end = -1  # 未检测到结束
                logger.debug(
                    f"后备VAD检测到语音: 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}"
                )
                return {"segments": [[speech_start, speech_end]], "cache": {}}
            else:
                # 没有检测到语音
                logger.debug(
                    f"后备VAD未检测到语音: 最大振幅={max_amp}, 非零比例={non_zero_ratio:.4f}"
                )
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

            logger.debug("模型初始化已完成，继续处理离线音频")

        try:
            # 记录音频基本信息
            logger.debug(f"准备离线处理音频数据，长度: {len(audio_data)} 字节")

            # 确保状态字典初始化
            if not hasattr(self, "status_dict_asr") or self.status_dict_asr is None:
                self.status_dict_asr = {}
                logger.debug("重新初始化离线ASR状态字典")

            # 在线程池中处理音频，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor, self._process_audio_offline_sync, audio_data
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
            logger.debug(f"准备离线处理音频数据，长度: {len(audio_data)} 字节")

            # 检查音频数据长度，避免处理空数据
            if len(audio_data) == 0:
                logger.warning("离线模型收到空音频数据，跳过处理")
                return {"text": "", "error": "空音频数据"}

            # 将音频数据转换为NumPy数组用于分析
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            samples = len(audio_np)
            duration_s = samples / 16000

            logger.debug(f"离线处理音频: 长度={samples}样本，{duration_s:.3f}秒")

            # 确保状态字典已初始化
            if not hasattr(self, "status_dict_asr") or self.status_dict_asr is None:
                self.status_dict_asr = {}

            # 如果在线ASR配置中有这些参数，复用它们
            if hasattr(self, "status_dict_asr_online"):
                if "encoder_chunk_look_back" in self.status_dict_asr_online:
                    self.status_dict_asr["encoder_chunk_look_back"] = self.status_dict_asr_online[
                        "encoder_chunk_look_back"
                    ]
                    logger.debug(
                        f"离线ASR使用encoder_chunk_look_back={self.status_dict_asr['encoder_chunk_look_back']}"
                    )

                if "decoder_chunk_look_back" in self.status_dict_asr_online:
                    self.status_dict_asr["decoder_chunk_look_back"] = self.status_dict_asr_online[
                        "decoder_chunk_look_back"
                    ]
                    logger.debug(
                        f"离线ASR使用decoder_chunk_look_back={self.status_dict_asr['decoder_chunk_look_back']}"
                    )

            # 使用离线模型处理
            logger.debug("使用离线模型处理最终音频...")

            # 标记是否使用了标点模型
            used_punctuation = False
            original_text = ""

            try:
                # 调用离线ASR模型
                logger.debug("调用离线ASR模型...")
                offline_result = self._model_asr.generate(
                    input=audio_data,  # 使用原始字节数据
                    **self.status_dict_asr,
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
                    logger.debug(f"离线ASR原始结果 (标点处理前): '{offline_text}'")

                    # 应用标点模型（如果有）
                    if self._model_punc is not None and offline_text.strip():
                        try:
                            logger.debug("应用标点模型...")
                            punc_result = self._model_punc.generate(
                                input=offline_text, **self.status_dict_punc
                            )

                            if isinstance(punc_result, list) and len(punc_result) > 0:
                                if isinstance(punc_result[0], dict) and "text" in punc_result[0]:
                                    offline_text = punc_result[0]["text"]
                                elif isinstance(punc_result[0], str):
                                    offline_text = punc_result[0]

                            logger.debug(f"已应用标点模型，结果: {offline_text}")
                            used_punctuation = True

                            # 修复：检查并处理标点模型可能引入的开头逗号问题
                            if offline_text.startswith("，") or offline_text.startswith(","):
                                logger.warning(f"检测到标点模型添加了不合理的开头逗号，正在修复")
                                # 去除开头的逗号
                                offline_text = offline_text[1:].strip()

                            # 如果标点前后文本有明显差异，记录下来
                            if original_text and original_text != offline_text:
                                diff_ratio = abs(len(original_text) - len(offline_text)) / max(
                                    len(original_text), len(offline_text)
                                )
                                if diff_ratio > 0.3:  # 差异超过30%
                                    logger.debug(
                                        f"标点处理前后的文本差异较大: '{original_text}' -> '{offline_text}'"
                                    )

                        except Exception as e:
                            logger.warning(f"标点模型处理失败，使用原始文本: {str(e)}")

                    logger.debug(f"离线模型最终结果: {offline_text}")

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
