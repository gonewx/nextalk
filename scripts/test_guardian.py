#!/usr/bin/env python3
"""
测试进程守护器 - 防止测试进程僵死

用法:
python scripts/test_guardian.py --timeout 300 -- python -m pytest tests/
python scripts/test_guardian.py --timeout 60 -- make test-quick
"""

import sys
import os
import signal
import subprocess
import time
import threading
import argparse
from pathlib import Path


class TestGuardian:
    """测试进程守护器"""
    
    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.process = None
        self.timer = None
        self.start_time = None
        
    def timeout_handler(self):
        """超时处理器"""
        if self.process and self.process.poll() is None:
            print(f"\n⚠️  测试进程超时 ({self.timeout}秒)，强制终止...", file=sys.stderr)
            
            # 首先尝试温和终止
            try:
                if os.name == 'posix':
                    # Unix系统：发送SIGTERM给进程组
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    # Windows系统
                    self.process.terminate()
                
                # 等待5秒让进程正常终止
                try:
                    self.process.wait(timeout=5)
                    print("✅ 进程已正常终止", file=sys.stderr)
                except subprocess.TimeoutExpired:
                    print("⚠️  进程未响应SIGTERM，发送SIGKILL...", file=sys.stderr)
                    
                    # 强制杀死
                    if os.name == 'posix':
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                    
                    self.process.wait()
                    print("💀 进程已强制终止", file=sys.stderr)
                    
            except Exception as e:
                print(f"❌ 终止进程时出错: {e}", file=sys.stderr)
        
        # 退出守护进程
        sys.exit(124)  # 特殊退出码表示超时
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            print(f"\n🛑 收到信号 {signum}，转发给测试进程...", file=sys.stderr)
            if self.process and self.process.poll() is None:
                try:
                    if os.name == 'posix':
                        os.killpg(os.getpgid(self.process.pid), signum)
                    else:
                        self.process.send_signal(signum)
                except Exception as e:
                    print(f"转发信号失败: {e}", file=sys.stderr)
            sys.exit(130)  # SIGINT 的标准退出码
        
        if os.name == 'posix':
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
    
    def run_command(self, command: list) -> int:
        """运行命令并监控"""
        print(f"🚀 启动测试进程: {' '.join(command)}")
        print(f"⏱️  超时设置: {self.timeout}秒")
        
        self.start_time = time.time()
        
        # 设置信号处理
        self.setup_signal_handlers()
        
        # 启动超时定时器
        self.timer = threading.Timer(self.timeout, self.timeout_handler)
        self.timer.start()
        
        try:
            # 启动进程（创建新的进程组）
            if os.name == 'posix':
                self.process = subprocess.Popen(
                    command,
                    preexec_fn=os.setsid,  # 创建新的会话和进程组
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
            else:
                self.process = subprocess.Popen(
                    command,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
            
            # 等待进程完成
            exit_code = self.process.wait()
            
            # 取消定时器
            if self.timer.is_alive():
                self.timer.cancel()
            
            elapsed = time.time() - self.start_time
            print(f"\n✅ 测试完成，耗时 {elapsed:.1f}秒，退出码: {exit_code}")
            
            return exit_code
            
        except KeyboardInterrupt:
            print("\n🛑 用户中断测试", file=sys.stderr)
            if self.timer.is_alive():
                self.timer.cancel()
            return 130
            
        except Exception as e:
            print(f"\n❌ 运行测试时出错: {e}", file=sys.stderr)
            if self.timer.is_alive():
                self.timer.cancel()
            return 1


def main():
    parser = argparse.ArgumentParser(
        description="测试进程守护器 - 防止测试进程僵死",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/test_guardian.py --timeout 300 -- python -m pytest tests/
  python scripts/test_guardian.py --timeout 60 -- make test-quick
  python scripts/test_guardian.py --timeout 120 -- python -m pytest tests/integration/ -v
        """
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=300,
        help='超时时间（秒），默认300秒'
    )
    
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help='要执行的测试命令'
    )
    
    args = parser.parse_args()
    
    # 处理 -- 分隔符
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]
    
    if not args.command:
        parser.error("必须提供要执行的命令")
    
    # 验证命令
    if not args.command[0]:
        parser.error("命令不能为空")
    
    # 创建守护器并运行
    guardian = TestGuardian(timeout=args.timeout)
    exit_code = guardian.run_command(args.command)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()