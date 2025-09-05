"""
FastAPI应用模块

创建并配置FastAPI应用实例，提供API服务。
"""

import logging
import atexit
import asyncio
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from logging.handlers import RotatingFileHandler

from .websocket_routes import router as websocket_router
from .config import get_config
from .funasr_model import GlobalFunASRModels


def setup_logging():
    """
    设置全局日志配置

    配置根日志记录器，确保所有模块使用统一的日志设置
    """
    # 创建日志目录
    log_dir = os.path.expanduser("~/.nextalk/logs")
    os.makedirs(log_dir, exist_ok=True)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清除现有处理器，避免重复
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建格式化器
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # 文件处理器 (轮转日志)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "nextalk.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # 抑制第三方库的日志
    for logger_name in ["uvicorn", "uvicorn.access"]:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.handlers = []
        third_party_logger.propagate = True

    return root_logger


# 设置日志系统
logger = setup_logging().getChild("nextalk_server.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI应用生命周期管理"""
    # 启动时初始化模型
    logger.info("正在初始化FunASR模型...")
    try:
        config = get_config()
        models = GlobalFunASRModels()
        models.initialize(config)
        
        # 将模型实例添加到应用状态
        app.state.models = models
        app.state.model_loaded = True
        logger.info("FunASR模型初始化完成")
    except Exception as e:
        logger.error(f"模型初始化失败: {str(e)}")
        app.state.model_loaded = False
        raise
    
    yield
    
    # 关闭时清理资源
    logger.info("清理模型资源...")
    try:
        # 这里可以添加模型清理逻辑，如果需要的话
        logger.info("模型资源清理完成")
    except Exception as e:
        logger.error(f"清理模型资源时出错: {str(e)}")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    logger.info("正在初始化NexTalk服务器应用...")

    # 创建FastAPI应用，使用生命周期管理
    app = FastAPI(
        title="NexTalk Server",
        description="NexTalk实时语音识别服务器 - FunASR模型",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 包含WebSocket路由
    app.include_router(websocket_router)

    return app


# 全局应用实例
app = create_app()
