#!/usr/bin/env python3
"""
NexTalk模型下载工具

此脚本用于手动下载和管理Whisper模型，解决自动下载失败的问题。
支持查看可用模型、下载模型和检查已下载模型。
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("模型下载器")

# 模型下载相关常量
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/NexTalk/models")
MODELS_LIST = [
    'tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 
    'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 
    'distil-large-v2', 'distil-medium.en', 'distil-small.en', 'distil-large-v3', 
    'large-v3-turbo', 'turbo'
]

def get_available_models() -> List[str]:
    """获取所有可用的模型列表"""
    try:
        from faster_whisper.utils import available_models
        models = available_models()
        return models
    except Exception as e:
        logger.error(f"获取可用模型列表失败: {str(e)}")
        return MODELS_LIST  # 使用备选列表

def check_downloaded_models(cache_dir: str) -> List[str]:
    """检查已经下载的模型"""
    downloaded = []
    cache_path = Path(cache_dir)
    
    if not cache_path.exists():
        return []
    
    # 检查faster-whisper目录下的模型
    whisper_cache = cache_path / "models--guillaumekln--faster-whisper"
    if whisper_cache.exists() and whisper_cache.is_dir():
        for model_dir in whisper_cache.glob("models--guillaumekln--faster-whisper-*"):
            if model_dir.is_dir():
                model_name = model_dir.name.replace("models--guillaumekln--faster-whisper-", "")
                downloaded.append(model_name)
    
    return downloaded

def download_model(model_name: str, cache_dir: str, force: bool = False) -> bool:
    """
    下载指定的模型
    
    Args:
        model_name: 模型名称，如"large-v3"
        cache_dir: 缓存目录
        force: 是否强制重新下载
        
    Returns:
        下载是否成功
    """
    # 确保目录存在
    os.makedirs(cache_dir, exist_ok=True)
    
    try:
        # 确保库已安装
        import huggingface_hub
        import faster_whisper
    except ImportError:
        print("错误: 缺少必要的依赖库。请安装以下包:")
        print("  pip install faster-whisper huggingface-hub")
        return False
        
    try:
        logger.info(f"开始下载模型: {model_name}")
        
        if model_name not in MODELS_LIST:
            logger.error(f"无效的模型名称: {model_name}")
            print(f"可用的模型有: {', '.join(get_available_models())}")
            return False
        
        # 使用huggingface-hub下载模型
        from huggingface_hub import snapshot_download, logging as hf_logging
        hf_logging.set_verbosity_info()
        
        # 在large和turbo使用别名的情况处理
        if model_name == "large":
            actual_model = "large-v3"
        elif model_name == "turbo":
            actual_model = "large-v3-turbo"
        else:
            actual_model = model_name
        
        # 构建仓库ID
        repo_id = f"Systran/faster-whisper-{actual_model}"
        
        print(f"从Hugging Face下载模型: {repo_id}")
        model_path = snapshot_download(
            repo_id=repo_id,
            local_dir=os.path.join(cache_dir, model_name),
            force_download=force
        )
        
        logger.info(f"模型 {model_name} 下载成功! 保存在: {model_path}")
        return True
    except Exception as e:
        logger.error(f"下载模型 {model_name} 失败: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="NexTalk Whisper模型下载工具")
    parser.add_argument("--list", action="store_true", help="列出所有可用模型")
    parser.add_argument("--check", action="store_true", help="检查已下载的模型")
    parser.add_argument("--download", type=str, help="下载指定模型，例如 large-v3")
    parser.add_argument("--cache-dir", type=str, default=DEFAULT_CACHE_DIR, 
                        help=f"模型缓存目录 (默认: {DEFAULT_CACHE_DIR})")
    parser.add_argument("--force", action="store_true", help="强制重新下载模型")
    args = parser.parse_args()
    
    # 如果没有参数，显示帮助信息
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # 列出可用模型
    if args.list:
        models = get_available_models()
        if models:
            print("\n可用的Whisper模型:")
            for model in models:
                print(f"  - {model}")
            print()
        else:
            print("无法获取可用模型列表")
    
    # 检查已下载模型
    if args.check:
        downloaded = check_downloaded_models(args.cache_dir)
        if downloaded:
            print(f"\n已下载的模型 (目录: {args.cache_dir}):")
            for model in downloaded:
                print(f"  - {model}")
            print()
        else:
            print(f"在 {args.cache_dir} 目录中未找到已下载的模型")
    
    # 下载模型
    if args.download:
        model_name = args.download
        print(f"开始下载模型 {model_name} 到 {args.cache_dir}")
        success = download_model(model_name, args.cache_dir, args.force)
        if success:
            print(f"模型 {model_name} 下载成功!")
        else:
            print(f"模型 {model_name} 下载失败。请检查网络连接和模型名称。")
            sys.exit(1)

if __name__ == "__main__":
    main() 