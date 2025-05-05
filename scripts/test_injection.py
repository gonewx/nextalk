#!/usr/bin/env python3
"""
测试文本注入功能的简单脚本。

这个脚本会初始化Linux文本注入器并执行简单的文本注入测试。
"""

import sys
import logging
import time
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_injection")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='测试文本注入功能')
    parser.add_argument('--text', default='测试文本注入功能', help='要注入的文本')
    parser.add_argument('--delay', type=float, default=3.0, help='执行前的延迟秒数')
    args = parser.parse_args()
    
    print(f"准备测试文本注入功能，将在 {args.delay} 秒后注入: '{args.text}'")
    print("请确保光标位于目标输入区域...")
    
    # 倒计时
    for i in range(int(args.delay), 0, -1):
        print(f"{i}...", end='', flush=True)
        time.sleep(1)
    print("开始注入!")
    
    try:
        # 导入Linux注入器
        from nextalk_client.injection.injector_linux import LinuxInjector
        
        # 创建注入器实例
        injector = LinuxInjector()
        
        # 执行文本注入
        result = injector.inject_text(args.text)
        
        # 显示结果
        if result:
            print("\n文本注入成功!")
        else:
            print("\n文本注入失败!")
            
    except ImportError:
        logger.error("无法导入LinuxInjector，请确保已安装nextalk_client包")
        return 1
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 