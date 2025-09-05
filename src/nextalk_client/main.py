#!/usr/bin/env python3
"""
NexTalk客户端主入口点。

此文件是NexTalk客户端应用程序的主入口，负责：
- 初始化NexTalkClient实例
- 设置和运行异步事件循环
- 处理应用程序生命周期
"""

import argparse
import asyncio
import logging
import os
import signal
import sys

from .client_logic import NexTalkClient


# 解析命令行参数
def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="NexTalk语音识别客户端")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，显示更详细的日志")
    parser.add_argument("--log-file", type=str, help="指定日志文件路径，默认只输出到控制台")
    parser.add_argument(
        "--server", help="服务器地址，例如: ws://localhost:8000/ws/stream", type=str
    )
    parser.add_argument("--ssl", help="使用SSL连接", action="store_true")
    parser.add_argument("--hotkey", help="热键组合，例如: ctrl+shift+space", type=str)
    parser.add_argument(
        "--log-level",
        help="日志级别: debug, info, warning, error, critical",
        type=str,
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
    )
    parser.add_argument("--config-file", help="配置文件路径", type=str)
    return parser.parse_args()


# 配置日志
def setup_logging(args):
    """根据命令行参数设置日志"""
    # 检查环境变量是否启用了调试模式
    env_debug = os.environ.get("NEXTALK_DEBUG", "0").lower() in ("1", "true", "yes")
    log_level = logging.DEBUG if args.debug or env_debug else logging.INFO

    # 创建日志处理器列表
    handlers = [logging.StreamHandler()]

    # 如果指定了日志文件，添加文件处理器
    if args.log_file:
        try:
            file_handler = logging.FileHandler(args.log_file)
            handlers.append(file_handler)
        except Exception as e:
            print(f"无法创建日志文件 {args.log_file}: {e}", file=sys.stderr)

    # 配置日志格式，增加颜色区分不同级别
    colored_formatter = logging.Formatter(
        "%(asctime)s - \033[36m%(name)s\033[0m - \033[1;%(levelcolor)sm%(levelname)s\033[0m - %(message)s"
    )

    # 普通格式，用于文件日志
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # 设置日志基本配置
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    # 为控制台输出添加彩色支持
    console_handler = handlers[0]

    # 自定义过滤器添加颜色代码
    class ColorFilter(logging.Filter):
        def filter(self, record):
            if record.levelno >= logging.ERROR:
                record.levelcolor = "31"  # 红色
            elif record.levelno >= logging.WARNING:
                record.levelcolor = "33"  # 黄色
            elif record.levelno >= logging.INFO:
                record.levelcolor = "32"  # 绿色
            else:
                record.levelcolor = "36"  # 青色(调试)
            return True

    # 只为控制台添加彩色
    console_handler.setFormatter(colored_formatter)
    console_handler.addFilter(ColorFilter())

    # 为文件处理器设置普通格式
    if len(handlers) > 1:
        handlers[1].setFormatter(file_formatter)

    # 获取日志记录器
    logger = logging.getLogger(__name__)

    # 打印启动信息
    print("\033[1;36m=== NexTalk客户端启动 ===\033[0m")

    # 如果启用调试模式，显示一些额外信息
    if log_level == logging.DEBUG:
        logger.debug("\033[1;33m调试模式已启用，将显示详细日志\033[0m")

        # 环境信息
        logger.debug(f"Python版本: {sys.version}")
        logger.debug(f"工作目录: {os.getcwd()}")

        # 环境变量
        env_vars = {
            "PYTHONPATH": os.environ.get("PYTHONPATH", "not set"),
            "NEXTALK_DEBUG": os.environ.get("NEXTALK_DEBUG", "not set"),
        }
        logger.debug(f"环境变量: {env_vars}")

        # 设置一些第三方库的日志级别，以防止过多的调试信息
        logging.getLogger("websockets").setLevel(logging.INFO)

    return logger


# 全局客户端实例，用于信号处理
client = None
loop = None


