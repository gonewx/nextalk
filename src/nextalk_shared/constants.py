"""
NexTalk shared constants.

This module contains constants used throughout the NexTalk project.
"""

# Server settings
DEFAULT_SERVER_PORT = 8000

# Audio settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_FALLBACK_SAMPLE_RATES = [8000, 11025, 16000, 22050, 44100, 48000]  # 备用采样率
AUDIO_CHANNELS = 1
AUDIO_FRAME_DURATION_MS = 30
# Calculate chunk size: sample_rate * (duration_ms / 1000) * channels
AUDIO_CHUNK_SIZE = int(AUDIO_SAMPLE_RATE * (AUDIO_FRAME_DURATION_MS / 1000) * AUDIO_CHANNELS)

# 音频静音判断相关
AUDIO_SILENCE_THRESHOLD = 0.01  # 非零比例阈值，低于此值认为是静音
AUDIO_INIT_FRAME_COUNT = 10  # 音频初始化阶段的帧数，用于跳过初始静音

# FunASR 配置常量
FUNASR_DEFAULT_MODE = "2pass"  # 默认使用2pass模式，兼顾实时响应与精度
FUNASR_DEFAULT_CHUNK_SIZE = [5, 10, 5]  # 默认分块大小，对应600ms音频
FUNASR_DEFAULT_CHUNK_INTERVAL = 10  # 默认分块间隔
FUNASR_OFFLINE_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
FUNASR_ONLINE_MODEL = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online"
FUNASR_VAD_MODEL = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
FUNASR_PUNC_MODEL = "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"
FUNASR_MODEL_REVISION = "v2.0.4"  # 模型版本

# FunASR模型配置常量
FUNASR_DISABLE_UPDATE = True  # 是否禁用FunASR模型更新检查
FUNASR_DISABLE_LOG = True  # 是否禁用FunASR内部日志输出
FUNASR_DISABLE_PBAR = True  # 是否禁用FunASR进度条

# Status strings
STATUS_LISTENING = "listening"
STATUS_PROCESSING = "processing"
STATUS_IDLE = "idle"
STATUS_ERROR = "error"
STATUS_DISCONNECTED = "disconnected"
STATUS_CONNECTED = "connected"
STATUS_READY = "ready"  # 服务器模型已就绪，可以开始音频捕获
