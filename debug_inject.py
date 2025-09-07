#!/usr/bin/env python3
"""
调试文本注入功能的简单测试脚本
"""

import time
import subprocess
import pyautogui
import pyperclip
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_active_window():
    """获取当前活动窗口信息"""
    try:
        # 获取窗口标题
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=1
        )
        window_title = result.stdout.strip() if result.returncode == 0 else "Unknown"
        
        # 获取进程名
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            capture_output=True, text=True, timeout=1
        )
        if result.returncode == 0:
            pid = int(result.stdout.strip())
            try:
                import psutil
                process = psutil.Process(pid)
                app_name = process.name()
                return window_title, app_name
            except:
                return window_title, "Unknown"
        
        return window_title, "Unknown"
    except Exception as e:
        logger.error(f"获取窗口信息失败: {e}")
        return "Unknown", "Unknown"

def test_clipboard_injection(text="测试文本注入"):
    """测试剪贴板注入"""
    logger.info(f"开始测试剪贴板注入: '{text}'")
    
    # 获取当前窗口信息
    window_title, app_name = get_active_window()
    logger.info(f"当前窗口: {window_title} (进程: {app_name})")
    
    # 保存原剪贴板内容
    original_clipboard = pyperclip.paste()
    logger.info(f"原剪贴板内容: '{original_clipboard[:50]}...'")
    
    try:
        # 复制到剪贴板
        pyperclip.copy(text)
        logger.info("已复制到剪贴板")
        
        # 等待用户切换到目标窗口
        print("\n请在3秒内切换到目标窗口（终端或编辑器）...")
        for i in range(3, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n开始注入！")
        
        # 获取当前窗口信息
        window_title, app_name = get_active_window()
        logger.info(f"目标窗口: {window_title} (进程: {app_name})")
        
        # 执行粘贴
        pyautogui.hotkey("ctrl", "v")
        logger.info("已执行 Ctrl+V")
        
        time.sleep(0.5)
        
        # 恢复剪贴板
        pyperclip.copy(original_clipboard)
        logger.info("已恢复原剪贴板内容")
        
        return True
        
    except Exception as e:
        logger.error(f"注入失败: {e}")
        # 恢复剪贴板
        try:
            pyperclip.copy(original_clipboard)
        except:
            pass
        return False

if __name__ == "__main__":
    print("=== NexTalk 文本注入调试工具 ===")
    print("这个工具将帮助诊断文本注入问题")
    print()
    
    # 测试剪贴板注入
    success = test_clipboard_injection("今天天气真好")
    
    print(f"\n注入结果: {'成功' if success else '失败'}")
    
    if not success:
        print("\n可能的问题:")
        print("1. 目标应用不支持 Ctrl+V 粘贴")
        print("2. 目标应用需要不同的粘贴快捷键")
        print("3. 焦点切换时间不足")
        print("4. 权限或安全限制")