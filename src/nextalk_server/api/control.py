"""
控制API路由。

此模块实现了用于控制服务器行为的API端点，如切换Whisper模型。
"""

import logging
from fastapi import APIRouter, WebSocket, Depends, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..config.settings import settings
from nextalk_shared.data_models import CommandMessage, StatusUpdate
from nextalk_shared.constants import STATUS_LISTENING, STATUS_ERROR

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/api", tags=["control"])

class ModelCommandResponse(BaseModel):
    """模型命令响应模型"""
    success: bool
    message: str
    model: Optional[str] = None

class SettingsResponse(BaseModel):
    """服务器设置响应模型"""
    default_model: str
    device: str
    compute_type: str
    vad_sensitivity: int
    port: int
    host: str
    language: str

@router.get("/settings")
async def get_settings() -> SettingsResponse:
    """获取当前服务器设置"""
    logger.info("收到请求：获取服务器设置")
    return SettingsResponse(
        default_model=settings.default_model,
        device=settings.device,
        compute_type=settings.compute_type,
        vad_sensitivity=settings.vad_sensitivity,
        port=settings.port,
        host=settings.host,
        language=settings.language
    )

@router.get("/models/available")
async def get_available_models():
    """获取可用的模型列表"""
    logger.info("收到请求：获取可用模型列表")
    try:
        from faster_whisper.utils import available_models
        models = available_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"获取可用模型列表时出错：{str(e)}")
        return Response(
            content=f"{{'error': '获取可用模型列表失败: {str(e)}'}}",
            status_code=500,
            media_type="application/json"
        )

@router.post("/models/switch")
async def switch_model(model_data: Dict[str, Any]) -> ModelCommandResponse:
    """
    切换到指定的模型

    Args:
        model_data: 包含model_size字段的字典
    """
    model_size = model_data.get("model_size")
    if not model_size:
        return ModelCommandResponse(
            success=False,
            message="无效的请求：缺少model_size字段"
        )
    
    logger.info(f"收到请求：切换到模型 {model_size}")
    
    # 从应用状态获取模型管理器
    from fastapi import Request
    request = Request(scope={"type": "http"})
    model_manager = request.app.state.model_manager
    
    # 切换模型
    success = model_manager.switch_model(model_size)
    
    if success:
        return ModelCommandResponse(
            success=True,
            message=f"已成功切换到模型: {model_size}",
            model=model_size
        )
    else:
        return ModelCommandResponse(
            success=False,
            message=f"切换到模型 {model_size} 失败",
            model=model_manager.current_model_size
        )

# WebSocket命令处理函数
async def handle_command(command: CommandMessage, model_manager, websocket: WebSocket) -> bool:
    """
    处理从WebSocket连接收到的命令。
    
    Args:
        command: 命令消息
        model_manager: 模型管理器实例
        websocket: WebSocket连接

    Returns:
        命令处理是否成功
    """
    logger.info(f"收到WebSocket命令: {command.command}")
    
    if command.command == "switch_model":
        # 模型切换命令
        payload = command.payload
        if payload and "model" in payload:
            model_size = payload["model"]
            logger.info(f"请求切换到模型: {model_size}")
            
            # 发送正在处理状态
            await websocket.send_json(StatusUpdate(state="processing").dict())
            
            # 切换模型
            success = model_manager.switch_model(model_size)
            
            if success:
                # 发送成功响应
                await websocket.send_json({
                    "type": "command_result",
                    "command": "switch_model",
                    "success": True,
                    "message": f"已切换到模型: {model_size}"
                })
                logger.info(f"成功切换到模型: {model_size}")
                
                # 恢复监听状态
                await websocket.send_json(StatusUpdate(state=STATUS_LISTENING).dict())
                return True
            else:
                # 发送失败响应
                await websocket.send_json({
                    "type": "command_result",
                    "command": "switch_model",
                    "success": False,
                    "message": f"切换模型失败: {model_size}"
                })
                logger.error(f"切换到模型 {model_size} 失败")
                
                # 发送错误状态
                await websocket.send_json(StatusUpdate(state=STATUS_ERROR).dict())
                
                # 短暂延迟后恢复监听状态
                import asyncio
                await asyncio.sleep(1.0)
                await websocket.send_json(StatusUpdate(state=STATUS_LISTENING).dict())
                return False
        else:
            # 缺少必要参数
            logger.warning("切换模型命令缺少必要参数: model")
            await websocket.send_json({
                "type": "command_result",
                "command": "switch_model",
                "success": False,
                "message": "切换模型命令缺少必要参数: model"
            })
            return False
    else:
        # 未知命令
        logger.warning(f"未知命令: {command.command}")
        await websocket.send_json({
            "type": "command_result",
            "command": command.command,
            "success": False,
            "message": f"未知命令: {command.command}"
        })
        return False 