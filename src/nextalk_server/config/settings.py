"""
NexTalk服务器配置设置。

该模块定义了服务器的配置变量，使用Pydantic的BaseSettings实现环境变量加载和类型验证。
同时支持从用户配置文件和默认配置文件加载设置。
"""

import os
import logging
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from nextalk_shared.constants import DEFAULT_SERVER_PORT

# 设置日志记录器
logger = logging.getLogger(__name__)

class ServerSettings(BaseSettings):
    """服务器配置设置。
    
    这个类定义了NexTalk服务器的配置选项，按以下优先级加载：
    1. 环境变量
    2. 用户配置文件 (~/.config/nextalk/server_config.ini)
    3. 默认配置文件 (config/default_config.ini)
    4. 类定义中的默认值
    """
    
    # Whisper模型设置
    model_size: str = "small.en"  # 使用小型英语模型
    device: str = "cuda"  # 使用GPU加速("cuda")，如果没有GPU则用"cpu"
    compute_type: str = "int8"  # 计算类型，int8量化提供好的性能和准确性平衡
    
    # 语音活动检测(VAD)设置
    vad_sensitivity: int = 2  # 灵敏度范围0-3，值越大越敏感
    
    # 模型文件路径
    model_path: str = Field(
        default=os.path.expanduser("~/.cache/NexTalk/models"),
        description="Whisper模型文件存储的路径"
    )
    
    # 服务器网络设置
    port: int = DEFAULT_SERVER_PORT  # 默认服务器端口
    host: str = "127.0.0.1"  # 默认绑定到本地地址
    
    model_config = {
        "env_prefix": "NEXTALK_",  # 环境变量前缀，例如NEXTALK_PORT=8080
        "case_sensitive": False,   # 环境变量不区分大小写
        "extra": "allow"           # 允许额外输入
    }
        
    def __init__(self, **kwargs):
        """
        初始化服务器设置，支持从多个来源加载配置。
        
        加载顺序:
        1. 命令行参数或kwargs传入的值
        2. 环境变量
        3. 用户配置文件
        4. 默认配置文件
        5. 类定义中的默认值
        """
        # 从配置文件加载设置
        config_values = self._load_from_config_files()
        
        # 合并配置值和kwargs(保持kwargs的优先级)
        merged_kwargs = {**config_values, **kwargs}
        
        # 调用父类初始化方法，处理环境变量等
        super().__init__(**merged_kwargs)
        
        logger.info(f"服务器配置已加载: 端口={self.port}, 模型={self.model_size}, 设备={self.device}")
    
    def _load_from_config_files(self) -> Dict[str, Any]:
        """
        从配置文件加载服务器设置。
        
        返回：
            从配置文件加载的设置字典
        """
        # 初始化配置解析器
        config = configparser.ConfigParser()
        
        # 定义配置文件路径
        user_config_path = os.path.expanduser("~/.config/nextalk/server_config.ini")
        default_config_path = Path(__file__).parents[3] / "config" / "default_config.ini"
        
        # 加载用户配置文件
        user_config_loaded = False
        if os.path.exists(user_config_path):
            try:
                files_read = config.read(user_config_path)
                if files_read:
                    user_config_loaded = True
                    logger.info(f"已从用户配置文件加载设置: {user_config_path}")
            except Exception as e:
                logger.error(f"读取用户配置文件时出错: {str(e)}")
        
        # 如果没有用户配置文件，尝试从默认配置加载
        if not user_config_loaded and os.path.exists(default_config_path):
            try:
                files_read = config.read(default_config_path)
                if files_read:
                    logger.info(f"已从默认配置文件加载设置: {default_config_path}")
            except Exception as e:
                logger.error(f"读取默认配置文件时出错: {str(e)}")
        
        # 提取服务器配置部分
        result = {}
        if 'Server' in config:
            for key, value in config['Server'].items():
                # 根据字段类型转换值
                field_type = self.__annotations__.get(key, str)
                if field_type == int:
                    result[key] = int(value)
                elif field_type == float:
                    result[key] = float(value)
                elif field_type == bool:
                    result[key] = value.lower() in ('true', 'yes', '1', 'on')
                else:
                    result[key] = value
        
        return result
    
    def save_to_user_config(self) -> bool:
        """
        保存当前配置到用户配置文件。
        
        返回：
            保存是否成功
        """
        user_config_path = os.path.expanduser("~/.config/nextalk/server_config.ini")
        config_dir = os.path.dirname(user_config_path)
        
        # 确保配置目录存在
        try:
            os.makedirs(config_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建配置目录时出错: {str(e)}")
            return False
        
        # 创建配置解析器并添加服务器部分
        config = configparser.ConfigParser()
        config.add_section('Server')
        
        # 将当前设置写入配置
        for key, value in self.dict().items():
            config.set('Server', key, str(value))
        
        # 写入文件
        try:
            with open(user_config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            logger.info(f"已保存配置到用户配置文件: {user_config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件时出错: {str(e)}")
            return False


def create_server_config_if_missing() -> bool:
    """
    如果用户服务器配置文件不存在，则创建一个。
    
    返回：
        创建是否成功
    """
    user_config_path = os.path.expanduser("~/.config/nextalk/server_config.ini")
    
    # 如果配置文件已存在，不进行操作
    if os.path.exists(user_config_path):
        return True
    
    # 获取默认配置
    settings = ServerSettings()
    return settings.save_to_user_config()


# 实例化默认设置
settings = ServerSettings() 