"""
WebSocket路由模块

定义WebSocket路由和处理器，适配新的全局模型管理。
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .websocket_handler import handle_websocket
from .funasr_model import GlobalFunASRModels

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.websocket_routes")

# 创建路由器
router = APIRouter()


def ensure_models_initialized():
    """确保全局模型已初始化"""
    models = GlobalFunASRModels()
    if not models.is_initialized():
        raise RuntimeError("全局FunASR模型尚未初始化，请检查应用启动过程")
    return models


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket连接端点，直接使用新的全局模型管理和处理逻辑
    """
    try:
        # 确保全局模型已初始化
        ensure_models_initialized()
        logger.info("全局FunASR模型已就绪")
    except Exception as e:
        logger.error(f"模型初始化检查失败: {str(e)}")
        await websocket.close(code=1011, reason="模型不可用")
        return

    try:
        # 接受连接
        await websocket.accept()
        logger.info("新的WebSocket连接已建立")
        
        # 直接使用新的处理函数（移植官方逻辑）
        await handle_websocket(websocket)
        
    except WebSocketDisconnect:
        logger.info("WebSocket 连接被客户端断开")
    except Exception as e:
        logger.exception(f"WebSocket 处理过程中发生错误: {str(e)}")
        try:
            await websocket.close(code=1011, reason="内部服务器错误")
        except Exception as close_error:
            logger.error(f"关闭 WebSocket 连接时出错: {str(close_error)}")
    finally:
        logger.info("WebSocket 连接处理结束")


# 保持向后兼容的路由（如果有其他地方还在使用 /ws）
@router.websocket("/ws")
async def legacy_websocket_endpoint(websocket: WebSocket):
    """向后兼容的WebSocket端点，重定向到新的处理逻辑"""
    logger.info("使用旧路由 /ws，重定向到新的处理逻辑")
    await websocket_endpoint(websocket)