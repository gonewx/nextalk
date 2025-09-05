"""
FunASR模型模块

提供全局单例FunASR模型管理，按照官方示例的方式进行模型管理。
"""

import logging
import time
import numpy as np
from typing import Dict, Any, Optional

# 使用全局日志配置
logger = logging.getLogger("nextalk_server.funasr_model")

# 检查FunASR是否可用
try:
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except ImportError:
    logger.warning("FunASR模块不可用，请安装FunASR依赖")
    FUNASR_AVAILABLE = False


class GlobalFunASRModels:
    """全局单例FunASR模型管理类，按照官方示例的全局变量方式管理模型"""
    
    _instance: Optional['GlobalFunASRModels'] = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化全局模型变量"""
        if not hasattr(self, 'model_asr'):
            # 全局模型变量（按官方示例命名）
            self.model_asr: Optional[AutoModel] = None
            self.model_asr_streaming: Optional[AutoModel] = None
            self.model_vad: Optional[AutoModel] = None
            self.model_punc: Optional[AutoModel] = None
            
            logger.debug("初始化全局FunASR模型变量")
    
    def initialize(self, config):
        """同步初始化所有模型（按官方示例方式）"""
        if self._initialized:
            logger.info("模型已初始化，跳过重复初始化")
            return
            
        try:
            logger.info("model loading")
            start_time = time.time()
            
            if not FUNASR_AVAILABLE:
                raise ImportError("FunASR不可用，请安装FunASR依赖")
            
            # 按照官方示例的方式加载模型
            # ASR 离线模型
            self.model_asr = AutoModel(
                model=getattr(config, 'asr_model', 'iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'),
                ngpu=getattr(config, 'ngpu', 1),
                ncpu=getattr(config, 'ncpu', 4),
                device=getattr(config, 'device', 'cuda'),
                disable_pbar=True,
                disable_log=True,
            )
            
            # ASR 在线模型  
            self.model_asr_streaming = AutoModel(
                model=getattr(config, 'asr_model_online', 'iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online'),
                ngpu=getattr(config, 'ngpu', 1),
                ncpu=getattr(config, 'ncpu', 4),
                device=getattr(config, 'device', 'cuda'),
                disable_pbar=True,
                disable_log=True,
            )
            
            # VAD 模型 - 添加VAD优化参数
            vad_kwargs = {
                "max_start_silence_time": getattr(config, 'vad_max_start_silence_time', 500),
                "lookback_time_start_point": getattr(config, 'vad_lookback_time_start_point', 600), 
                "sil_to_speech_time_thres": getattr(config, 'vad_sil_to_speech_time', 80),
                "speech_to_sil_time_thres": getattr(config, 'vad_speech_to_sil_time', 150),
                "max_end_silence_time": getattr(config, 'vad_max_end_silence_time', 800),
                "speech_noise_thres": getattr(config, 'vad_speech_noise_thres', 0.4),
            }
            
            logger.info(f"🎛️  VAD优化参数: {vad_kwargs}")
            
            self.model_vad = AutoModel(
                model=getattr(config, 'vad_model', 'iic/speech_fsmn_vad_zh-cn-16k-common-pytorch'),
                vad_kwargs=vad_kwargs,
                ngpu=getattr(config, 'ngpu', 1),
                ncpu=getattr(config, 'ncpu', 4),
                device=getattr(config, 'device', 'cuda'),
                disable_pbar=True,
                disable_log=True,
            )
            
            # 标点模型（可选）
            punc_model_path = getattr(config, 'punc_model', 'iic/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727')
            if punc_model_path and punc_model_path.strip() != "":
                self.model_punc = AutoModel(
                    model=punc_model_path,
                    ngpu=getattr(config, 'ngpu', 1),
                    ncpu=getattr(config, 'ncpu', 4),
                    device=getattr(config, 'device', 'cuda'),
                    disable_pbar=True,
                    disable_log=True,
                )
            else:
                self.model_punc = None
            
            self._initialized = True
            duration = time.time() - start_time
            logger.info(f"model loaded! 初始化耗时: {duration:.2f}秒")
            logger.info("only support one client at the same time now!!!!")
            
        except Exception as e:
            logger.error(f"模型初始化失败: {str(e)}")
            self._initialized = False
            raise
    
    def is_initialized(self) -> bool:
        """检查模型是否已初始化"""
        return self._initialized


# 完全按照官方示例实现VAD函数
async def async_vad(websocket, audio_in):
    """VAD处理 - 完全按照官方示例实现"""
    models = GlobalFunASRModels()
    if not models.is_initialized():
        raise RuntimeError("模型尚未初始化")
    
    # 调试：记录VAD输入
    audio_len_ms = len(audio_in) // 32  # 16kHz, 16-bit = 32 bytes per ms
    logger.debug(f"🎙️  VAD处理: {len(audio_in)}字节 ({audio_len_ms}ms)")
    
    # 按照官方示例：使用websocket.status_dict_vad参数
    segments_result = models.model_vad.generate(input=audio_in, **websocket.status_dict_vad)[0]["value"]
    logger.debug(f"🎙️  VAD原始结果: {segments_result}")

    speech_start = -1
    speech_end = -1

    # 按照官方示例：只处理单个语音段，多段或空结果直接返回-1,-1
    if len(segments_result) == 0 or len(segments_result) > 1:
        logger.debug(f"🔇 VAD跳过: 检测到{len(segments_result)}个语音段")
        return speech_start, speech_end
    
    # 按照官方示例：处理单个语音段
    if segments_result[0][0] != -1:
        speech_start = segments_result[0][0]
        logger.info(f"🎤 VAD检测语音开始: {speech_start}ms")
    if segments_result[0][1] != -1:
        speech_end = segments_result[0][1]  
        logger.info(f"🤐 VAD检测语音结束: {speech_end}ms")
        
    return speech_start, speech_end


async def async_asr(websocket, audio_in):
    """直接移植官方的async_asr函数，添加调试日志"""
    models = GlobalFunASRModels()
    if not models.is_initialized():
        raise RuntimeError("模型尚未初始化")
    
    # 调试：记录离线ASR输入
    audio_len_ms = len(audio_in) // 32 if len(audio_in) > 0 else 0
    logger.debug(f"🎯 ASR离线处理: {len(audio_in)}字节 ({audio_len_ms}ms)")
        
    if len(audio_in) > 0:
        rec_result = models.model_asr.generate(input=audio_in, **websocket.status_dict_asr)[0]
        
        # 调试：记录原始识别结果
        raw_text = rec_result.get("text", "")
        logger.debug(f"📝 ASR离线原始结果: '{raw_text}'")
        
        if models.model_punc is not None and len(rec_result["text"]) > 0:
            rec_result = models.model_punc.generate(
                input=rec_result["text"], **websocket.status_dict_punc
            )[0]
            logger.debug(f"📝 ASR离线标点后结果: '{rec_result.get('text', '')}'")
            
        if len(rec_result["text"]) > 0:
            mode = "2pass-offline" if "2pass" in websocket.mode else websocket.mode
            message = {
                "mode": mode,
                "text": rec_result["text"],
                "wav_name": getattr(websocket, 'wav_name', 'microphone'),
                "is_final": not websocket.is_speaking,
            }
            
            # 添加协议要求的可选字段
            if "timestamp" in rec_result:
                message["timestamp"] = rec_result["timestamp"]
            if "stamp_sents" in rec_result:
                message["stamp_sents"] = rec_result["stamp_sents"]
            
            logger.info(f"📤 发送离线结果: {mode} - '{rec_result['text']}'")
            import json
            await websocket.send_text(json.dumps(message))
        else:
            logger.debug(f"🤐 ASR离线无结果输出")
    else:
        logger.debug(f"❌ ASR离线收到空音频数据")
        mode = "2pass-offline" if "2pass" in websocket.mode else websocket.mode
        message = {
            "mode": mode,
            "text": "",
            "wav_name": websocket.wav_name,
            "is_final": not websocket.is_speaking,
        }
        
        import json
        await websocket.send_text(json.dumps(message))    


async def async_asr_online(websocket, audio_in):
    """直接移植官方的async_asr_online函数，添加调试日志"""
    models = GlobalFunASRModels()
    if not models.is_initialized():
        raise RuntimeError("模型尚未初始化")
    
    # 调试：记录在线ASR输入
    audio_len_ms = len(audio_in) // 32 if len(audio_in) > 0 else 0
    is_final = websocket.status_dict_asr_online.get("is_final", False)
    logger.debug(f"⚡ ASR在线处理: {len(audio_in)}字节 ({audio_len_ms}ms) is_final={is_final}")
        
    if len(audio_in) > 0:
        rec_result = models.model_asr_streaming.generate(
            input=audio_in, **websocket.status_dict_asr_online
        )[0]
        
        # 调试：记录流式识别状态
        raw_text = rec_result.get("text", "")
        logger.debug(f"⚡ ASR在线原始结果: '{raw_text}'")
        
        if websocket.mode == "2pass" and websocket.status_dict_asr_online.get("is_final", False):
            logger.debug(f"⚡ ASR在线跳过最终结果（2pass模式）")
            return
            
        if len(rec_result["text"]):
            mode = "2pass-online" if "2pass" in websocket.mode else websocket.mode
            message = {
                "mode": mode,
                "text": rec_result["text"],
                "wav_name": websocket.wav_name,
                "is_final": not websocket.is_speaking,
            }
            
            logger.info(f"📤 发送在线结果: {mode} - '{rec_result['text']}'")
            import json
            await websocket.send_text(json.dumps(message))
        else:
            logger.debug(f"🤐 ASR在线无结果输出")
    else:
        logger.debug(f"❌ ASR在线收到空音频数据")