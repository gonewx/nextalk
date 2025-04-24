"""
NexTalk WebSocket通信的数据模型定义。

包含以下模型：
- TranscriptionResponse: 语音转文本的结果响应
- ErrorMessage: 错误消息
- StatusUpdate: 状态更新消息
- CommandMessage: 客户端到服务器的命令消息
"""

from pydantic import BaseModel


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