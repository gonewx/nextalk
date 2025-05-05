#!/usr/bin/env python
"""
FunASR客户端演示脚本

该脚本展示如何使用NexTalk的FunASR客户端捕获麦克风音频
并使用FunASR服务器进行实时转录。
"""

import asyncio
import logging
import argparse
import os
import sys
import signal

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.nextalk_client.audio.capture import AudioCapturer
from src.nextalk_client.network.funasr_client import FunASRWebSocketClient
from src.nextalk_shared.constants import (
    FUNASR_DEFAULT_MODE,
    FUNASR_DEFAULT_CHUNK_SIZE,
    FUNASR_DEFAULT_CHUNK_INTERVAL
)

# 设置日志格式
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FunASRDemo")

# 结束时的标志
is_running = True

def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    global is_running
    print("\n正在停止演示...")
    is_running = False

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def handle_transcription(result):
    """处理转录结果"""
    text = result.get("text", "")
    mode = result.get("mode", "")
    is_final = result.get("is_final", False)
    
    # 2pass模式在线部分为临时结果，不最终显示
    if mode == "2pass-online":
        sys.stdout.write(f"\r临时结果: {text}")
        sys.stdout.flush()
    elif mode == "2pass-offline":
        print(f"\n最终结果: {text}")
    else:
        # 在线或离线模式
        if is_final:
            print(f"\n最终结果({mode}): {text}")
        else:
            sys.stdout.write(f"\r临时结果({mode}): {text}")
            sys.stdout.flush()


def handle_error(result):
    """处理错误消息"""
    message = result.get("message", "未知错误")
    print(f"\n错误: {message}")


def handle_disconnect():
    """处理与服务器断开连接"""
    global is_running
    print("\n与服务器的连接已断开")
    is_running = False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="FunASR客户端演示")
    parser.add_argument("--url", type=str, default="ws://localhost:8010/ws/funasr",
                       help="FunASR WebSocket服务器URL")
    parser.add_argument("--mode", type=str, default=FUNASR_DEFAULT_MODE,
                       choices=["offline", "online", "2pass"],
                       help="转录模式")
    parser.add_argument("--ssl", action="store_true", 
                       help="使用SSL连接")
    parser.add_argument("--device", type=int, default=None,
                       help="音频输入设备索引（默认使用系统默认设备）")
    args = parser.parse_args()
    
    # 创建FunASR客户端
    client = FunASRWebSocketClient()
    
    # 配置客户端
    client.configure(
        mode=args.mode,
        chunk_size=FUNASR_DEFAULT_CHUNK_SIZE,
        chunk_interval=FUNASR_DEFAULT_CHUNK_INTERVAL
    )
    
    # 注册回调函数
    client.register_callbacks(
        message_callback=handle_transcription,
        error_callback=handle_error,
        disconnect_callback=handle_disconnect
    )
    
    # 创建音频捕获器
    audio_capturer = AudioCapturer()
    
    # 列出可用设备
    devices = audio_capturer.list_devices()
    print("可用的音频输入设备:")
    for i, device in enumerate(devices):
        print(f"  [{device['index']}] {device['name']}")
    
    # 选择设备
    device_index = args.device
    if device_index is None:
        print(f"使用系统默认音频输入设备")
    else:
        device_found = any(device['index'] == device_index for device in devices)
        if not device_found:
            print(f"未找到设备索引 {device_index}，将使用系统默认设备")
            device_index = None
        else:
            # 如果找到指定设备，选择它
            device_name = next((device['name'] for device in devices if device['index'] == device_index), "未知设备")
            print(f"已选择音频设备: [{device_index}] {device_name}")
    
    # 只有在明确指定设备时才调用select_device
    if device_index is not None:
        if not audio_capturer.select_device(device_index):
            print("选择音频设备失败，将尝试使用系统默认设备")
    
    # 连接到服务器
    print(f"正在连接到服务器: {args.url}")
    if not await client.connect(args.url, use_ssl=args.ssl):
        print("连接到服务器失败")
        return
    
    print(f"已连接到服务器，使用模式: {args.mode}")
    print("开始捕获音频...")
    print("按Ctrl+C停止演示")
    
    # 配置FunASR参数
    client.configure(
        mode=args.mode, 
        chunk_size=FUNASR_DEFAULT_CHUNK_SIZE,
        chunk_interval=FUNASR_DEFAULT_CHUNK_INTERVAL,
        wav_name="demo_recording"
    )
    
    # 开始音频捕获
    global is_running
    
    # 音频回调函数
    async def audio_callback(data):
        if not is_running:
            return
        
        if client.is_connected():
            await client.send_audio(data)
    
    # 启动音频流
    def sync_audio_callback(data):
        # 创建一个新的事件循环来处理异步回调
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(audio_callback(data))
        finally:
            loop.close()
    
    if not audio_capturer.start_stream(sync_audio_callback):
        print("启动音频流失败")
        await client.disconnect()
        return
    
    # 运行直到结束
    try:
        while is_running:
            await asyncio.sleep(0.1)
    finally:
        # 停止捕获
        print("\n停止音频捕获...")
        audio_capturer.stop_stream()
        
        # 设置不再说话标志并等待最终结果
        print("等待最终结果...")
        if client.is_connected():
            await client.set_speaking_state(False)
            await asyncio.sleep(2)  # 等待最终结果
        
        # 断开连接
        print("断开与服务器的连接...")
        await client.disconnect()
        print("演示已结束")


if __name__ == "__main__":
    asyncio.run(main()) 