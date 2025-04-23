"""
NexTalk服务器FastAPI应用。

该模块创建主FastAPI应用实例，并包含所有路由。
"""

from fastapi import FastAPI
from .api import websocket, control

# 创建FastAPI应用
app = FastAPI(
    title="NexTalk Server",
    description="NexTalk实时语音识别服务器",
    version="0.1.0"
)

# 包含WebSocket路由
app.include_router(websocket.router)

# 包含控制API路由
app.include_router(control.router) 