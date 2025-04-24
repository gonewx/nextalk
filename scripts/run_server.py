#!/usr/bin/env python3
"""
NexTalk 服务器运行脚本

该脚本启动NexTalk的语音识别服务器，使用Uvicorn作为ASGI服务器。
支持标准模式和调试模式，可通过命令行参数控制。
"""

import uvicorn
import logging
import argparse
import os
import sys
from pathlib import Path
from nextalk_server.config.settings import settings


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
    
    # 设置uvicorn和fastapi的日志级别
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("fastapi").setLevel(level)
    
    # 确保nextalk模块的日志级别正确设置
    logging.getLogger("nextalk_server").setLevel(level)
    
    logger = logging.getLogger(__name__)
    
    # 打印环境信息(在调试模式下)
    if level == logging.DEBUG:
        logger.debug("=== 调试模式环境信息 ===")
        logger.debug(f"Python版本: {sys.version}")
        logger.debug(f"工作目录: {os.getcwd()}")
        logger.debug(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'not set')}")
        logger.debug(f"服务器配置: 模型={settings.default_model}, 设备={settings.device}")
    
    return logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="NexTalk语音识别服务器")
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
        "--host",
        type=str,
        default=settings.host,
        help=f"指定服务器监听的主机地址，默认为{settings.host}"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"指定服务器监听的端口，默认为{settings.port}"
    )
    return parser.parse_args()


def main():
    """
    启动NexTalk服务器
    
    解析命令行参数，设置日志，使用Uvicorn启动FastAPI应用程序。
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
    
    # 设置日志
    logger = setup_logging(log_level, args.log_file)
    
    # 显示启动信息
    print("\033[1;36m=== NexTalk服务器启动 ===\033[0m")
    logger.info(f"正在启动NexTalk服务器，主机:{args.host}, 端口:{args.port}...")
    
    if args.debug:
        print(f"\033[1;33m调试模式已启用，将显示详细日志\033[0m")
        if args.log_file:
            print(f"\033[1;33m日志将保存到 {args.log_file}\033[0m")
    
    try:
        # 使用Uvicorn运行FastAPI应用
        uvicorn.run(
            "nextalk_server.main:app", 
            host=args.host,
            port=args.port,
            reload=args.debug,  # 在调试模式下启用热重载
            log_level=log_level
        )
    except KeyboardInterrupt:
        logger.info("服务器被用户中断")
    except Exception as e:
        logger.exception(f"服务器运行时发生错误: {e}")
        return 1
    
    logger.info("服务器已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 