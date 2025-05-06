"""
NexTalk WebSocket通信的数据模型定义。

包含以下模型：
- TranscriptionResponse: 语音转文本的结果响应
- ErrorMessage: 错误消息
- StatusUpdate: 状态更新消息
- CommandMessage: 客户端到服务器的命令消息
- FunASRConfig: FunASR配置模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union


class BaseModelWithDict(BaseModel):
    """为所有模型提供兼容v1和v2版本的基类"""
    
    def dict(self, *args, **kwargs):
        """
        Pydantic v1兼容性方法。在v2中调用model_dump方法。
        """
        if hasattr(super(), "model_dump"):
            return super().model_dump(*args, **kwargs)
        return super().dict(*args, **kwargs)


class TranscriptionResponse(BaseModelWithDict):
    """语音转文本结果响应模型。"""
    type: str = "transcription"
    text: str
    mode: Optional[str] = None  # offline, online, 2pass, 2pass-online, 2pass-offline
    wav_name: Optional[str] = None
    is_final: Optional[bool] = None
    timestamp: Optional[Union[str, float]] = None


class ErrorMessage(BaseModelWithDict):
    """错误消息模型。"""
    type: str = "error"
    message: str


class StatusUpdate(BaseModelWithDict):
    """状态更新消息模型。"""
    type: str = "status"
    state: str


class CommandMessage(BaseModelWithDict):
    """客户端到服务器的命令消息模型。"""
    type: str = "command"
    command: str
    payload: str = ""


class FunASRConfig(BaseModel):
    """FunASR配置类，用于控制语音识别参数"""
    
    # 识别模式: 2pass(先在线后离线), online(纯在线), offline(纯离线)
    mode: str = "2pass"
    
    # 在线模型参数
    chunk_size: List[int] = [5, 10]  # 用于在线流式模型的分块大小
    chunk_interval: int = 10  # 处理音频块的间隔（帧数）
    encoder_chunk_look_back: Optional[int] = 4  # 编码器回看窗口大小，默认4（与FunASR示例相同）
    decoder_chunk_look_back: Optional[int] = 0  # 解码器回看窗口大小，默认0（与FunASR示例相同）
    
    # 状态控制
    is_speaking: bool = True  # 是否正在说话
    
    # 增强特性
    hotwords: Optional[str] = None  # 热词，增强特定词语的识别
    itn: bool = True  # 是否使用逆文本正规化（数字转换等）
    
    # 其他参数
    wav_name: str = "microphone"  # 音频名称标识 