def handle_shutdown(sig, frame):
    """处理终止信号，优雅地关闭应用程序。"""
    logger.info(f"收到信号 {sig}，准备关闭...")
    if client and asyncio.get_event_loop().is_running():
        asyncio.create_task(shutdown())


async def shutdown():
    """优雅地关闭应用程序。"""
    global client
    if client:
        # 等待客户端完全停止后再停止事件循环
        await client.stop()

    # 不要在这里直接停止事件循环
    # 让主函数中的shutdown_event处理程序退出


async def main(args):
    """
    NexTalk客户端的主函数。

    初始化客户端、注册信号处理器、启动客户端，并保持应用程序运行。

    Args:
        args: 解析后的命令行参数
    """
    global client

    # 输出版本信息
    logger.info("NexTalk客户端 v0.1.0")
    logger.info("正在启动NexTalk客户端...")

    # 创建客户端实例
    client = NexTalkClient()

    # 注册信号处理程序（SIGINT对应Ctrl+C，SIGTERM对应终止信号）
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # 使用更直接的信号处理方式
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(immediate_shutdown(s)))

    try:
        # 启动客户端
        print("\033[1;36m正在连接到服务器...\033[0m")
        success = await client.start()
        if not success:
            logger.error("\033[1;31m客户端启动失败\033[0m")
            print("\033[1;31m错误: 客户端启动失败，请检查服务器是否正在运行\033[0m")
            return

        print("\033[1;32m客户端已成功启动\033[0m")
        print(
            f"\033[1;33m提示: 使用热键({client.client_config.get('hotkey', 'ctrl+shift+space')})激活语音识别\033[0m"
        )

        # 等待关闭事件被设置
        await client._shutdown_event.wait()

    except Exception as e:
        logger.exception(f"运行过程中发生错误: {e}")
    finally:
        # 确保客户端已停止
        if client:
            try:
                await client.stop()
            except Exception as e:
                logger.error(f"停止客户端时出错: {e}")
        logger.info("NexTalk客户端已关闭")


async def immediate_shutdown(sig):
    """立即关闭应用程序，对信号做出更直接的响应。"""
    global client
    logger.info(f"收到信号 {sig}，立即关闭...")

    # 立即停止客户端
    if client:
        try:
            await client.stop()
        except Exception as e:
            logger.error(f"停止客户端时出错: {e}")

    # 设置关闭事件
    if client and hasattr(client, "_shutdown_event"):
        client._shutdown_event.set()

    # 更强制地停止程序（如果客户端没有正确响应）
    if sig == signal.SIGINT:
        logger.warning("强制终止程序...")
        # 使用os._exit强制终止，而不是sys.exit，因为后者只会引发异常
        import os

        os._exit(130)  # 130是SIGINT的标准退出码


def run_client(debug=False, log_file=None):
    """
    启动NexTalk客户端的公共接口

    这个函数可以从外部脚本调用，用于启动客户端应用程序。

    Args:
        debug: 布尔值，是否启用调试模式
        log_file: 字符串，日志文件路径，None表示只输出到控制台

    Returns:
        整数，表示程序退出状态码，0表示正常退出
    """

    # 创建一个类似的参数对象
    class Args:
        pass

    args = Args()
    args.debug = debug
    args.log_file = log_file

    # 设置日志
    global logger
    logger = setup_logging(args)

    try:
        # 运行主异步函数
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.exception(f"主程序发生错误: {e}")
        return 1
    finally:
        # 打印退出消息
        print("\033[1;36m=== NexTalk客户端已退出 ===\033[0m")
        logger.info("程序退出")

    return 0


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()

    # 设置日志
    logger = setup_logging(args)

    try:
        # 运行主异步函数
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.exception(f"主程序发生错误: {e}")
    finally:
        # 打印退出消息
        print("\033[1;36m=== NexTalk客户端已退出 ===\033[0m")
        logger.info("程序退出")
        sys.exit(0)
