#!/usr/bin/env python
"""
NexTalk服务器的便捷启动脚本。

本脚本用于方便地启动NexTalk服务器，处理命令行参数和环境设置。
"""

import os
import sys
import logging
import argparse
import uvicorn
import asyncio
import time
from pathlib import Path

# 添加src目录到Python路径
src_dir = Path(__file__).resolve().parent.parent / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

from nextalk_server.config import get_config, update_config


def setup_logging(log_level="info", log_file=None):
    """
    配置日志系统。
    
    Args:
        log_level: 日志级别，可以是"debug", "info", "warning", "error"
        log_file: 日志文件路径，如果为None则只输出到控制台
    
    Returns:
        配置好的日志记录器
    """
    # 转换字符串日志级别到数值
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 设置日志处理器
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # 配置日志格式和处理器
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # 获取日志记录器
    logger = logging.getLogger("nextalk")
    
    return logger


def parse_args():
    """解析命令行参数"""
    # 获取当前配置
    config = get_config()
    
    parser = argparse.ArgumentParser(description="NexTalk语音识别服务器")
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试模式，显示更详细的日志 (等同于 --log-level debug)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="设置日志级别 (debug, info, warning, error, critical)"
    )
    parser.add_argument(
        "--log-file", 
        type=str, 
        help="指定日志文件路径，默认只输出到控制台"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.host,
        help=f"指定服务器监听的主机地址，默认为{config.host}"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.port,
        help=f"指定服务器监听的端口，默认为{config.port}"
    )
    parser.add_argument(
        "--model-path", 
        type=str, 
        default=config.model_path,
        help=f"模型缓存路径，默认为{config.model_path}"
    )
    parser.add_argument(
        "--device", 
        type=str, 
        default=config.device,
        choices=["cpu", "cuda"], 
        help=f"计算设备，默认为{config.device}"
    )
    parser.add_argument(
        "--vad-sensitivity", 
        type=int, 
        default=config.vad_sensitivity,
        choices=[1, 2, 3], 
        help=f"VAD灵敏度 (1-低, 3-高)，默认为{config.vad_sensitivity}"
    )
    parser.add_argument(
        "--enable-funasr-update",
        action="store_true",
        help="启用FunASR模型更新检查，默认禁用"
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="只打印当前配置信息，不启动服务器"
    )
    parser.add_argument(
        "--skip-preload",
        action="store_true",
        help="跳过模型预加载，改为懒加载（不推荐）"
    )
    return parser.parse_args()


