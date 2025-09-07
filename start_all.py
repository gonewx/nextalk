#!/usr/bin/env python
"""
NexTalk 一键启动脚本
自动启动 FunASR 服务器和 NexTalk 客户端
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path
import threading
import platform

# 项目根目录
ROOT_DIR = Path(__file__).parent.resolve()

# 全局进程列表
processes = []

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print(" NexTalk 语音识别系统 - 一键启动")
    print("=" * 60)
    print()

def check_dependencies():
    """检查必要的依赖"""
    print("检查依赖...")
    
    required = ["funasr", "websockets", "yaml", "pynput", "sounddevice"]
    missing = []
    
    for module in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"✗ 缺少依赖: {', '.join(missing)}")
        print("\n请运行以下命令安装：")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    print("✓ 所有依赖已安装")
    return True

def start_funasr_server():
    """启动 FunASR 服务器"""
    print("\n启动 FunASR 语音识别服务器...")
    print("-" * 40)
    
    server_script = ROOT_DIR / "funasr_wss_server.py"
    
    if not server_script.exists():
        print(f"✗ 找不到服务器脚本: {server_script}")
        return None
    
    # 启动服务器进程
    try:
        if platform.system() == "Windows":
            # Windows 使用 CREATE_NEW_CONSOLE 创建新控制台窗口
            process = subprocess.Popen(
                [sys.executable, str(server_script)],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Unix 系统
            process = subprocess.Popen(
                [sys.executable, str(server_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 在后台线程中读取输出
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(f"[服务器] {line.rstrip()}")
                        if "model loaded" in line.lower():
                            print("\n✓ FunASR 服务器就绪！")
            
            thread = threading.Thread(target=read_output, daemon=True)
            thread.start()
        
        # 等待服务器启动
        print("等待服务器加载模型（首次运行需要下载，请耐心等待）...")
        
        # 给服务器一些启动时间
        for i in range(30):  # 最多等待 30 秒
            time.sleep(1)
            if process.poll() is not None:
                print("✗ 服务器启动失败")
                return None
            
            # 检查服务器是否就绪（简单的端口检查）
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 10095))
                sock.close()
                if result == 0:
                    print("✓ 服务器端口已开放")
                    break
            except:
                pass
        
        return process
        
    except Exception as e:
        print(f"✗ 启动服务器失败: {e}")
        return None

def start_nextalk_client():
    """启动 NexTalk 客户端"""
    print("\n启动 NexTalk 客户端...")
    print("-" * 40)
    
    # 尝试多种启动方式
    start_commands = [
        [sys.executable, "-m", "nextalk"],
        [sys.executable, str(ROOT_DIR / "nextalk" / "main.py")],
        [sys.executable, str(ROOT_DIR / "run.py")],
    ]
    
    for cmd in start_commands:
        try:
            if platform.system() == "Windows":
                # Windows 创建新控制台窗口
                process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(ROOT_DIR)
                )
            else:
                # Unix 系统
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    cwd=str(ROOT_DIR)
                )
                
                # 在后台线程中读取输出
                def read_output():
                    for line in iter(process.stdout.readline, ''):
                        if line:
                            print(f"[客户端] {line.rstrip()}")
                
                thread = threading.Thread(target=read_output, daemon=True)
                thread.start()
            
            print("✓ NexTalk 客户端已启动")
            return process
            
        except Exception as e:
            continue
    
    print("✗ 无法启动 NexTalk 客户端")
    return None

def signal_handler(signum, frame):
    """处理中断信号"""
    print("\n\n正在关闭...")
    cleanup()
    sys.exit(0)

def cleanup():
    """清理进程"""
    global processes
    
    for process in processes:
        if process and process.poll() is None:
            try:
                if platform.system() == "Windows":
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except:
                try:
                    process.kill()
                except:
                    pass
    
    print("✓ 所有进程已关闭")

def main():
    """主函数"""
    global processes
    
    # 打印横幅
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动 FunASR 服务器
    server_process = start_funasr_server()
    if server_process:
        processes.append(server_process)
    else:
        print("\n✗ 无法启动 FunASR 服务器")
        return 1
    
    # 等待一下确保服务器完全启动
    time.sleep(3)
    
    # 启动 NexTalk 客户端
    client_process = start_nextalk_client()
    if client_process:
        processes.append(client_process)
    else:
        print("\n✗ 无法启动 NexTalk 客户端")
        cleanup()
        return 1
    
    print("\n" + "=" * 60)
    print(" ✓ NexTalk 系统已成功启动！")
    print("=" * 60)
    print("\n使用说明：")
    print("  • 按 Ctrl+Alt+Space 开始/停止语音识别")
    print("  • 按 Ctrl+Alt+C 清除识别结果")
    print("  • 按 Ctrl+Alt+Q 退出程序")
    print("  • 按 Ctrl+C 关闭所有进程")
    print("\n系统正在运行中...")
    
    try:
        # 等待进程结束
        while True:
            # 检查进程状态
            all_alive = True
            for process in processes:
                if process.poll() is not None:
                    all_alive = False
                    break
            
            if not all_alive:
                print("\n有进程已退出，正在关闭系统...")
                break
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n接收到中断信号...")
    
    finally:
        cleanup()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)