"""
NexTalk客户端配置加载器。

该模块提供了加载客户端配置的功能，支持从用户配置文件或默认值中读取设置。
"""

import os
import logging
import configparser
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, List


# 设置日志记录器
logger = logging.getLogger(__name__)


class Config:
    """配置访问器类，提供面向对象的配置访问接口。"""
    
    def __init__(self, config_data: Dict[str, Dict[str, str]] = None, config_path: Optional[str] = None):
        """
        初始化配置访问器。
        
        Args:
            config_data: 可选的配置数据字典
            config_path: 可选的配置文件路径
        """
        if config_data is None:
            self._config = load_config(config_path)
        else:
            self._config = config_data
            
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值。
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        if section not in self._config:
            return default
        
        section_config = self._config[section]
        return section_config.get(key, default)
    
    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """
        获取布尔配置值。
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认布尔值
            
        Returns:
            bool: 配置的布尔值
        """
        return get_bool_config(self._config, section, key, default)
    
    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """
        获取整数配置值。
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认整数值
            
        Returns:
            int: 配置的整数值
        """
        value = self.get(section, key, default)
        if isinstance(value, int):
            return value
        
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"无法转换为整数的配置: [{section}].{key}={value}，使用默认值: {default}")
            return default
    
    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        """
        获取浮点数配置值。
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认浮点数值
            
        Returns:
            float: 配置的浮点数值
        """
        value = self.get(section, key, default)
        if isinstance(value, float):
            return value
        
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"无法转换为浮点数的配置: [{section}].{key}={value}，使用默认值: {default}")
            return default
    
    def get_list(self, section: str, key: str, default: List[str] = None, delimiter: str = ',') -> List[str]:
        """
        获取列表配置值（以分隔符分隔的字符串）。
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认列表值
            delimiter: 分隔符
            
        Returns:
            List[str]: 配置的列表值
        """
        if default is None:
            default = []
            
        value = self.get(section, key, None)
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        
        if not isinstance(value, str):
            logger.warning(f"无法转换为列表的配置: [{section}].{key}={value}，使用默认值: {default}")
            return default
        
        return [item.strip() for item in value.split(delimiter) if item.strip()]
    
    def client(self) -> Dict[str, str]:
        """
        获取客户端配置部分。
        
        Returns:
            Dict[str, str]: 客户端配置字典
        """
        return self._config.get('Client', {})
    
    def server(self) -> Dict[str, str]:
        """
        获取服务器配置部分。
        
        Returns:
            Dict[str, str]: 服务器配置字典
        """
        return self._config.get('Server', {})
    
    def client_bool(self, key: str, default: bool = False) -> bool:
        """
        获取客户端布尔配置值。
        
        Args:
            key: 配置键名
            default: 默认布尔值
            
        Returns:
            bool: 配置的布尔值
        """
        return self.get_bool('Client', key, default)
    
    def server_bool(self, key: str, default: bool = False) -> bool:
        """
        获取服务器布尔配置值。
        
        Args:
            key: 配置键名
            default: 默认布尔值
            
        Returns:
            bool: 配置的布尔值
        """
        return self.get_bool('Server', key, default)


# 全局配置实例
_config_instance = None


def get_config() -> Config:
    """
    获取全局配置实例。
    
    Returns:
        Config: 配置访问器实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


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
                logger.debug(f"已从用户配置文件加载配置: {user_config_path}")
        except Exception as e:
            logger.error(f"读取用户配置文件时出错: {str(e)}")
    else:
        logger.debug(f"用户配置文件不存在: {user_config_path}")
    
    # 步骤2: 加载默认配置文件
    if os.path.exists(package_config_path):
        try:
            files_read = default_config.read(package_config_path)
            if files_read:
                loaded_configs.append(package_config_path)
                logger.debug(f"已加载默认配置文件: {package_config_path}")
                
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


def get_bool_config(config: Dict[str, Any], section: str, key: str, default: bool = False) -> bool:
    """
    从配置中获取布尔值，正确处理字符串表示的布尔值。
    
    支持的真值：'true', 'yes', '1', 't', 'y'（不区分大小写）
    支持的假值：'false', 'no', '0', 'f', 'n'（不区分大小写）
    
    Args:
        config: 包含配置的字典
        section: 配置节名
        key: 配置键名
        default: 默认布尔值，当键不存在或无法识别时返回
        
    Returns:
        bool: 配置的布尔值
    """
    if section not in config:
        return default
    
    section_config = config[section]
    if key not in section_config:
        return default
    
    value = section_config[key]
    
    # 如果已经是布尔类型，直接返回
    if isinstance(value, bool):
        return value
    
    # 处理字符串形式的布尔值
    if isinstance(value, str):
        true_values = ('true', 'yes', '1', 't', 'y')
        false_values = ('false', 'no', '0', 'f', 'n')
        
        value_lower = value.lower()
        
        if value_lower in true_values:
            return True
        if value_lower in false_values:
            return False
    
    # 如果无法识别，返回默认值
    logger.warning(f"无法识别为布尔值的配置: [{section}].{key}={value}，使用默认值: {default}")
    return default


def get_client_bool_config(key: str, default: bool = False) -> bool:
    """
    获取客户端部分的布尔配置值。
    
    Args:
        key: 配置键名
        default: 默认布尔值
        
    Returns:
        bool: 配置的布尔值
    """
    config = load_config()
    return get_bool_config(config, 'Client', key, default)


def get_server_bool_config(key: str, default: bool = False) -> bool:
    """
    获取服务器部分的布尔配置值。
    
    Args:
        key: 配置键名
        default: 默认布尔值
        
    Returns:
        bool: 配置的布尔值
    """
    config = load_config()
    return get_bool_config(config, 'Server', key, default)


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