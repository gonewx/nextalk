#!/usr/bin/env python3
"""
NexTalk客户端主入口点。

此文件是NexTalk客户端应用程序的主入口，负责：
- 初始化NexTalkClient实例
- 设置和运行异步事件循环
- 处理应用程序生命周期
"""

import asyncio
import logging
import signal
import sys
from .client_logic import NexTalkClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# 全局客户端实例，用于信号处理
client = None

def handle_shutdown(sig, frame):
    """处理终止信号，优雅地关闭应用程序。"""
    logger.info(f"收到信号 {sig}，准备关闭...")
    if client and asyncio.get_event_loop().is_running():
        asyncio.create_task(shutdown())

async def shutdown():
    """优雅地关闭应用程序。"""
    global client
    if client:
        await client.stop()
    # 终止事件循环
    loop = asyncio.get_event_loop()
    loop.stop()

async def main():
    """
    NexTalk客户端的主函数。
    
    初始化客户端、注册信号处理器、启动客户端，并保持应用程序运行。
    """
    global client
    
    logger.info("启动NexTalk客户端...")
    
    # 创建客户端实例
    client = NexTalkClient()
    
    # 注册信号处理程序（SIGINT对应Ctrl+C，SIGTERM对应终止信号）
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))
    
    try:
        # 启动客户端
        success = await client.start()
        if not success:
            logger.error("客户端启动失败")
            return
        
        # 创建一个Future对象，用于保持事件循环运行
        # 直到收到关闭信号
        running = asyncio.Future()
        
        # 等待关闭事件被设置
        await client._shutdown_event.wait()
        
        # 解决Future，允许程序退出
        if not running.done():
            running.set_result(None)
            
    except Exception as e:
        logger.exception(f"运行过程中发生错误: {e}")
    finally:
        # 确保客户端已停止
        if client:
            await client.stop()
        logger.info("NexTalk客户端已关闭")

if __name__ == "__main__":
    try:
        # 运行主异步函数
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.exception(f"主程序发生错误: {e}")
    finally:
        logger.info("程序退出")
        sys.exit(0) 