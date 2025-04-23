"""
NexTalk服务器控制API模块。

该模块提供了用于控制服务器行为的API端点，包括：
1. REST API端点，用于服务器的远程控制
2. 处理WebSocket命令消息的工具函数
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, Callable

from ..models.manager import ModelManager
from ..config.settings import settings
from nextalk_shared.data_models import CommandMessage, StatusUpdate

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/control", tags=["control"])


# 定义REST API的请求模型
class ModelSwitchRequest(BaseModel):
    """模型切换请求。"""
    model_size: str


# 定义可用的命令处理器映射
command_handlers: Dict[str, Callable] = {}


@router.post("/switch-model")
async def switch_model(request: ModelSwitchRequest, background_tasks: BackgroundTasks):
    """
    切换语音识别模型的REST API端点。
    
    Args:
        request: 包含新模型大小的请求
        background_tasks: FastAPI的后台任务对象，用于异步执行模型切换
        
    Returns:
        操作结果的字典
    """
    logger.info(f"收到模型切换请求: {request.model_size}")
    
    # 获取模型管理器实例
    # 注意：在实际实现中，应该使用依赖注入或单例模式获取模型管理器
    model_manager = ModelManager(settings)
    
    try:
        # 在后台任务中执行模型切换
        # 这样可以立即返回响应，而不需要等待模型加载完成
        background_tasks.add_task(model_manager.switch_model, request.model_size)
        
        return {
            "status": "success",
            "message": f"正在切换到模型: {request.model_size}",
            "model_size": request.model_size
        }
    except ValueError as ve:
        # 处理无效模型名称等错误
        logger.error(f"模型切换请求无效: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # 处理其他未预料的错误
        logger.error(f"模型切换请求失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"模型切换失败: {str(e)}")


async def handle_command(command_message: CommandMessage, model_manager: ModelManager, websocket = None):
    """
    处理WebSocket命令消息。
    
    该函数用于在WebSocket接收循环中处理命令消息，例如切换模型。
    
    Args:
        command_message: 客户端发送的命令消息
        model_manager: 模型管理器实例
        websocket: WebSocket连接对象，用于发送响应消息
        
    Returns:
        操作是否成功
    """
    command = command_message.command
    payload = command_message.payload
    
    logger.info(f"收到WebSocket命令: {command}, 参数: {payload}")
    
    # 处理模型切换命令
    if command == "switch_model":
        try:
            # 执行模型切换
            success = model_manager.switch_model(payload)
            
            # 如果提供了WebSocket，发送操作结果
            if websocket:
                if success:
                    await websocket.send_json({
                        "type": "command_result",
                        "command": command,
                        "status": "success",
                        "message": f"已切换到模型: {payload}"
                    })
                else:
                    await websocket.send_json({
                        "type": "command_result",
                        "command": command,
                        "status": "error",
                        "message": f"切换到模型 {payload} 失败"
                    })
            
            return success
        except Exception as e:
            logger.error(f"执行命令 {command} 失败: {str(e)}", exc_info=True)
            
            # 如果提供了WebSocket，发送错误消息
            if websocket:
                await websocket.send_json({
                    "type": "command_result",
                    "command": command,
                    "status": "error",
                    "message": f"命令执行错误: {str(e)}"
                })
            
            return False
    else:
        logger.warning(f"未知命令: {command}")
        
        # 如果提供了WebSocket，发送错误消息
        if websocket:
            await websocket.send_json({
                "type": "command_result",
                "command": command,
                "status": "error",
                "message": f"未知命令: {command}"
            })
        
        return False 