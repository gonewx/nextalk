"""
NexTalk 服务器入口程序

提供NexTalk语音转文本服务器的入口点，使用FunASR模型。
"""

import argparse
import logging
import uvicorn
import os
import asyncio
import time
import sys
from logging.handlers import RotatingFileHandler

from .app import app, create_app, setup_logging
from .config import get_config, update_config
from .funasr_model import FunASRModel

# 使用统一的日志系统
logger = setup_logging().getChild("nextalk_server.main")


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 命令行参数解析器
    """
    # 获取当前配置
    config = get_config()
    
    parser = argparse.ArgumentParser(description="NexTalk 服务器 - FunASR版")
    
    # 服务器设置
    parser.add_argument("--host", type=str, default=config.host, help="服务器主机名")
    parser.add_argument("--port", type=int, default=config.port, help="服务器端口")
    parser.add_argument("--log-level", type=str, default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="日志级别")
    
    # 模型设置
    parser.add_argument("--model-path", type=str, default=config.model_path, help="模型缓存路径")
    parser.add_argument("--device", type=str, default=config.device, 
                        choices=["cpu", "cuda"], help="计算设备")
    parser.add_argument("--ngpu", type=int, default=config.ngpu, help="使用的GPU数量")
    parser.add_argument("--ncpu", type=int, default=config.ncpu, help="使用的CPU核心数")
    
    # VAD设置
    parser.add_argument("--vad-sensitivity", type=int, default=config.vad_sensitivity,
                        choices=[1, 2, 3], help="VAD灵敏度 (1-低, 3-高)")
    
    # 模型预加载选项
    parser.add_argument("--preload", action="store_true", help="在服务器启动前预加载模型")
    parser.add_argument("--skip-preload", action="store_true", help="跳过模型预加载（不推荐）")
    
    return parser


async def preload_models():
    """在服务器启动前预加载模型"""
    logger.info("在服务器启动前预加载FunASR模型...")
    config = get_config()
    model = FunASRModel(config)
    
    start_time = time.time()
    
    # 最大重试次数
    max_retries = 3
    retry_count = 0
    retry_delay = 5  # 初始重试延迟（秒）
    
    # 设置更详细的日志级别
    funasr_logger = logging.getLogger('nextalk_server.funasr_model')
    original_level = funasr_logger.level
    funasr_logger.setLevel(logging.DEBUG)
    
    try:
        while retry_count < max_retries:
            try:
                logger.info("开始第 %s 次尝试加载模型", retry_count + 1)
                
                success = await model.initialize()
                
                if success:
                    elapsed_time = time.time() - start_time
                    logger.info(f"FunASR模型预加载成功，耗时: {elapsed_time:.2f}秒")
                    return True
                else:
                    retry_count += 1
                    logger.error(f"FunASR模型预加载失败 (尝试 {retry_count}/{max_retries})")
                    if retry_count < max_retries:
                        logger.info(f"将在 {retry_delay} 秒后重试...")
                        await asyncio.sleep(retry_delay)
                        # 增加重试延迟，避免频繁失败
                        retry_delay *= 2
            except Exception as e:
                retry_count += 1
                logger.exception(f"预加载FunASR模型时出错 (尝试 {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    logger.info(f"将在 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
                    # 增加重试延迟，避免频繁失败
                    retry_delay *= 2
        
        # 如果所有重试都失败
        logger.critical("所有预加载尝试均失败，无法启动服务器。请检查模型配置和GPU状态。")
        return False
    finally:
        # 恢复原来的日志级别
        funasr_logger.setLevel(original_level)


def main() -> None:
    """主函数，服务器入口点"""
    # 解析命令行参数
    parser = create_parser()
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)
    
    # 更新配置
    update_config({
        "host": args.host,
        "port": args.port,
        "model_path": args.model_path,
        "device": args.device,
        "ngpu": args.ngpu,
        "ncpu": args.ncpu,
        "vad_sensitivity": args.vad_sensitivity
    })
    
    # 预加载标志检查，优先使用命令行参数
    should_preload = args.preload
    should_skip_preload = args.skip_preload
    
    # 如果通过脚本设置了环境变量，则检查环境变量
    if not (should_preload or should_skip_preload):
        # 如果环境变量表示已预加载，则不需要再预加载
        if os.environ.get("NEXTALK_MODEL_PRELOADED", "0") == "1":
            logger.info("检测到环境变量NEXTALK_MODEL_PRELOADED=1，模型已预加载")
            should_preload = False
        else:
            # 默认预加载
            should_preload = True
    
    # 如果需要预加载，且未明确要求跳过
    if should_preload and not should_skip_preload:
        # 预加载模型
        logger.info("开始预加载模型...")
        model_loaded = asyncio.run(preload_models())
        if not model_loaded:
            logger.critical("模型预加载失败，服务器无法启动。")
            return
        
        # 设置环境变量，表示模型已预加载
        os.environ["NEXTALK_MODEL_PRELOADED"] = "1"
    else:
        if should_skip_preload:
            logger.warning("已明确跳过模型预加载，将使用懒加载模式（不推荐）")
        os.environ["NEXTALK_MODEL_PRELOADED"] = "0"
    
    # 配置uvicorn日志，使用我们的统一日志格式
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 启动服务器
    config = get_config()
    logger.info(f"正在启动NexTalk服务器 (FunASR版): http://{config.host}:{config.port}")
    uvicorn.run(
        "nextalk_server.app:app",
        host=config.host,
        port=config.port,
        log_level=args.log_level.lower(),
        log_config=log_config
    )


if __name__ == "__main__":
    main()
