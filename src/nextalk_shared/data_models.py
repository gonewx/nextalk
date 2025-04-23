"""
NexTalk WebSocket通信的数据模型定义。

包含以下模型：
- TranscriptionResponse: 语音转文本的结果响应
- ErrorMessage: 错误消息
- StatusUpdate: 状态更新消息
- CommandMessage: 客户端到服务器的命令消息
"""

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    """语音转文本结果响应模型。"""
    type: str = "transcription"
    text: str


class ErrorMessage(BaseModel):
    """错误消息模型。"""
    type: str = "error"
    message: str


class StatusUpdate(BaseModel):
    """状态更新消息模型。"""
    type: str = "status"
    state: str


class CommandMessage(BaseModel):
    """客户端到服务器的命令消息模型。"""
    type: str = "command"
    command: str
    payload: str = "" 