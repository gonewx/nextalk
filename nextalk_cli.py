#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NexTalk 命令行界面
不依赖 GUI 组件的简单客户端
"""

import sys
import locale

# 设置默认编码为 UTF-8
if sys.platform == "win32":
    import codecs
    # Windows 下强制使用 UTF-8
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
else:
    # Unix/Linux 系统设置 locale
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            pass  # 忽略 locale 设置失败

import asyncio
import signal
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from nextalk.audio import AudioCaptureManager
from nextalk.network.ws_client import WebSocketClient
from nextalk.input.hotkey import HotkeyManager
from nextalk.output.text_injector import TextInjector
from nextalk.config.manager import ConfigManager


class SimpleCLIClient:
    """简单的命令行客户端"""
    
    def __init__(self, config_path: str = "config/nextalk.yaml"):
        """初始化客户端"""
        logger.info("初始化 NexTalk CLI 客户端...")
        
        # 加载配置
        self.config = ConfigManager.load(config_path)
        
        # 初始化组件
        self.audio_capture = AudioCaptureManager(
            sample_rate=self.config.get("audio.sample_rate", 16000),
            channels=self.config.get("audio.channels", 1)
        )
        
        self.ws_client = WebSocketClient(
            url=f"ws://{self.config.get('server.host', '127.0.0.1')}:{self.config.get('server.port', 10095)}"
        )
        
        self.text_injector = TextInjector()
        self.hotkey_manager = HotkeyManager()
        
        self.is_recording = False
        self.running = True
        
    async def connect(self):
        """连接到服务器"""
        logger.info("连接到 FunASR 服务器...")
        try:
            await self.ws_client.connect()
            logger.info("✓ 已连接到服务器")
            return True
        except Exception as e:
            logger.error(f"✗ 连接失败: {e}")
            return False
    
    async def start_recording(self):
        """开始录音"""
        if not self.is_recording:
            self.is_recording = True
            logger.info("🎙️ 开始录音...")
            self.audio_capture.start_capture()
    
    async def stop_recording(self):
        """停止录音"""
        if self.is_recording:
            self.is_recording = False
            logger.info("⏹️ 停止录音")
            self.audio_capture.stop_capture()
    
    async def handle_recognition_result(self, text: str):
        """处理识别结果"""
        if text:
            logger.info(f"📝 识别结果: {text}")
            # 注入文本到光标位置
            self.text_injector.inject_text(text)
    
    async def run(self):
        """运行客户端"""
        # 连接服务器
        if not await self.connect():
            return
        
        # 设置信号处理
        def signal_handler(sig, frame):
            logger.info("\n正在关闭...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print("\n" + "=" * 50)
        print(" NexTalk CLI - 语音识别客户端")
        print("=" * 50)
        print("\n命令:")
        print("  r/record  - 开始/停止录音")
        print("  q/quit    - 退出程序")
        print("  h/help    - 显示帮助")
        print("\n")
        
        # 主循环
        while self.running:
            try:
                # 简单的命令行交互
                cmd = input("NexTalk> ").strip().lower()
                
                if cmd in ['q', 'quit', 'exit']:
                    break
                elif cmd in ['r', 'record']:
                    if self.is_recording:
                        await self.stop_recording()
                    else:
                        await self.start_recording()
                elif cmd in ['h', 'help']:
                    print("命令列表:")
                    print("  r/record - 切换录音状态")
                    print("  q/quit   - 退出程序")
                elif cmd:
                    print(f"未知命令: {cmd}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"错误: {e}")
        
        # 清理
        await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        
        if self.is_recording:
            await self.stop_recording()
        
        await self.ws_client.disconnect()
        self.hotkey_manager.stop_listening()
        
        logger.info("✓ 已退出")


async def main():
    """主函数"""
    client = SimpleCLIClient()
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n已退出")
    except Exception as e:
        logger.error(f"程序错误: {e}")
        sys.exit(1)