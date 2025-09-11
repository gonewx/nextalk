#!/usr/bin/env python3
"""
测试进程清理工具 - 清理可能僵死的测试进程

用法:
python scripts/cleanup_test_processes.py              # 交互式清理
python scripts/cleanup_test_processes.py --force      # 强制清理所有相关进程
python scripts/cleanup_test_processes.py --check      # 仅检查，不清理
"""

import sys
import os
import psutil
import argparse
import signal
import time
from typing import List, Dict


class TestProcessCleaner:
    """测试进程清理器"""
    
    def __init__(self):
        self.test_keywords = [
            'pytest',
            'test_guardian',
            'safe_test_runner',
            'nextalk',
            'python -m pytest',
            'python -m nextalk'
        ]
        
        self.dangerous_pids = set()
        self.safe_pids = set()
    
    def find_test_processes(self) -> List[Dict]:
        """查找可能的测试进程"""
        processes = []
        current_pid = os.getpid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status']):
            try:
                info = proc.info
                if info['pid'] == current_pid:
                    continue
                
                # 检查命令行
                cmdline = ' '.join(info['cmdline']) if info['cmdline'] else ''
                
                # 检查是否是测试相关进程
                is_test_process = False
                for keyword in self.test_keywords:
                    if keyword.lower() in cmdline.lower():
                        is_test_process = True
                        break
                
                if is_test_process:
                    # 获取更多信息
                    try:
                        proc_obj = psutil.Process(info['pid'])
                        cpu_percent = proc_obj.cpu_percent()
                        memory_mb = proc_obj.memory_info().rss / 1024 / 1024
                        
                        processes.append({
                            'pid': info['pid'],
                            'name': info['name'],
                            'cmdline': cmdline,
                            'status': info['status'],
                            'create_time': info['create_time'],
                            'cpu_percent': cpu_percent,
                            'memory_mb': memory_mb,
                            'age_seconds': time.time() - info['create_time']
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def classify_processes(self, processes: List[Dict]) -> None:
        """分类进程（危险/安全）"""
        self.dangerous_pids.clear()
        self.safe_pids.clear()
        
        for proc in processes:
            # 判断是否是僵死进程的标准
            is_dangerous = False
            
            # 1. 运行时间过长（超过30分钟）
            if proc['age_seconds'] > 1800:  # 30分钟
                is_dangerous = True
            
            # 2. 状态异常
            if proc['status'] in ['zombie', 'stopped']:
                is_dangerous = True
            
            # 3. CPU使用率长期为0（可能僵死）
            if proc['cpu_percent'] == 0 and proc['age_seconds'] > 300:  # 5分钟
                is_dangerous = True
            
            # 4. 内存使用异常高
            if proc['memory_mb'] > 1000:  # 1GB
                is_dangerous = True
            
            if is_dangerous:
                self.dangerous_pids.add(proc['pid'])
            else:
                self.safe_pids.add(proc['pid'])
    
    def display_processes(self, processes: List[Dict]) -> None:
        """显示进程列表"""
        if not processes:
            print("✅ 未发现测试相关进程")
            return
        
        print(f"🔍 发现 {len(processes)} 个测试相关进程:")
        print()
        print(f"{'PID':<8} {'状态':<10} {'CPU%':<6} {'内存(MB)':<10} {'运行时长':<12} {'命令':<50}")
        print("-" * 90)
        
        for proc in processes:
            age_str = f"{proc['age_seconds']:.0f}s"
            if proc['age_seconds'] > 3600:
                age_str = f"{proc['age_seconds']/3600:.1f}h"
            elif proc['age_seconds'] > 60:
                age_str = f"{proc['age_seconds']/60:.1f}m"
            
            is_dangerous = proc['pid'] in self.dangerous_pids
            marker = "⚠️ " if is_dangerous else "✅ "
            
            print(f"{marker}{proc['pid']:<6} {proc['status']:<10} {proc['cpu_percent']:<6.1f} "
                  f"{proc['memory_mb']:<10.1f} {age_str:<12} {proc['cmdline'][:50]}")
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """终止进程"""
        try:
            proc = psutil.Process(pid)
            
            if not force:
                # 先尝试温和终止
                print(f"💬 发送 SIGTERM 到进程 {pid}")
                proc.terminate()
                
                # 等待5秒
                try:
                    proc.wait(timeout=5)
                    print(f"✅ 进程 {pid} 已正常终止")
                    return True
                except psutil.TimeoutExpired:
                    print(f"⏰ 进程 {pid} 未响应 SIGTERM")
            
            # 强制终止
            print(f"💀 发送 SIGKILL 到进程 {pid}")
            proc.kill()
            proc.wait(timeout=3)
            print(f"✅ 进程 {pid} 已强制终止")
            return True
            
        except psutil.NoSuchProcess:
            print(f"ℹ️  进程 {pid} 已不存在")
            return True
        except psutil.AccessDenied:
            print(f"❌ 无权限终止进程 {pid}")
            return False
        except Exception as e:
            print(f"❌ 终止进程 {pid} 时出错: {e}")
            return False
    
    def interactive_cleanup(self, processes: List[Dict]) -> None:
        """交互式清理"""
        if not processes:
            return
        
        self.classify_processes(processes)
        
        # 处理危险进程
        if self.dangerous_pids:
            print(f"\n⚠️  发现 {len(self.dangerous_pids)} 个可能僵死的进程")
            response = input("是否清理这些进程？(y/N): ").strip().lower()
            
            if response in ['y', 'yes']:
                for pid in self.dangerous_pids:
                    self.kill_process(pid)
        
        # 处理安全进程
        if self.safe_pids:
            print(f"\nℹ️  发现 {len(self.safe_pids)} 个正常的测试进程")
            response = input("是否也清理这些进程？(y/N): ").strip().lower()
            
            if response in ['y', 'yes']:
                for pid in self.safe_pids:
                    self.kill_process(pid)
    
    def force_cleanup(self, processes: List[Dict]) -> None:
        """强制清理所有进程"""
        if not processes:
            return
        
        print(f"💀 强制清理 {len(processes)} 个进程")
        
        for proc in processes:
            self.kill_process(proc['pid'], force=True)


def main():
    parser = argparse.ArgumentParser(
        description="测试进程清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/cleanup_test_processes.py              # 交互式清理
  python scripts/cleanup_test_processes.py --force      # 强制清理
  python scripts/cleanup_test_processes.py --check      # 仅检查
        """
    )
    
    parser.add_argument("--force", action="store_true", help="强制清理所有相关进程")
    parser.add_argument("--check", action="store_true", help="仅检查，不清理")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    cleaner = TestProcessCleaner()
    
    print("🔍 搜索测试相关进程...")
    processes = cleaner.find_test_processes()
    
    cleaner.classify_processes(processes)
    cleaner.display_processes(processes)
    
    if args.check:
        print("\nℹ️  仅检查模式，不进行清理")
        if cleaner.dangerous_pids:
            print(f"⚠️  发现 {len(cleaner.dangerous_pids)} 个可能的僵死进程")
            return 1
        return 0
    
    if args.force:
        cleaner.force_cleanup(processes)
    else:
        cleaner.interactive_cleanup(processes)
    
    print("\n✅ 清理完成")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)