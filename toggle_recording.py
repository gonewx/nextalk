#!/usr/bin/env python3
"""
NexTalk系统快捷键触发脚本
用于Wayland环境下的全局热键支持
"""

import os
import sys
import subprocess
import signal
import time

def find_nextalk_process():
    """查找运行中的NexTalk进程"""
    try:
        result = subprocess.run(['pgrep', '-f', 'nextalk'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            return [int(pid) for pid in pids if pid]
        return []
    except Exception as e:
        print(f"Error finding NexTalk process: {e}")
        return []

def send_toggle_signal():
    """向运行中的NexTalk进程发送切换信号"""
    pids = find_nextalk_process()
    if pids:
        for pid in pids:
            try:
                # 发送SIGUSR1信号用于切换录音状态
                os.kill(pid, signal.SIGUSR1)
                print(f"Toggle signal sent to PID {pid}")
                return True
            except ProcessLookupError:
                print(f"Process {pid} not found")
            except PermissionError:
                print(f"Permission denied for process {pid}")
            except Exception as e:
                print(f"Error sending signal to {pid}: {e}")
    return False

def start_nextalk():
    """启动NexTalk"""
    try:
        nextalk_dir = "/mnt/disk0/project/newx/nextalk/nextalk_v3"
        os.chdir(nextalk_dir)
        
        # 检查FunASR服务器是否运行
        funasr_result = subprocess.run(['pgrep', '-f', 'funasr_wss_server'], capture_output=True)
        if funasr_result.returncode != 0:
            print("FunASR服务器未运行，请先启动：python funasr_wss_server.py")
            return False
        
        # 启动NexTalk
        subprocess.Popen([sys.executable, '-m', 'nextalk'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        print("NexTalk started")
        return True
    except Exception as e:
        print(f"Error starting NexTalk: {e}")
        return False

def main():
    """主函数"""
    # 首先尝试向现有进程发送切换信号
    if send_toggle_signal():
        return
    
    # 如果没有运行的进程，启动NexTalk
    print("No running NexTalk process found, attempting to start...")
    start_nextalk()

if __name__ == "__main__":
    main()