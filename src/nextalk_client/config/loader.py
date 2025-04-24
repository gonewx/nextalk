"""
NexTalk客户端配置加载器。

该模块提供了加载客户端配置的功能，支持从用户配置文件或默认值中读取设置。
"""

import os
import logging
import configparser
import shutil
from pathlib import Path
from typing import Dict, Any, Optional


# 设置日志记录器
logger = logging.getLogger(__name__)


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载客户端配置。
    
    加载顺序:
    1. 首先尝试从指定路径或默认用户配置文件(~/.config/nextalk/config.ini)加载配置。
    2. 对于缺失的键，从应用打包的默认配置文件(config/default_config.ini)加载。
    3. 如果仍有缺失的键，使用内置默认值。
    
    Args:
        config_path: 可选的配置文件路径，如果不提供则使用默认路径
        
    Returns:
        包含配置键值对的字典
    """
    # 初始化配置解析器
    config = configparser.ConfigParser()
    default_config = configparser.ConfigParser()
    
    # 定义内置默认配置值
    builtin_defaults = {
        'Client': {
            'hotkey': 'ctrl+shift+space',
            'server_url': 'ws://127.0.0.1:8000/ws/stream',
            'locale': 'en',
        },
        'Server': {
            'default_model': 'small.en-int8',
            'vad_sensitivity': '2',
            'device': 'cuda',
            'compute_type': 'int8',
        }
    }
    
    # 定义配置文件路径
    if config_path is None:
        user_config_path = os.path.expanduser("~/.config/nextalk/config.ini")
    else:
        user_config_path = config_path
        
    # 获取打包的默认配置文件路径
    package_config_path = Path(__file__).parents[3] / "config" / "default_config.ini"
    
    # 跟踪已加载的配置文件
    loaded_configs = []
    
    # 步骤1: 尝试加载用户配置文件
    if os.path.exists(user_config_path):
        try:
            files_read = config.read(user_config_path)
            if files_read:
                loaded_configs.append(user_config_path)
                logger.info(f"已从用户配置文件加载配置: {user_config_path}")
        except Exception as e:
            logger.error(f"读取用户配置文件时出错: {str(e)}")
    else:
        logger.info(f"用户配置文件不存在: {user_config_path}")
    
    # 步骤2: 加载默认配置文件
    if os.path.exists(package_config_path):
        try:
            files_read = default_config.read(package_config_path)
            if files_read:
                loaded_configs.append(package_config_path)
                logger.info(f"已加载默认配置文件: {package_config_path}")
                
                # 填充用户配置中缺失的部分
                for section in default_config.sections():
                    if not config.has_section(section):
                        config.add_section(section)
                        
                    for key, value in default_config[section].items():
                        if key not in config[section]:
                            config.set(section, key, value)
                            logger.debug(f"从默认配置中添加缺失的设置: [{section}].{key}={value}")
        except Exception as e:
            logger.error(f"读取默认配置文件时出错: {str(e)}")
    else:
        logger.warning(f"默认配置文件不存在: {package_config_path}")
    
    # 步骤3: 确保所有内置默认值都存在
    for section, options in builtin_defaults.items():
        if not config.has_section(section):
            config.add_section(section)
            
        for key, value in options.items():
            if key not in config[section]:
                config.set(section, key, value)
                logger.debug(f"使用内置默认值: [{section}].{key}={value}")
    
    if not loaded_configs:
        logger.warning("未能加载任何配置文件，仅使用内置默认值")
    
    # 将配置转换为字典并返回
    result = {}
    for section in config.sections():
        result[section] = dict(config[section])
        
    return result


def get_client_config() -> Dict[str, Any]:
    """
    获取仅客户端部分的配置。
    
    返回:
        包含客户端配置的字典
    """
    config = load_config()
    return config.get('Client', {})


def get_server_config() -> Dict[str, Any]:
    """
    获取仅服务器部分的配置。
    
    返回:
        包含服务器配置的字典
    """
    config = load_config()
    return config.get('Server', {})


def ensure_config_directory() -> bool:
    """
    确保配置目录存在。
    
    创建~/.config/nextalk/目录（如果不存在）。
    
    返回:
        bool: 如果目录已存在或成功创建则为True，否则为False
    """
    config_dir = os.path.expanduser("~/.config/nextalk")
    try:
        os.makedirs(config_dir, exist_ok=True)
        logger.info(f"已确保配置目录存在: {config_dir}")
        return True
    except Exception as e:
        logger.error(f"创建配置目录时出错: {str(e)}")
        return False


def create_default_user_config() -> bool:
    """
    在用户配置目录创建默认配置文件。
    
    如果用户配置文件不存在，将默认配置文件复制到~/.config/nextalk/config.ini。
    
    返回:
        bool: 如果文件已存在或成功创建则为True，否则为False
    """
    user_config_path = os.path.expanduser("~/.config/nextalk/config.ini")
    
    # 如果用户配置文件已存在，不进行操作
    if os.path.exists(user_config_path):
        logger.info(f"用户配置文件已存在: {user_config_path}")
        return True
    
    # 确保配置目录存在
    if not ensure_config_directory():
        return False
    
    # 获取打包的默认配置文件路径
    package_config_path = Path(__file__).parents[3] / "config" / "default_config.ini"
    
    if os.path.exists(package_config_path):
        try:
            shutil.copy2(package_config_path, user_config_path)
            logger.info(f"已创建用户配置文件: {user_config_path}")
            return True
        except Exception as e:
            logger.error(f"创建用户配置文件时出错: {str(e)}")
            return False
    else:
        # 如果默认配置文件不存在，则从内置默认值创建
        try:
            config = configparser.ConfigParser()
            
            # 使用内置默认值
            config.add_section('Client')
            config.set('Client', 'hotkey', 'ctrl+shift+space')
            config.set('Client', 'server_url', 'ws://127.0.0.1:8000/ws/stream')
            config.set('Client', 'locale', 'en')
            
            config.add_section('Server')
            config.set('Server', 'default_model', 'small.en-int8')
            config.set('Server', 'vad_sensitivity', '2')
            config.set('Server', 'device', 'cuda')
            config.set('Server', 'compute_type', 'int8')
            
            with open(user_config_path, 'w', encoding='utf-8') as f:
                config.write(f)
                
            logger.info(f"已从内置默认值创建用户配置文件: {user_config_path}")
            return True
        except Exception as e:
            logger.error(f"从内置默认值创建用户配置文件时出错: {str(e)}")
            return False 