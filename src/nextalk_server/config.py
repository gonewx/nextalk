"""
配置模块

提供全局配置管理，用于服务器和模型设置。
"""

import os
import json
import logging
import shutil
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
    "device": "cpu",  # 'cpu' 或 'cuda:0' 等
    "ngpu": 1,
    "ncpu": 4,
    "cpu_threads": 4,
    "use_fp16": False,  # 是否使用FP16精度（仅GPU有效）
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
    # FunASR在线模型高级设置
    "encoder_chunk_look_back": 4,  # 编码器回看块数，用于提升在线识别准确度
    "decoder_chunk_look_back": 0,  # 解码器回看块数，用于提升在线识别准确度
    "chunk_size": [0, 10, 8],  # 流式识别chunk大小: [look_back, chunk_length, look_ahead] (优化版)
    "recognition_mode": "accuracy",  # 识别模式: accuracy/balanced/speed
    "enable_cache_warmup": True,  # 是否启用缓存预热
    "warmup_rounds": 3,  # 预热轮数
    # VAD高级参数
    "vad_max_start_silence_time": 200,
    "vad_sil_to_speech_time": 100, 
    "vad_speech_to_sil_time": 400,
}

# 新的统一配置路径
CONFIG_PATH = os.path.expanduser("~/.config/nextalk/server.ini")
# 旧的配置路径，用于迁移
OLD_CONFIG_PATH = os.path.expanduser("~/.nextalk/config.json")

# 改为绝对路径，确保能找到配置文件
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
INI_PATH = os.path.join(BASE_DIR, "nextalk", "config", "default_config.ini")


class Config(BaseModel):
    """配置类，保存服务器和模型设置"""

    # 服务器设置
    host: str = "127.0.0.1"
    port: int = 8000

    # 模型设置
    model_path: str = "~/.nextalk/models"
    device: str = "cpu"
    ngpu: int = 1
    ncpu: int = 4
    cpu_threads: int = 4
    use_fp16: bool = False

    # FunASR模型设置
    asr_model: str = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    asr_model_revision: str = "v2.0.4"
    asr_model_streaming: str = (
        "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"
    )
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

    # FunASR在线模型高级设置
    encoder_chunk_look_back: Optional[int] = 4  # 编码器回看块数，参考FunASR wss client的默认值
    decoder_chunk_look_back: Optional[int] = 0  # 解码器回看块数，参考FunASR wss client的默认值
    chunk_size: list = [0, 10, 8]  # 流式识别chunk大小参数(优化版)
    recognition_mode: str = "accuracy"  # 识别模式
    enable_cache_warmup: bool = True  # 缓存预热
    warmup_rounds: int = 3  # 预热轮数
    # VAD高级参数
    vad_max_start_silence_time: int = 200
    vad_sil_to_speech_time: int = 100
    vad_speech_to_sil_time: int = 400


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
    logger.debug(f"尝试从INI文件加载配置: {ini_path}")
    config = configparser.ConfigParser()
    if not os.path.exists(ini_path):
        logger.warning(f"INI配置文件不存在: {ini_path}")
        return {}

    config.read(ini_path, encoding="utf-8")
    if "Server" not in config:
        logger.warning(f"INI文件中缺少[Server]部分: {ini_path}")
        return {}

    server_cfg = dict(config["Server"])
    logger.debug(f"从INI文件读取到[Server]配置: {server_cfg}")

    # 类型转换
    result = {}
    for k, v in server_cfg.items():
        if k == "chunk_size":
            # 特殊chunk_size参数解析
            try:
                if isinstance(v, str) and "," in v:
                    result[k] = [int(x.strip()) for x in v.split(",")]
                    logger.debug(f"INI配置项解析为chunk_size列表: {k}={v} → {result[k]}")
                else:
                    logger.warning(f"chunk_size配置格式错误: {v}, 使用默认值")
                    result[k] = [0, 10, 5]
            except Exception as e:
                logger.warning(f"chunk_size解析失败: {v}, 错误: {e}, 使用默认值")
                result[k] = [0, 10, 5]
        elif k in [
            "port",
            "vad_sensitivity",
            "ngpu",
            "ncpu",
            "encoder_chunk_look_back",
            "decoder_chunk_look_back",
            "device_id",
            "warmup_rounds",
            "vad_max_start_silence_time", 
            "vad_sil_to_speech_time",
            "vad_speech_to_sil_time",
        ]:
            try:
                result[k] = int(v)
                logger.debug(f"INI配置项转换为整数: {k}={v} → {result[k]}")
            except Exception as e:
                logger.warning(f"INI配置项转换整数失败: {k}={v}, 错误: {e}")
                continue
        elif k in ["funasr_streaming", "funasr_disable_update", "use_fp16", "enable_cache_warmup"]:
            result[k] = v.lower() in ("1", "true", "yes")
            logger.debug(f"INI配置项转换为布尔值: {k}={v} → {result[k]}")
        elif k == "recognition_mode":
            result[k] = v
            logger.debug(f"INI配置项识别模式: {k}={v}")
        else:
            result[k] = v
            logger.debug(f"INI配置项保持原值: {k}={v}")

    # 应用recognition_mode预设配置
    mode = result.get('recognition_mode', 'accuracy')
    if mode == 'speed':
        # 低延迟模式
        result['chunk_size'] = [0, 10, 5]
        result['encoder_chunk_look_back'] = 0
        result['decoder_chunk_look_back'] = 1
        logger.info("应用速度优先模式: chunk_size=[0,10,5], 低延迟但准确度略低")
    elif mode == 'balanced':
        # 平衡模式
        result['chunk_size'] = [0, 10, 6]
        result['encoder_chunk_look_back'] = 1
        result['decoder_chunk_look_back'] = 1
        logger.info("应用平衡模式: chunk_size=[0,10,6], 延迟和准确度平衡")
    elif mode == 'accuracy':
        # 高准确度模式（默认）
        result['chunk_size'] = [0, 10, 8]
        result['encoder_chunk_look_back'] = 2
        result['decoder_chunk_look_back'] = 2
        logger.info("应用准确度优先模式: chunk_size=[0,10,8], 高准确度但延迟略高")
    else:
        logger.warning(f"未知的识别模式: {mode}, 使用默认accuracy模式")
        result['chunk_size'] = [0, 10, 8]
        result['encoder_chunk_look_back'] = 2
        result['decoder_chunk_look_back'] = 2

    logger.debug(f"INI配置解析结果: {result}")
    return result


