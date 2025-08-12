#!/usr/bin/env python3
"""
测试新的智能文本注入器。

运行此脚本以测试不同的注入方法。
"""

import time
import logging
import sys
from src.nextalk_client.injection import get_injector, IMEDetector, SmartInjector

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ime_detection():
    """测试输入法检测。"""
    print("\n=== 测试输入法检测 ===")
    ime_type = IMEDetector.detect_ime()
    print(f"检测到的输入法: {ime_type}")
    
    priority = IMEDetector.get_ime_priority_list()
    print(f"输入法优先级列表: {priority}")
    print()

def test_smart_injector():
    """测试智能注入器。"""
    print("\n=== 测试智能注入器 ===")
    
    injector = SmartInjector()
    if injector.is_available():
        status = injector.get_status()
        print(f"智能注入器状态:")
        print(f"  - 可用: {status['available']}")
        print(f"  - 注入器数量: {status['injector_count']}")
        print(f"  - 主要注入器: {status['primary_injector']}")
        print(f"  - 所有注入器: {status['all_injectors']}")
        
        # 测试注入
        print("\n准备在5秒后注入测试文本...")
        print("请将光标放在文本编辑器中...")
        for i in range(5, 0, -1):
            print(f"{i}...")
            time.sleep(1)
            
        test_text = "测试智能注入器：Hello, 你好！"
        success = injector.inject_text(test_text)
        
        if success:
            print("✓ 文本注入成功！")
        else:
            print("✗ 文本注入失败")
    else:
        print("✗ 智能注入器不可用")
    print()

def test_legacy_injector():
    """测试旧版注入器（兼容性）。"""
    print("\n=== 测试旧版注入器 ===")
    
    injector = get_injector(use_smart=False, legacy=True)
    if injector:
        print("旧版注入器已创建")
        
        # 测试注入
        print("\n准备在5秒后注入测试文本...")
        print("请将光标放在文本编辑器中...")
        for i in range(5, 0, -1):
            print(f"{i}...")
            time.sleep(1)
            
        test_text = "测试旧版注入器：Legacy test"
        success = injector.inject_text(test_text)
        
        if success:
            print("✓ 文本注入成功！")
        else:
            print("✗ 文本注入失败")
    else:
        print("✗ 无法创建旧版注入器")
    print()

def test_default_injector():
    """测试默认注入器。"""
    print("\n=== 测试默认注入器 ===")
    
    injector = get_injector()
    if injector:
        print(f"默认注入器类型: {type(injector).__name__}")
        
        # 测试注入
        print("\n准备在5秒后注入测试文本...")
        print("请将光标放在文本编辑器中...")
        for i in range(5, 0, -1):
            print(f"{i}...")
            time.sleep(1)
            
        test_text = "默认注入器测试：Default test 默认测试"
        success = injector.inject_text(test_text)
        
        if success:
            print("✓ 文本注入成功！")
        else:
            print("✗ 文本注入失败")
    else:
        print("✗ 无法创建默认注入器")
    print()

def main():
    """主函数。"""
    print("=" * 50)
    print("NexTalk 智能文本注入器测试")
    print("=" * 50)
    
    # 测试输入法检测
    test_ime_detection()
    
    # 询问用户要测试哪个注入器
    print("\n选择要测试的注入器:")
    print("1. 智能注入器（推荐）")
    print("2. 旧版注入器")
    print("3. 默认注入器")
    print("4. 全部测试")
    print("0. 退出")
    
    choice = input("\n请输入选择 (0-4): ").strip()
    
    if choice == '1':
        test_smart_injector()
    elif choice == '2':
        test_legacy_injector()
    elif choice == '3':
        test_default_injector()
    elif choice == '4':
        test_smart_injector()
        test_legacy_injector()
        test_default_injector()
    elif choice == '0':
        print("退出测试")
        sys.exit(0)
    else:
        print("无效选择")
        
    print("\n测试完成！")

if __name__ == "__main__":
    main()