def preload_models():
    """在服务器启动前预加载模型（新的全局模型管理）"""
    from nextalk_server.funasr_model import GlobalFunASRModels
    from nextalk_server.config import get_config
    logger = logging.getLogger("nextalk.preload")
    
    logger.info("在服务器启动前预加载FunASR模型...")
    config = get_config()
    
    start_time = time.time()
    
    # 最大重试次数
    max_retries = 3
    retry_count = 0
    retry_delay = 5  # 初始重试延迟（秒）
    
    # 设置环境变量告知模型正在预加载
    os.environ["NEXTALK_MODEL_PRELOADING"] = "1"
    
    try:
        while retry_count < max_retries:
            try:
                # 使用全局单例模型管理器
                models = GlobalFunASRModels()
                models.initialize(config)
                
                elapsed_time = time.time() - start_time
                logger.info(f"FunASR模型预加载成功，耗时: {elapsed_time:.2f}秒")
                
                # 标记预加载成功
                os.environ["NEXTALK_MODEL_PRELOADED"] = "1"
                
                return True
                
            except Exception as e:
                retry_count += 1
                logger.exception(f"预加载FunASR模型时出错 (尝试 {retry_count}/{max_retries}): {str(e)}")
                print(f"预加载FunASR模型时出错: {str(e)}")
                if retry_count < max_retries:
                    logger.info(f"将在 {retry_delay} 秒后重试...")
                    print(f"将在 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)  # 使用同步sleep，因为这个函数现在是同步的
                    # 增加重试延迟，避免频繁失败
                    retry_delay *= 2
        
        # 如果所有重试都失败
        logger.critical("所有预加载尝试均失败，无法启动服务器。请检查模型配置和GPU状态。")
        return False
    finally:
        # 清除预加载标记
        os.environ.pop("NEXTALK_MODEL_PRELOADING", None)


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
    
    # 设置日志级别
    if args.debug:
        log_level = "debug"
        os.environ["NEXTALK_DEBUG"] = "1"
    else:
        log_level = args.log_level.lower()
    
    # 设置环境变量 LOG_LEVEL，这将被 app.py 中的日志配置使用
    os.environ["LOG_LEVEL"] = log_level.upper()
    
    # 设置日志
    logger = setup_logging(log_level, args.log_file)
    
    # 显示启动信息
    print("\033[1;36m=== NexTalk服务器启动 ===\033[0m")
    
    # 打印配置源文件路径
    from nextalk_server.config import INI_PATH, CONFIG_PATH, DEFAULT_CONFIG
    
    # 获取当前配置
    config = get_config()
    
    # 如果只是打印配置，则退出
    if args.print_config:
        print("\033[1;33m当前配置信息:\033[0m")
        for key, value in config.dict().items():
            print(f"\033[1;32m{key}\033[0m = \033[1;34m{value}\033[0m")
        return 0
    
    # 正常启动信息
    logger.info(f"正在启动NexTalk服务器，主机:{args.host}, 端口:{args.port}...")
    
    # 显示日志级别
    if log_level == "debug":
        print(f"\033[1;33m调试模式已启用，将显示详细日志\033[0m")
    else:
        print(f"\033[1;33m日志级别: {log_level.upper()}\033[0m")
    
    if args.log_file:
        print(f"\033[1;33m日志将保存到 {args.log_file}\033[0m")
    
    # 设置FunASR更新检查
    funasr_disable_update = not args.enable_funasr_update
    if args.enable_funasr_update:
        logger.info("FunASR模型更新检查已启用")
    else:
        logger.info("FunASR模型更新检查已禁用")
    
    # 更新配置（仅内存中，不保存到文件）
    logger.info(f"从命令行参数更新配置: host={args.host}, port={args.port}, device={args.device}, ...")
    update_config({
        "host": args.host,
        "port": args.port,
        "model_path": args.model_path,
        "device": args.device,
        "vad_sensitivity": args.vad_sensitivity,
        "funasr_disable_update": funasr_disable_update
    }, save=False)  # 明确指定不保存
    
    # 更新后再次获取配置
    config = get_config()
    
    # 强制预加载模型，忽略skip_preload选项
    if args.skip_preload:
        logger.warning("已忽略skip_preload选项，将强制预加载模型")
        print("\033[1;33m警告: 已忽略skip_preload选项，将强制预加载模型\033[0m")
    
    # 开始预加载模型
    logger.info("开始预加载模型...")
    print("\033[1;36m开始预加载模型...\033[0m")
    
    # 预加载模型
    success = preload_models()  # 现在是同步函数
    
    if not success:
        logger.critical("模型预加载失败，服务器无法启动。")
        print("\n\033[1;31m错误: 模型预加载失败，服务器无法启动。请检查日志获取详细信息。\033[0m")
        return 1
        
    # 模型已在preload_models()函数中设置了NEXTALK_MODEL_PRELOADED环境变量
    logger.info("模型预加载成功，已设置环境变量NEXTALK_MODEL_PRELOADED=1")
    print("\033[1;32m模型预加载成功，已设置环境变量NEXTALK_MODEL_PRELOADED=1\033[0m")
    
    try:
        # 使用Uvicorn运行FastAPI应用
        uvicorn.run(
            "nextalk_server.app:app", 
            host=args.host,
            port=config.port,  # 使用配置文件中的端口值而不是args.port
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