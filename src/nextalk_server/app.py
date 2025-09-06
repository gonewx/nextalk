"""
FastAPI应用模块

创建并配置FastAPI应用实例，提供API服务。
"""

import logging
import atexit
import asyncio
import os
import sys
from fastapi import FastAPI
from logging.handlers import RotatingFileHandler

from .websocket_routes import router as websocket_router
from .config import get_config
from .funasr_model import FunASRModel, get_preloaded_model


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


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    # 获取配置
    config = get_config()

    logger.info("正在初始化NexTalk服务器应用...")

    # 创建FastAPI应用
    app = FastAPI(
        title="NexTalk Server",
        description="NexTalk实时语音识别服务器 - FunASR模型",
        version="0.1.0",
    )

    # 检查是否有预加载的模型实例
    preloaded_model = get_preloaded_model()

    if preloaded_model is not None:
        logger.info("使用预加载的模型实例")
        model = preloaded_model
    else:
        logger.info("没有预加载的模型实例，创建新的模型实例")
        model = FunASRModel(config)

    # 将模型实例添加到应用状态
    app.state.model = model

    # 注册应用启动事件，加载模型
    @app.on_event("startup")
    async def setup_model():
        """服务器启动时加载模型"""
        logger.info("服务器启动，开始加载模型...")

        # 检查是否使用的预加载模型
        if get_preloaded_model() is app.state.model:
            logger.info("使用的是预加载模型，已就绪")
            app.state.model_loaded = True
            return

        # 检查环境变量，如果模型已预加载则跳过初始化
        if os.environ.get("NEXTALK_MODEL_PRELOADED", "0") == "1":
            logger.info("检测到环境变量NEXTALK_MODEL_PRELOADED=1，模型已预加载，跳过重复初始化")
            app.state.model_loaded = True
            return

        try:
            success = await app.state.model.initialize()
            if success:
                app.state.model_loaded = True
                logger.info("模型加载成功，服务器已就绪")
            else:
                app.state.model_loaded = False
                logger.error("模型加载失败，服务器可能无法正常工作")
        except Exception as e:
            app.state.model_loaded = False
            logger.exception(f"模型加载时出错: {str(e)}")

    # 注册应用关闭时的清理函数
    @app.on_event("shutdown")
    async def cleanup_resources():
        """应用关闭时清理资源"""
        logger.info("服务器关闭，清理模型资源...")
        if hasattr(app.state, "model"):
            try:
                await app.state.model.release()
                logger.info("模型资源已释放")
            except Exception as e:
                logger.error(f"释放模型资源时出错: {str(e)}")

    # 同时使用atexit注册，确保在非正常关闭时也能清理资源
    def cleanup_on_exit():
        """程序退出时清理资源"""
        try:
            logger.info("程序退出，清理模型资源...")
            if hasattr(app.state, "model"):
                # 使用同步方式释放模型
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                try:
                    loop.run_until_complete(app.state.model.release())
                    logger.info("模型资源已释放")
                except Exception as e:
                    logger.error(f"释放模型资源时出错: {str(e)}")
        except Exception as e:
            # 异常时直接使用print，因为logger可能已经关闭
            print(f"退出清理时发生错误: {str(e)}")

    atexit.register(cleanup_on_exit)

    # 包含WebSocket路由
    app.include_router(websocket_router)

    return app


# 全局应用实例
app = create_app()
