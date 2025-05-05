#!/usr/bin/env python3
"""
测试热键持续按下时的音频捕获功能。

这个脚本提供简单的命令行测试功能，可以模拟热键按下、释放和语音识别过程。
"""

import sys
import logging
import time
import argparse
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_hotkey")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试热键功能')
    parser.add_argument('--mode', choices=['press_hold', 'press_release', 'toggle'], 
                        default='press_hold', help='测试模式')
    args = parser.parse_args()
    
    try:
        # 导入所需模块
        from nextalk_client.client_logic import NexTalkClient
        import asyncio
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 创建客户端实例
        client = NexTalkClient()
        
        # 启动客户端
        async def setup():
            await client.start()
        
        # 运行启动
        loop.run_until_complete(setup())
        
        # 测试热键功能
        if args.mode == 'press_hold':
            # 测试按下并保持热键的情况
            print("测试热键按下并保持...")
            print("1. 激活音频监听 (模拟热键按下)")
            client._activate_listening()
            
            # 等待5秒，模拟用户说话
            time.sleep(5)
            
            print("2. 释放热键但继续监听 (模拟热键释放)")
            async def release_hotkey():
                await client._deactivate_listening()
            loop.run_until_complete(release_hotkey())
            
            # 再等待5秒，模拟语音识别完成
            time.sleep(5)
            
            # 模拟收到最终识别结果
            print("3. 模拟收到最终识别结果")
            client._handle_transcription("这是测试结果", is_final=True)
            
            # 等待停止完成
            time.sleep(2)
            
        elif args.mode == 'press_release':
            # 测试快速按下释放热键的情况
            print("测试快速按下释放热键...")
            print("1. 激活音频监听 (模拟热键按下)")
            client._activate_listening()
            
            # 快速释放热键
            print("2. 快速释放热键 (模拟热键释放)")
            async def release_hotkey():
                await client._deactivate_listening()
            loop.run_until_complete(release_hotkey())
            
            # 等待5秒，模拟用户说话和识别过程
            time.sleep(5)
            
            # 模拟收到最终识别结果
            print("3. 模拟收到最终识别结果")
            client._handle_transcription("这是快速测试结果", is_final=True)
            
            # 等待停止完成
            time.sleep(2)
            
        else:  # toggle模式
            # 测试手动切换模式
            print("测试手动切换模式...")
            print("1. 激活音频监听")
            client.toggle_listening()
            
            # 等待3秒
            time.sleep(3)
            
            # 停止监听
            print("2. 停止音频监听")
            client.toggle_listening()
            
            # 等待停止完成
            time.sleep(2)
        
        # 停止客户端
        async def cleanup():
            await client.stop()
        
        loop.run_until_complete(cleanup())
        loop.close()
            
    except ImportError:
        logger.error("无法导入NexTalkClient，请确保已安装nextalk_client包")
        return 1
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 