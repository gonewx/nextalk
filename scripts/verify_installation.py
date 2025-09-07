#!/usr/bin/env python
"""
NexTalk 安装验证脚本
检查系统环境和依赖是否正确安装
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from typing import Tuple, List

# 颜色输出支持
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    
    @staticmethod
    def disable():
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.BLUE = ''
        Colors.END = ''

# Windows 不支持 ANSI 颜色
if platform.system() == 'Windows':
    Colors.disable()

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BLUE}{'=' * 50}{Colors.END}")
    print(f"{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 50}{Colors.END}")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗{Colors.END} {text}")

def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        return False, f"Python {version_str} (需要 3.8+)"
    
    return True, f"Python {version_str}"

def check_module(module_name: str, display_name: str = None) -> Tuple[bool, str]:
    """检查 Python 模块是否安装"""
    display = display_name or module_name
    
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'unknown')
        return True, f"{display} {version}"
    except ImportError:
        return False, f"{display} 未安装"

def check_required_modules() -> List[Tuple[bool, str]]:
    """检查必需的 Python 模块"""
    modules = [
        ('websockets', 'WebSockets'),
        ('yaml', 'PyYAML'),
        ('pynput', 'pynput'),
        ('pyautogui', 'PyAutoGUI'),
        ('pyperclip', 'pyperclip'),
        ('sounddevice', 'sounddevice'),
        ('numpy', 'NumPy'),
    ]
    
    results = []
    for module_name, display_name in modules:
        results.append(check_module(module_name, display_name))
    
    return results

def check_optional_modules() -> List[Tuple[bool, str]]:
    """检查可选的 Python 模块"""
    modules = [
        ('PyQt6', 'PyQt6 (GUI)'),
        ('PIL', 'Pillow (图像处理)'),
    ]
    
    results = []
    for module_name, display_name in modules:
        results.append(check_module(module_name, display_name))
    
    return results

def check_audio_devices() -> Tuple[bool, str]:
    """检查音频设备"""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            return False, "未找到麦克风设备"
        
        default_input = sd.query_devices(kind='input')
        return True, f"找到 {len(input_devices)} 个输入设备 (默认: {default_input['name']})"
    
    except Exception as e:
        return False, f"无法检查音频设备: {e}"

def check_network() -> Tuple[bool, str]:
    """检查网络连接"""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True, "网络连接正常"
    except:
        return False, "无法连接到互联网"

def check_permissions() -> List[Tuple[bool, str]]:
    """检查系统权限"""
    results = []
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        # 检查辅助功能权限
        try:
            result = subprocess.run(
                ['osascript', '-e', 'tell application "System Events" to get name of first process'],
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                results.append((True, "辅助功能权限已授予"))
            else:
                results.append((False, "需要辅助功能权限（系统偏好设置 > 安全性与隐私）"))
        except:
            results.append((False, "无法检查辅助功能权限"))
    
    elif system == 'Linux':
        # 检查 X11 或 Wayland
        display = os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')
        if display:
            results.append((True, f"显示服务器: {display}"))
        else:
            results.append((False, "未检测到 X11 或 Wayland 显示服务器"))
    
    elif system == 'Windows':
        # Windows 通常不需要特殊权限
        results.append((True, "Windows 平台无需特殊权限"))
    
    return results

def check_config_file() -> Tuple[bool, str]:
    """检查配置文件"""
    config_paths = [
        Path.cwd() / "config" / "nextalk.yaml",
        Path.home() / ".config" / "nextalk" / "config.yaml",
        Path.home() / "Library" / "Application Support" / "nextalk" / "config.yaml",
        Path(os.environ.get('APPDATA', '')) / "nextalk" / "config.yaml",
    ]
    
    for path in config_paths:
        if path.exists():
            return True, f"配置文件: {path}"
    
    return False, "未找到配置文件（将使用默认配置）"

def check_funasr_server() -> Tuple[bool, str]:
    """检查 FunASR 服务器连接"""
    try:
        import websockets
        import asyncio
        
        async def test_connection():
            try:
                async with websockets.connect(
                    "ws://127.0.0.1:10095",
                    timeout=2
                ) as ws:
                    return True
            except:
                return False
        
        connected = asyncio.run(test_connection())
        
        if connected:
            return True, "FunASR 服务器连接成功"
        else:
            return False, "无法连接到 FunASR 服务器 (ws://127.0.0.1:10095)"
    
    except Exception as e:
        return False, f"测试连接失败: {e}"

def check_nextalk_installation() -> Tuple[bool, str]:
    """检查 NexTalk 是否已安装"""
    try:
        import nextalk
        version = getattr(nextalk, '__version__', '0.1.0')
        return True, f"NexTalk {version} 已安装"
    except ImportError:
        return False, "NexTalk 未安装"

def main():
    """主函数"""
    print_header("NexTalk 安装验证")
    
    all_passed = True
    
    # 系统信息
    print(f"\n系统信息:")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  架构: {platform.machine()}")
    print(f"  主机名: {platform.node()}")
    
    # Python 版本
    print(f"\n基础环境:")
    passed, message = check_python_version()
    if passed:
        print_success(message)
    else:
        print_error(message)
        all_passed = False
    
    # NexTalk 安装
    passed, message = check_nextalk_installation()
    if passed:
        print_success(message)
    else:
        print_warning(message)
    
    # 必需模块
    print(f"\n必需依赖:")
    for passed, message in check_required_modules():
        if passed:
            print_success(message)
        else:
            print_error(message)
            all_passed = False
    
    # 可选模块
    print(f"\n可选依赖:")
    for passed, message in check_optional_modules():
        if passed:
            print_success(message)
        else:
            print_warning(message)
    
    # 系统检查
    print(f"\n系统检查:")
    
    # 音频设备
    passed, message = check_audio_devices()
    if passed:
        print_success(message)
    else:
        print_error(message)
        all_passed = False
    
    # 网络连接
    passed, message = check_network()
    if passed:
        print_success(message)
    else:
        print_warning(message)
    
    # 系统权限
    for passed, message in check_permissions():
        if passed:
            print_success(message)
        else:
            print_warning(message)
    
    # 配置文件
    passed, message = check_config_file()
    if passed:
        print_success(message)
    else:
        print_warning(message)
    
    # FunASR 服务器
    passed, message = check_funasr_server()
    if passed:
        print_success(message)
    else:
        print_warning(message)
    
    # 总结
    print_header("验证结果")
    
    if all_passed:
        print_success("所有必需组件已正确安装！")
        print("\n您可以运行以下命令启动 NexTalk:")
        print(f"  {Colors.GREEN}nextalk{Colors.END}")
        return 0
    else:
        print_error("某些必需组件未正确安装")
        print("\n请安装缺失的依赖:")
        print(f"  {Colors.YELLOW}pip install -r requirements.txt{Colors.END}")
        return 1

if __name__ == "__main__":
    sys.exit(main())