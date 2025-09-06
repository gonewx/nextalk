"""
WebSocket路由模块

定义WebSocket路由和处理器。
"""

import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from .websocket_handler import WebSocketHandler
from .funasr_model import FunASRModel, get_preloaded_model
from .config import get_config
from nextalk_shared.constants import STATUS_CONNECTED

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.websocket_routes")

# 创建路由器
router = APIRouter()

# 全局模型实例 - 只创建一次
_model_instance = None


async def get_model():
    """获取或创建模型实例，并确保初始化"""
    global _model_instance
    try:
        # 首先尝试获取预加载的模型实例
        preloaded_model = get_preloaded_model()

        if preloaded_model is not None:
            logger.info("使用预加载的模型实例")
            return preloaded_model

        # 如果没有预加载的模型，检查全局实例
        if _model_instance is None:
            logger.info("创建全局FunASR模型实例")
            config = get_config()
            logger.debug(
                f"获取到配置: {config.__dict__ if hasattr(config, '__dict__') else 'No __dict__'}"
            )
            _model_instance = FunASRModel(config)
            logger.info("FunASR模型实例创建成功")

        # 如果模型尚未初始化，初始化它
        if not hasattr(_model_instance, "_initialized") or not _model_instance._initialized:
            logger.info("初始化FunASR模型...")
            success = await _model_instance.initialize()
            if success:
                logger.info("FunASR模型初始化成功")
            else:
                logger.error("FunASR模型初始化失败")

        return _model_instance
    except Exception as e:
        logger.error(f"获取或初始化模型时出错: {str(e)}")
        logger.exception(e)
        # 如果遇到错误，重置全局实例以便下次连接时重新尝试
        _model_instance = None
        raise


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，处理语音识别请求"""
    # 获取模型实例
    try:
        logger.info("接收新的WebSocket连接请求...")
        model = await get_model()

        # 创建WebSocket处理器
        handler = WebSocketHandler(websocket, model)

        # 接受连接
        await handler.accept()
        logger.info("WebSocket连接已建立")

        # 发送连接状态
        await handler.send_status(STATUS_CONNECTED)

        # 监听消息
        await handler.listen()

    except WebSocketDisconnect:
        logger.info("WebSocket连接已断开")
    except Exception as e:
        logger.error(f"WebSocket处理出错: {str(e)}")
        logger.exception(e)
        # 尝试关闭连接
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1011, reason=f"处理时出错: {str(e)}")
            except:
                pass
