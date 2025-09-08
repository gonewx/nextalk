#!/usr/bin/env python3
"""
NexTalk重启脚本
优雅地重启NexTalk服务，应用最新代码修改
"""

import subprocess
import signal
import os
import sys
import time

def find_nextalk_processes():
    """查找所有NexTalk相关进程"""
    try:
        result = subprocess.run(['pgrep', '-f', 'nextalk'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return [int(pid) for pid in result.stdout.strip().split('\n') if pid]
        return []
    except Exception as e:
        print(f"Error finding processes: {e}")
        return []

def stop_nextalk():
    """停止NexTalk进程"""
    pids = find_nextalk_processes()
    if not pids:
        print("No NexTalk processes found")
        return True
    
    print(f"Found NexTalk processes: {pids}")
    
    # 发送SIGINT信号进行优雅关闭
    for pid in pids:
        try:
            print(f"Sending SIGINT to PID {pid}...")
            os.kill(pid, signal.SIGINT)
        except ProcessLookupError:
            print(f"Process {pid} already terminated")
        except Exception as e:
            print(f"Error stopping process {pid}: {e}")
    
    # 等待进程结束
    max_wait = 10  # 等待10秒
    for i in range(max_wait):
        remaining_pids = find_nextalk_processes()
        if not remaining_pids:
            print("All NexTalk processes stopped successfully")
            return True
        time.sleep(1)
        print(f"Waiting for processes to stop... ({i+1}/{max_wait})")
    
    # 强制终止剩余进程
    remaining_pids = find_nextalk_processes()
    if remaining_pids:
        print(f"Force killing remaining processes: {remaining_pids}")
        for pid in remaining_pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except:
                pass
        time.sleep(1)
    
    return True

def start_nextalk():
    """启动NexTalk"""
    try:
        print("Starting NexTalk...")
        
        # 检查FunASR服务器
        funasr_result = subprocess.run(['pgrep', '-f', 'funasr_wss_server'], capture_output=True)
        if funasr_result.returncode != 0:
            print("⚠️  Warning: FunASR server not running!")
            print("   Please start it with: python funasr_wss_server.py")
        
        # 启动NexTalk
        nextalk_process = subprocess.Popen(
            [sys.executable, '-m', 'nextalk'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"NexTalk started with PID: {nextalk_process.pid}")
        
        # 等待一下确保启动成功
        time.sleep(2)
        
        if nextalk_process.poll() is None:
            print("✅ NexTalk started successfully!")
            print("📝 Check logs with: tail -f c.log")
            return True
        else:
            stdout, stderr = nextalk_process.communicate()
            print(f"❌ NexTalk failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"Error starting NexTalk: {e}")
        return False

def main():
    """主函数"""
    print("🔄 Restarting NexTalk...")
    
    # 停止现有进程
    print("\n1. Stopping existing NexTalk processes...")
    if not stop_nextalk():
        print("❌ Failed to stop NexTalk processes")
        return False
    
    # 短暂等待
    time.sleep(1)
    
    # 启动新进程
    print("\n2. Starting NexTalk with updated code...")
    if not start_nextalk():
        print("❌ Failed to start NexTalk")
        return False
    
    print("\n✅ NexTalk restart complete!")
    print("🔧 Signal handling fix applied")
    print("🎯 Test global hotkey: Super+Space")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)