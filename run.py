#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NexTalk 便捷启动脚本
直接运行此文件启动 NexTalk
"""

import sys
import os
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
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

def check_environment():
    """检查运行环境"""
    import platform
    
    print("=" * 50)
    print("NexTalk 启动中...")
    print("=" * 50)
    print(f"Python 版本: {sys.version}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"项目路径: {project_root}")
    print("=" * 50)
    
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("错误: NexTalk 需要 Python 3.8 或更高版本")
        sys.exit(1)
    
    # 检查必要的依赖
    try:
        import websockets
        import yaml
        import pynput
        import pyautogui
        import sounddevice
        import numpy
        print("✓ 核心依赖已安装")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("\n请运行以下命令安装依赖：")
        print("  pip install -r requirements.txt")
        sys.exit(1)

def main():
    """主函数"""
    # 检查环境
    check_environment()
    
    try:
        # 导入并运行 NexTalk
        from nextalk.main import main as nextalk_main
        
        print("\n启动 NexTalk...")
        print("提示: 使用 Ctrl+C 退出\n")
        
        # 运行主程序
        return nextalk_main()
        
    except ImportError as e:
        print(f"\n错误: 无法导入 NexTalk 模块: {e}")
        print("请确保项目结构完整")
        return 1
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        return 0
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())