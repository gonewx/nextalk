#!/usr/bin/env python3
"""
NexTalk 服务器运行脚本

该脚本启动NexTalk的语音识别服务器，使用Uvicorn作为ASGI服务器。
"""

import uvicorn
from nextalk_server.config.settings import settings


def main():
    """
    启动NexTalk服务器
    
    使用nextalk_server.config.settings中的设置配置Uvicorn服务器，
    启动FastAPI应用程序。
    """
    print(f"正在启动NexTalk服务器，端口:{settings.port}...")
    print(f"服务器配置: 模型={settings.model_size}, 设备={settings.device}")
    
    # 使用Uvicorn运行FastAPI应用
    uvicorn.run(
        "nextalk_server.main:app", 
        host=settings.host,
        port=settings.port,
        reload=True  # 开发模式下启用热重载
    )


if __name__ == "__main__":
    main() 