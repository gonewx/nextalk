"""
配置模块

提供全局配置管理，用于服务器和模型设置。
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel
import configparser

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    # 服务器设置
    "host": "127.0.0.1",
    "port": 8010,
    
    # 模型设置
    "model_path": "~/.nextalk/models",
    "temp_dir": "~/.nextalk/temp",
    "device": "cpu",  # 'cpu' 或 'cuda'
    "ngpu": 1,
    "ncpu": 4,
    "cpu_threads": 4,
    "compute_type": "float16",  # 'float16', 'float32', 'int8'等
    
    # FunASR模型设置
    "asr_model": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "asr_model_revision": "v2.0.4",
    "asr_model_streaming": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online",
    "asr_model_streaming_revision": "v2.0.4",
    "vad_model": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "vad_model_revision": "v2.0.4",
    "punc_model": "iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727",
    "punc_model_revision": "v2.0.4",
    "model_cache_dir": "~/.nextalk/models",
    "device_id": 0,
    
    # VAD设置
    "vad_sensitivity": 2,  # 1-3，数值越大灵敏度越高
    
    # FunASR设置
    "funasr_disable_update": True,  # 是否禁用FunASR更新检查
}

CONFIG_PATH = os.path.expanduser("~/.nextalk/config.json")

# 改为绝对路径，确保能找到配置文件
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
INI_PATH = os.path.join(BASE_DIR, "nextalk", "config", "default_config.ini")


class Config(BaseModel):
    """配置类，保存服务器和模型设置"""
    
    # 服务器设置
    host: str = "127.0.0.1"
    port: int = 8000
    
    # 模型设置
    model_path: str = "~/.nextalk/models"
    temp_dir: str = "~/.nextalk/temp"
    device: str = "cpu"
    ngpu: int = 1
    ncpu: int = 4
    cpu_threads: int = 4
    compute_type: str = "float16"
    
    # FunASR模型设置
    asr_model: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    asr_model_revision: str = "v2.0.4"
    asr_model_streaming: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"
    asr_model_streaming_revision: str = "v2.0.4"
    vad_model: str = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
    vad_model_revision: str = "v2.0.4"
    punc_model: str = "iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727"
    punc_model_revision: str = "v2.0.4"
    model_cache_dir: str = "~/.nextalk/models"
    device_id: int = 0
    
    # VAD设置
    vad_sensitivity: int = 2
    
    # FunASR设置
    funasr_disable_update: bool = True


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例
    
    Returns:
        Config: 配置实例
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def parse_ini_config(ini_path: str) -> dict:
    """
    解析 ini 文件，返回 [Server] 配置字典，类型自动转换
    """
    logger.info(f"尝试从INI文件加载配置: {ini_path}")
    config = configparser.ConfigParser()
    if not os.path.exists(ini_path):
        logger.warning(f"INI配置文件不存在: {ini_path}")
        return {}
    
    config.read(ini_path, encoding="utf-8")
    if "Server" not in config:
        logger.warning(f"INI文件中缺少[Server]部分: {ini_path}")
        return {}
    
    server_cfg = dict(config["Server"])
    logger.info(f"从INI文件读取到[Server]配置: {server_cfg}")
    
    # 类型转换
    result = {}
    for k, v in server_cfg.items():
        if k in ["port", "vad_sensitivity", "ngpu", "ncpu"]:
            try:
                result[k] = int(v)
                logger.info(f"INI配置项转换为整数: {k}={v} → {result[k]}")
            except Exception as e:
                logger.warning(f"INI配置项转换整数失败: {k}={v}, 错误: {e}")
                continue
        elif k in ["funasr_streaming"]:
            result[k] = v.lower() in ("1", "true", "yes")
            logger.info(f"INI配置项转换为布尔值: {k}={v} → {result[k]}")
        else:
            result[k] = v
            logger.info(f"INI配置项保持原值: {k}={v}")
    
    logger.info(f"INI配置解析结果: {result}")
    return result


def load_config() -> Config:
    """
    加载配置，优先级：ini > json > DEFAULT_CONFIG
    """
    try:
        logger.info(f"开始加载配置...")
        logger.info(f"INI配置文件路径: {INI_PATH}")
        logger.info(f"JSON配置文件路径: {CONFIG_PATH}")
        
        # 1. 先加载 ini 配置
        ini_config = parse_ini_config(INI_PATH)
        merged_config = DEFAULT_CONFIG.copy()
        
        if ini_config:
            logger.info(f"使用INI配置覆盖默认配置")
            for k, v in ini_config.items():
                if k in merged_config:
                    logger.info(f"配置项从INI覆盖: {k}={merged_config[k]} → {v}")
                    merged_config[k] = v
                else:
                    logger.info(f"从INI添加新配置项: {k}={v}")
                    merged_config[k] = v
        else:
            logger.warning("未能加载INI配置或INI配置为空")

        # 2. 再加载 json 覆盖
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                logger.info(f"从JSON文件加载配置: {CONFIG_PATH}")
                logger.info(f"JSON配置内容: {config_data}")
                
                for k, v in config_data.items():
                    if k in merged_config:
                        logger.info(f"配置项从JSON覆盖: {k}={merged_config[k]} → {v}")
                    else:
                        logger.info(f"从JSON添加新配置项: {k}={v}")
                
                merged_config.update(config_data)
        else:
            logger.info("JSON配置文件不存在，跳过加载")

        # 3. 创建配置对象并保存
        logger.info(f"最终合并的配置: {merged_config}")
        config = Config(**merged_config)
        logger.info(f"创建的Config对象: {config}")
        save_config(config)
        return config
    except Exception as e:
        logger.exception(f"加载配置失败: {e}，使用默认配置")
        return Config(**DEFAULT_CONFIG)


def save_config(config: Config) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置实例
        
    Returns:
        bool: 是否保存成功
    """
    try:
        # 确保配置目录存在
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        
        # 保存到文件
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, indent=4, ensure_ascii=False)
            
        logger.info(f"配置已保存到: {CONFIG_PATH}")
        return True
        
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False


def update_config(config_updates: Dict[str, Any]) -> Config:
    """
    更新配置
    
    Args:
        config_updates: 要更新的配置项
        
    Returns:
        Config: 更新后的配置实例
    """
    config = get_config()
    
    # 更新配置
    for key, value in config_updates.items():
        if hasattr(config, key):
            logger.info(f"配置项更新: {key}={getattr(config, key)} → {value}")
            setattr(config, key, value)
    
    # 保存更新后的配置
    save_config(config)
    
    # 更新全局配置实例
    global _config
    _config = config
    
    return config 