def migrate_old_json_config() -> bool:
    """
    从旧的JSON配置迁移到新的INI配置

    Returns:
        bool: 是否成功迁移
    """
    if not os.path.exists(OLD_CONFIG_PATH):
        return False

    if os.path.exists(CONFIG_PATH):
        logger.debug("新配置文件已存在，跳过迁移")
        return False

    try:
        logger.info(f"开始从旧JSON配置迁移: {OLD_CONFIG_PATH} -> {CONFIG_PATH}")

        # 读取旧JSON配置
        with open(OLD_CONFIG_PATH, "r", encoding="utf-8") as f:
            old_config = json.load(f)

        # 确保目录存在
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

        # 创建INI配置
        config = configparser.ConfigParser()
        config.add_section("Server")

        # 转换配置项
        for key, value in old_config.items():
            config.set("Server", key, str(value))

        # 保存INI配置
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            config.write(f)

        logger.info(f"配置迁移成功: {CONFIG_PATH}")

        # 可选：备份旧配置文件
        backup_path = OLD_CONFIG_PATH + ".backup"
        shutil.move(OLD_CONFIG_PATH, backup_path)
        logger.info(f"旧配置文件已备份到: {backup_path}")

        return True

    except Exception as e:
        logger.error(f"配置迁移失败: {e}")
        return False


def load_config() -> Config:
    """
    加载配置，优先级：用户INI > 默认INI > DEFAULT_CONFIG
    同时支持从旧JSON配置迁移
    """
    try:
        logger.debug(f"开始加载配置...")
        logger.debug(f"默认INI配置文件路径: {INI_PATH}")
        logger.debug(f"用户INI配置文件路径: {CONFIG_PATH}")

        # 0. 尝试从旧JSON配置迁移
        migrate_old_json_config()

        # 1. 先加载默认 ini 配置
        default_ini_config = parse_ini_config(INI_PATH)
        merged_config = DEFAULT_CONFIG.copy()

        if default_ini_config:
            logger.debug(f"使用默认INI配置覆盖默认配置")
            for k, v in default_ini_config.items():
                if k in merged_config:
                    logger.debug(f"配置项从默认INI覆盖: {k}={merged_config[k]} → {v}")
                    merged_config[k] = v
                else:
                    logger.debug(f"从默认INI添加新配置项: {k}={v}")
                    merged_config[k] = v

        # 2. 再加载用户 ini 配置
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        user_ini_config = parse_ini_config(CONFIG_PATH)

        if user_ini_config:
            logger.debug(f"使用用户INI配置覆盖")
            for k, v in user_ini_config.items():
                if k in merged_config:
                    logger.debug(f"配置项从用户INI覆盖: {k}={merged_config[k]} → {v}")
                else:
                    logger.debug(f"从用户INI添加新配置项: {k}={v}")
                merged_config[k] = v
        else:
            logger.debug("用户INI配置文件不存在或为空")

        # 3. 创建配置对象并保存
        logger.debug(f"最终合并的配置: {merged_config}")
        config = Config(**merged_config)
        logger.debug(f"创建的Config对象: {config}")
        save_config(config)
        return config
    except Exception as e:
        logger.exception(f"加载配置失败: {e}，使用默认配置")
        return Config(**DEFAULT_CONFIG)


def save_config(config: Config) -> bool:
    """
    保存配置到INI文件

    Args:
        config: 配置实例

    Returns:
        bool: 是否保存成功
    """
    try:
        # 确保配置目录存在
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

        # 创建INI配置
        ini_config = configparser.ConfigParser()
        ini_config.add_section("Server")

        # 转换配置项
        config_dict = config.model_dump()
        for key, value in config_dict.items():
            if key == "chunk_size" and isinstance(value, list):
                # 特殊处理chunk_size列表
                ini_config.set("Server", key, ",".join(map(str, value)))
            else:
                ini_config.set("Server", key, str(value))

        # 保存到文件
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            ini_config.write(f)

        logger.debug(f"配置已保存到: {CONFIG_PATH}")
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
            logger.debug(f"配置项更新: {key}={getattr(config, key)} → {value}")
            setattr(config, key, value)

    # 保存更新后的配置
    save_config(config)

    # 更新全局配置实例
    global _config
    _config = config

    return config
