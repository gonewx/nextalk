"""
NexTalk ASR (语音识别) 识别器模块。

该模块定义了ASR识别器类，用于处理音频数据并生成文本转录。
使用faster_whisper库加载和运行Whisper模型。
"""

import logging
import numpy as np
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from faster_whisper import WhisperModel

# 设置日志记录器
logger = logging.getLogger(__name__)


class ASRRecognizer:
    """
    自动语音识别(ASR)处理器类。
    
    该类负责接收音频数据并将其转换为文本。
    使用faster-whisper模型进行实际的语音识别。
    """
    
    def __init__(
        self,
        model_size: str = "small.en-int8",
        model_path: str = "~/.cache/NexTalk/models",
        device: str = "cuda",
        compute_type: str = "int8"
    ):
        """
        初始化ASR识别器，加载Whisper模型。
        
        Args:
            model_size: Whisper模型大小，如"tiny.en"、"small.en-int8"等
            model_path: 模型文件存储路径
            device: 计算设备，"cuda"用于GPU，"cpu"用于CPU
            compute_type: 计算类型，如"int8"、"float16"等
        """
        self.model_size = model_size
        self.model_path = os.path.expanduser(model_path)
        self.device = device
        self.compute_type = compute_type
        
        logger.info(
            f"初始化ASR识别器: model_size={model_size}, device={device}, "
            f"compute_type={compute_type}, model_path={self.model_path}"
        )
        
        # 确保模型缓存目录存在
        os.makedirs(self.model_path, exist_ok=True)
        
        try:
            # 加载Whisper模型
            self.model = WhisperModel(
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.model_path
            )
            logger.info(f"成功加载Whisper模型: {self.model_size}")
        except Exception as e:
            logger.error(f"加载Whisper模型时出错: {str(e)}")
            raise RuntimeError(f"无法加载Whisper模型: {str(e)}")
    
    def transcribe(self, audio_chunk: np.ndarray) -> str:
        """
        将音频数据转换为文本。
        
        使用Whisper模型处理音频数据并返回转录结果。
        
        Args:
            audio_chunk: 包含音频数据的NumPy数组，预期为float32类型
            
        Returns:
            转录的文本字符串
        
        Raises:
            RuntimeError: 当转录过程中发生错误时
        """
        if self.model is None:
            error_msg = "Whisper模型未加载，无法进行转录"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # 记录接收到的音频块信息
        logger.info(
            f"收到音频块进行转录: shape={audio_chunk.shape}, "
            f"dtype={audio_chunk.dtype}, mean={audio_chunk.mean():.4f}, "
            f"std={audio_chunk.std():.4f}"
        )
        
        try:
            # 确保音频数据类型为float32
            if audio_chunk.dtype != np.float32:
                logger.warning(f"音频数据类型不是float32，正在转换: {audio_chunk.dtype} -> float32")
                audio_chunk = audio_chunk.astype(np.float32)
            
            # 使用Whisper模型进行转录
            # beam_size: 搜索宽度，更大的值可能提高准确性，但会增加处理时间
            # language: 可以设置为None进行自动检测，或指定语言代码如"en"
            # task: 默认为"transcribe"，可以是"translate"将非英语音频翻译为英语
            segments, info = self.model.transcribe(
                audio_chunk,
                beam_size=5,
                language=None,  # 自动检测语言
                task="transcribe",
                vad_filter=True,  # 使用VAD过滤静音部分
                vad_parameters=dict(min_silence_duration_ms=500)  # VAD参数
            )
            
            # 收集所有文本段落
            text_segments = []
            for segment in segments:
                text_segments.append(segment.text)
            
            # 合并所有文本段落
            full_text = " ".join(text_segments).strip()
            
            logger.info(f"转录成功: '{full_text}'")
            logger.debug(f"转录详情: 检测到的语言={info.language}, "
                         f"语言概率={info.language_probability:.4f}, "
                         f"检测到的段落数={len(text_segments)}")
            
            return full_text
            
        except Exception as e:
            error_msg = f"转录过程中出错: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def unload_model(self) -> None:
        """
        卸载当前加载的模型，释放资源。
        在切换模型或应用程序关闭时调用。
        """
        if self.model is not None:
            # 注意：faster_whisper没有显式的卸载方法
            # 我们设置为None并触发垃圾回收来释放资源
            logger.info(f"卸载Whisper模型: {self.model_size}")
            self.model = None
    
    def __del__(self):
        """析构函数，确保资源被释放"""
        self.unload_model() 