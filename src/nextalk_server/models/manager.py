"""
NexTalk模型管理器模块。

该模块定义了ModelManager类，用于管理语音识别模型的加载、切换和访问。
实现了模型的动态加载、卸载和切换功能。
"""

import logging
import os
import gc
from typing import Optional, Any

from faster_whisper import WhisperModel
from ..asr.recognizer import ASRRecognizer

# 设置日志记录器
logger = logging.getLogger(__name__)


class ModelManager:
    """
    语音识别模型管理器。
    
    该类负责管理Whisper模型的加载、切换和获取。
    支持动态加载和卸载模型，实现模型间的切换，有效管理GPU内存。
    """
    
    def __init__(self, settings):
        """
        初始化模型管理器。
        
        Args:
            settings: 服务器配置设置，包含模型大小、路径、设备和计算类型等信息
        """
        self.settings = settings
        self.current_model = None
        self.current_model_size = None
        self.asr_instance = None
        
        logger.info(
            f"初始化模型管理器: 默认模型大小={settings.model_size}, "
            f"设备={settings.device}, 计算类型={settings.compute_type}"
        )
        
        # 初始化时不自动加载模型，等待显式调用load_model
    
    def load_model(self, model_size: Optional[str] = None) -> bool:
        """
        加载指定大小的Whisper模型。
        
        使用faster-whisper库加载模型，并更新当前模型状态。
        如果当前已有模型加载，会先卸载它以释放资源。
        
        Args:
            model_size: 要加载的模型大小，如果为None则使用设置中的默认值
            
        Returns:
            加载是否成功
        """
        # 使用指定的模型大小或默认设置
        model_size = model_size or self.settings.model_size
        
        logger.info(f"请求加载模型: {model_size}")
        
        # 如果当前有模型加载，先卸载它
        if self.current_model is not None:
            self._unload_current_model()
        
        try:
            # 确保模型缓存目录存在
            model_path = os.path.expanduser(self.settings.model_path)
            os.makedirs(model_path, exist_ok=True)
            
            # 加载新模型
            logger.info(f"正在加载模型 {model_size}，设备={self.settings.device}，计算类型={self.settings.compute_type}")
            self.current_model = WhisperModel(
                model_size_or_path=model_size,
                device=self.settings.device,
                compute_type=self.settings.compute_type,
                download_root=model_path
            )
            
            # 更新当前模型大小
            self.current_model_size = model_size
            
            logger.info(f"模型 {model_size} 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"加载模型 {model_size} 失败: {str(e)}", exc_info=True)
            self.current_model = None
            self.current_model_size = None
            return False
    
    def get_current_model(self) -> Optional[Any]:
        """
        获取当前加载的模型实例。
        
        Returns:
            当前加载的Whisper模型实例，如果没有加载则返回None
        """
        if self.current_model is None:
            logger.warning("尝试获取模型，但当前没有加载模型")
        
        return self.current_model
    
    def _unload_current_model(self) -> None:
        """
        卸载当前模型并释放资源。
        
        内部方法，用于释放GPU内存并清除当前模型引用。
        """
        if self.current_model is not None:
            model_size = self.current_model_size
            logger.info(f"正在卸载模型: {model_size}")
            
            # 设置为None以允许垃圾回收器回收资源
            self.current_model = None
            
            # 强制进行垃圾回收以释放GPU内存
            gc.collect()
            
            if self.settings.device == "cuda":
                try:
                    # 尝试导入torch以清理CUDA缓存
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        logger.info("已清理CUDA缓存")
                except ImportError:
                    logger.warning("无法导入torch来清理CUDA缓存")
                except Exception as e:
                    logger.warning(f"清理CUDA缓存时出错: {str(e)}")
            
            logger.info(f"模型 {model_size} 已卸载")
    
    def switch_model(self, new_model_size: str) -> bool:
        """
        切换到新的模型大小。
        
        卸载当前模型并加载新模型，有效管理GPU内存资源。
        
        Args:
            new_model_size: 要切换到的新模型大小
            
        Returns:
            切换是否成功
        """
        # 检查是否与当前模型相同
        if new_model_size == self.current_model_size and self.current_model is not None:
            logger.info(f"请求切换到已加载的模型: {new_model_size}，无需操作")
            return True
        
        logger.info(f"请求从 {self.current_model_size or '无'} 切换到新模型: {new_model_size}")
        
        # 验证模型大小是否有效
        valid_models = [
            "tiny", "tiny.en", 
            "base", "base.en", 
            "small", "small.en", 
            "medium", "medium.en", 
            "large-v1", "large-v2", "large-v3", "large", 
            "distil-large-v2", "distil-medium.en", "distil-small.en", "distil-large-v3",
            "large-v3-turbo", "turbo"
        ]
        
        if not any(new_model_size.startswith(model) for model in valid_models):
            logger.error(f"无效的模型大小: {new_model_size}")
            return False
        
        try:
            # 卸载当前模型
            self._unload_current_model()
            
            # 加载新模型
            success = self.load_model(new_model_size)
            
            if success:
                logger.info(f"已成功切换到模型: {new_model_size}")
                return True
            else:
                logger.error(f"切换到模型 {new_model_size} 失败")
                
                # 尝试恢复之前的模型
                if self.current_model_size:
                    logger.info(f"尝试恢复之前的模型: {self.current_model_size}")
                    self.load_model(self.current_model_size)
                
                return False
                
        except Exception as e:
            logger.error(f"切换模型过程中出错: {str(e)}", exc_info=True)
            return False
    
    def __del__(self):
        """析构函数，确保资源被释放"""
        self._unload_current_model() 