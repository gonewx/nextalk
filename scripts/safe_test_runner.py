#!/usr/bin/env python3
"""
安全测试运行器 - 防止测试僵死的增强版测试运行器

用法:
python scripts/safe_test_runner.py                    # 运行所有测试
python scripts/safe_test_runner.py --quick            # 运行快速测试
python scripts/safe_test_runner.py --integration      # 运行集成测试
python scripts/safe_test_runner.py --timeout 60       # 自定义超时
python scripts/safe_test_runner.py tests/core/        # 运行特定目录
"""

import sys
import os
import subprocess
import argparse
import signal
import threading
import time
from pathlib import Path


def setup_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ['PYTHONPATH'] = str(Path(__file__).parent.parent)
    os.environ['PYTEST_CURRENT_TEST'] = '1'
    
    # 设置更严格的资源限制（如果可用）
    try:
        import resource
        # 获取当前限制
        current_mem = resource.getrlimit(resource.RLIMIT_AS)
        current_proc = resource.getrlimit(resource.RLIMIT_NPROC)
        
        # 限制内存使用（只降低，不提高）
        new_mem_limit = min(current_mem[1], 2 * 1024 * 1024 * 1024) if current_mem[1] > 0 else 2 * 1024 * 1024 * 1024
        if new_mem_limit < current_mem[0] or current_mem[1] == -1:
            resource.setrlimit(resource.RLIMIT_AS, (new_mem_limit, current_mem[1]))
        
        # 限制进程数（只降低，不提高）
        new_proc_limit = min(current_proc[1], 100) if current_proc[1] > 0 else 100
        if new_proc_limit < current_proc[0] or current_proc[1] == -1:
            resource.setrlimit(resource.RLIMIT_NPROC, (new_proc_limit, current_proc[1]))
    except (ImportError, OSError, ValueError):
        # 忽略资源限制设置失败
        pass


def run_with_guardian(test_command, timeout=600):
    """使用进程守护器运行测试"""
    guardian_script = Path(__file__).parent / "test_guardian.py"
    
    if not guardian_script.exists():
        print("⚠️  测试守护器不存在，直接运行测试（有风险）", file=sys.stderr)
        return subprocess.run(test_command)
    
    # 构建守护器命令
    guardian_cmd = [
        sys.executable,
        str(guardian_script),
        "--timeout", str(timeout),
        "--"
    ] + test_command
    
    print(f"🛡️  使用进程守护器运行测试 (超时: {timeout}秒)")
    return subprocess.run(guardian_cmd)


def build_pytest_command(args):
    """构建pytest命令"""
    cmd = [sys.executable, "-m", "pytest"]
    
    # 基本选项
    cmd.extend(["-v", "--tb=short", "--no-header"])
    
    # 超时设置
    if args.timeout:
        cmd.extend(["--timeout", str(args.timeout)])
    
    # 测试类型选择
    if args.quick:
        cmd.extend(["-m", "not integration and not slow and not hardware"])
        cmd.extend(["--timeout", "10"])  # 快速测试更短超时
    elif args.integration:
        cmd.extend(["-m", "integration"])
        cmd.extend(["--timeout", "60"])  # 集成测试更长超时
    elif args.slow:
        cmd.extend(["-m", "slow"])
        cmd.extend(["--timeout", "120"])
    elif args.hardware:
        cmd.extend(["-m", "hardware"])
        cmd.extend(["--timeout", "30"])
    
    # 并发控制
    if args.serial or args.integration:
        # 串行执行
        pass
    else:
        # 可以添加并发执行（如果需要）
        pass
    
    # 输出选项
    if args.verbose:
        cmd.append("-s")
    
    if args.coverage:
        cmd.extend(["--cov=nextalk", "--cov-report=html"])
    
    # 失败处理
    if args.fail_fast:
        cmd.extend(["--maxfail=1"])
    else:
        cmd.extend(["--maxfail=5"])
    
    # 添加测试路径和额外参数
    if args.paths:
        cmd.extend(args.paths)
    else:
        cmd.append("tests/")
    
    # 添加额外的pytest参数
    if hasattr(args, 'extra_args') and args.extra_args:
        cmd.extend(args.extra_args)
    
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="安全测试运行器 - 防止测试僵死",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/safe_test_runner.py                    # 所有测试
  python scripts/safe_test_runner.py --quick            # 快速测试
  python scripts/safe_test_runner.py --integration      # 集成测试
  python scripts/safe_test_runner.py --timeout 120      # 自定义超时
  python scripts/safe_test_runner.py tests/core/        # 特定目录
  python scripts/safe_test_runner.py --coverage         # 带覆盖率
        """
    )
    
    # 测试类型
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--quick", action="store_true", help="运行快速测试（排除集成测试）")
    test_group.add_argument("--integration", action="store_true", help="仅运行集成测试")
    test_group.add_argument("--slow", action="store_true", help="仅运行慢测试")
    test_group.add_argument("--hardware", action="store_true", help="仅运行硬件测试")
    
    # 超时设置
    parser.add_argument("--timeout", type=int, help="单个测试超时时间（秒）")
    parser.add_argument("--global-timeout", type=int, default=600, help="总体测试超时时间（秒）")
    
    # 执行选项
    parser.add_argument("--serial", action="store_true", help="串行执行所有测试")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--fail-fast", action="store_true", help="第一个失败后停止")
    
    # 安全选项
    parser.add_argument("--no-guardian", action="store_true", help="不使用进程守护器（不推荐）")
    parser.add_argument("--force", action="store_true", help="强制运行（忽略警告）")
    
    # 测试路径
    parser.add_argument("paths", nargs="*", help="要测试的路径或文件")
    
    # 支持额外的pytest参数
    parser.add_argument("--", dest="extra_args", nargs="*", help="额外的pytest参数")
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    
    # 构建pytest命令
    pytest_cmd = build_pytest_command(args)
    
    print(f"🚀 准备运行测试: {' '.join(pytest_cmd)}")
    
    # 运行测试
    if args.no_guardian:
        if not args.force:
            print("⚠️  警告：不使用进程守护器可能导致测试僵死！")
            print("    如果确定要继续，请添加 --force 参数")
            return 1
        
        print("⚠️  直接运行测试（无守护器保护）")
        result = subprocess.run(pytest_cmd)
    else:
        result = run_with_guardian(pytest_cmd, args.global_timeout)
    
    # 处理结果
    exit_code = result.returncode
    
    if exit_code == 0:
        print("✅ 所有测试通过！")
    elif exit_code == 124:
        print("💀 测试超时被强制终止")
    elif exit_code == 125:
        print("💀 测试被守护器强制终止")
    else:
        print(f"❌ 测试失败，退出码: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)