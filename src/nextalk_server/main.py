"""
NexTalk 服务器主入口点

此文件负责导出FastAPI应用程序实例，供Uvicorn服务器发现和运行
"""
from .config.settings import settings

from .server_app import app

# FastAPI应用程序实例会自动被Uvicorn服务器发现
# 使用 'nextalk_server.main:app' 作为Uvicorn的应用路径 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
