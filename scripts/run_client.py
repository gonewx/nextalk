#!/usr/bin/env python3
"""
NexTalk 客户端运行脚本

该脚本启动NexTalk的语音识别客户端，支持标准模式和调试模式。
"""

import sys
import os
import logging
import argparse
from pathlib import Path


def setup_logging(log_level="info", log_file=None):
    """
    配置日志系统
    
    设置基本的日志格式和级别，确保所有模块的日志都能被正确显示
    
    参数:
        log_level: 日志级别，可选值为"debug", "info", "warning", "error"
        log_file: 日志文件路径，如不指定则只输出到控制台
    """
    # 转换字符串日志级别到logging模块常量
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR
    }
    level = level_map.get(log_level.lower(), logging.INFO)
    
    # 创建处理器列表
    handlers = [logging.StreamHandler()]
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='w')
            handlers.append(file_handler)
        except Exception as e:
            print(f"警告: 无法创建日志文件 {log_file}: {e}")
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # 设置特定模块的日志级别
    logging.getLogger("websockets").setLevel(logging.INFO)  # 防止websockets库输出过多调试信息
    
    # 确保nextalk模块的日志级别正确设置
    logging.getLogger("nextalk_client").setLevel(level)
    
    logger = logging.getLogger(__name__)
    
    # 打印环境信息(在调试模式下)
    if level == logging.DEBUG:
        logger.debug("=== 调试模式环境信息 ===")
        logger.debug(f"Python版本: {sys.version}")
        logger.debug(f"工作目录: {os.getcwd()}")
        logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")
        logger.debug(f"NEXTALK_DEBUG: {os.environ.get('NEXTALK_DEBUG', 'not set')}")
    
    return logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="NexTalk语音识别客户端")
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式，显示更详细的日志"
    )
    parser.add_argument(
        "--log-file", 
        type=str, 
        help="指定日志文件路径，默认只输出到控制台"
    )
    parser.add_argument(
        "--server-host",
        type=str,
        help="指定服务器主机地址，默认使用配置文件中的设置"
    )
    parser.add_argument(
        "--server-port",
        type=int,
        help="指定服务器端口，默认使用配置文件中的设置"
    )
    return parser.parse_args()


def main():
    """
    启动NexTalk客户端
    
    解析命令行参数，设置日志，启动客户端应用程序。
    """
    # 解析命令行参数
    args = parse_args()
    
    # 确保PYTHONPATH包含src目录
    src_path = Path(__file__).resolve().parent.parent / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
        os.environ["PYTHONPATH"] = f"{str(src_path)}:{os.environ.get('PYTHONPATH', '')}"
    
    # 设置环境变量以启用调试模式
    if args.debug:
        os.environ["NEXTALK_DEBUG"] = "1"
        log_level = "debug"
    else:
        log_level = "info"
    
    # 如果指定了服务器地址和端口，设置相应的环境变量
    if args.server_host:
        os.environ["NEXTALK_SERVER_HOST"] = args.server_host
    if args.server_port:
        os.environ["NEXTALK_SERVER_PORT"] = str(args.server_port)
    
    # 设置日志
    logger = setup_logging(log_level, args.log_file)
    
    # 显示启动信息
    print("\033[1;36m=== NexTalk客户端启动 ===\033[0m")
    logger.info("正在启动NexTalk客户端...")
    
    if args.debug:
        print(f"\033[1;33m调试模式已启用，将显示详细日志\033[0m")
        if args.log_file:
            print(f"\033[1;33m日志将保存到 {args.log_file}\033[0m")
    
    try:
        # 导入并运行客户端模块
        from nextalk_client.main import run_client
        run_client(debug=args.debug, log_file=args.log_file)
    except ModuleNotFoundError:
        logger.error("无法导入nextalk_client模块，请确保已安装")
        print("\033[1;31m错误: 无法导入nextalk_client模块，请确保已安装\033[0m")
        return 1
    except KeyboardInterrupt:
        logger.info("客户端被用户中断")
    except Exception as e:
        logger.exception(f"客户端运行时发生错误: {e}")
        return 1
    
    logger.info("NexTalk客户端已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 