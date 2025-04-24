"""
NexTalk服务器FastAPI应用。

该模块创建主FastAPI应用实例，并包含所有路由。
"""

from fastapi import FastAPI
from .api import websocket, control
from .models.manager import ModelManager
from .config.settings import settings
import logging
import atexit

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="NexTalk Server",
    description="NexTalk实时语音识别服务器",
    version="0.1.0"
)

# 初始化模型管理器并预加载模型
model_manager = ModelManager(settings)
logger.info(f"服务器启动时预加载语音识别模型: {settings.default_model}")
model_loaded = model_manager.load_model(settings.default_model)
if model_loaded:
    logger.info(f"模型 {settings.default_model} 预加载成功")
else:
    logger.error(f"模型 {settings.default_model} 预加载失败")

# 将模型管理器添加到应用状态，使其可在路由中访问
app.state.model_manager = model_manager

# 注册应用关闭时的清理函数
@app.on_event("shutdown")
async def cleanup_resources():
    """应用关闭时清理资源"""
    logger.info("服务器关闭，清理模型资源...")
    if hasattr(app.state, "model_manager"):
        app.state.model_manager._unload_current_model()
        logger.info("模型资源已释放")

# 同时使用atexit注册，确保在非正常关闭时也能清理资源
def cleanup_on_exit():
    """程序退出时清理资源"""
    logger.info("程序退出，清理模型资源...")
    if model_manager and model_manager.current_model is not None:
        model_manager._unload_current_model()
        logger.info("模型资源已释放")

atexit.register(cleanup_on_exit)

# 包含WebSocket路由
app.include_router(websocket.router)

# 包含控制API路由
app.include_router(control.router) 