#!/usr/bin/env python3
"""
NexTalk 统一启动脚本

这个脚本是NexTalk的主要入口点，可以用于启动服务器、客户端或完整的工作流。
提供命令行参数，支持标准模式和调试模式。

使用方法:
  - 启动服务器: python nextalk.py server [--log-level LEVEL] [--log-file FILE]
  - 启动客户端: python nextalk.py client [--debug] [--log-file FILE]
  - 启动完整工作流: python nextalk.py start [--log-level LEVEL] [--log-file-server FILE] [--log-file-client FILE]
"""

import argparse
import os
import sys
import time
import subprocess
import importlib.util
import logging
import shutil
from pathlib import Path


# 设置基本日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nextalk")


def find_project_root():
    """
    查找项目根目录
    
    从当前目录开始向上查找，直到找到包含src/nextalk_server的目录
    """
    current_dir = Path.cwd()
    
    # 向上最多查找5层目录
    for _ in range(5):
        if (current_dir / "nextalk" / "src" / "nextalk_server").exists() or (current_dir / "nextalk" / "src" / "nextalk_client").exists():
            return current_dir
        
        # 向上移动一级
        parent_dir = current_dir.parent
        if parent_dir == current_dir:  # 已到根目录
            break
        current_dir = parent_dir
    
    # 如果找不到，返回当前目录
    return Path.cwd()


def add_src_to_path():
    """将项目的src目录添加到Python路径"""
    project_root = find_project_root()
    src_path = project_root / "nextalk" / "src"
       
    if src_path.exists():
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
            os.environ["PYTHONPATH"] = f"{str(src_path)}:{os.environ.get('PYTHONPATH', '')}"
        
        return True
    else:
        return False


def check_dependencies():
    """检查基本依赖是否满足"""
    missing = []
    
    # 检查xdotool（客户端需要）
    if not shutil.which("xdotool"):
        missing.append("xdotool (sudo apt install xdotool)")
    
    return missing


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="NexTalk语音识别系统统一启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  启动服务器:
    python nextalk.py server --log-level debug
  
  启动客户端:
    python nextalk.py client
  
  启动完整工作流:
    python nextalk.py start --log-level debug
        """
    )
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest="command", help="要执行的命令")
    
    # 服务器命令
    server_parser = subparsers.add_parser("server", help="启动NexTalk服务器")
    server_parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"], help="设置日志级别，默认为info")
    server_parser.add_argument("--log-file", type=str, help="指定日志文件路径")
    server_parser.add_argument("--host", type=str, help="指定服务器监听地址")
    server_parser.add_argument("--port", type=int, help="指定服务器监听端口")
    
    # 客户端命令
    client_parser = subparsers.add_parser("client", help="启动NexTalk客户端")
    client_parser.add_argument("--debug", action="store_true", help="启用调试模式")
    client_parser.add_argument("--log-file", type=str, help="指定日志文件路径")
    client_parser.add_argument("--server-host", type=str, help="指定服务器地址")
    client_parser.add_argument("--server-port", type=int, help="指定服务器端口")
    
    # 完整工作流命令
    workflow_parser = subparsers.add_parser("start", help="启动完整NexTalk工作流（服务器+客户端）")
    workflow_parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"], help="设置服务器日志级别，默认为info")
    workflow_parser.add_argument("--log-file-server", type=str, default="server_debug.log", help="指定服务器日志文件路径")
    workflow_parser.add_argument("--log-file-client", type=str, default="client_debug.log", help="指定客户端日志文件路径")
    workflow_parser.add_argument("--host", type=str, help="指定服务器监听地址")
    workflow_parser.add_argument("--port", type=int, help="指定服务器监听端口")
    
    # 版本信息
    parser.add_argument('--version', action='version', version='NexTalk v0.1.0')
    
    args = parser.parse_args()
    
    # 如果没有指定命令，显示帮助
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    return args


def start_server(args):
    """启动NexTalk服务器"""
    print("\033[1;36m=== 启动NexTalk服务器 ===\033[0m")
    
    # 设置环境变量
    log_level = args.log_level.lower()
    if log_level == "debug":
        os.environ["NEXTALK_DEBUG"] = "1"
        print("\033[1;33m调试模式已启用\033[0m")
    
    try:
        # 尝试导入服务器模块
        spec = importlib.util.find_spec("nextalk_server.main")
        if spec is None:
            logger.error("无法导入nextalk_server模块，请确保已安装或PYTHONPATH设置正确")
            print("\033[1;31m错误: 无法找到nextalk_server模块\033[0m")
            return 1
        
        # 构建启动命令
        cmd = [sys.executable, "-m", "nextalk_server.main"]
        
        cmd.extend(["--log-level", log_level])
        
        if args.log_file:
            cmd.extend(["--log-file", args.log_file])
            
        if args.host:
            cmd.extend(["--host", args.host])
            
        if args.port:
            cmd.extend(["--port", str(args.port)])
        
        # 执行服务器命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        return subprocess.call(cmd)
        
    except Exception as e:
        logger.exception(f"启动服务器时发生错误: {e}")
        print(f"\033[1;31m错误: 启动服务器失败: {e}\033[0m")
        return 1


def start_client(args):
    """启动NexTalk客户端"""
    print("\033[1;36m=== 启动NexTalk客户端 ===\033[0m")
    
    # 设置环境变量
    if args.debug:
        os.environ["NEXTALK_DEBUG"] = "1"
        print("\033[1;33m调试模式已启用\033[0m")
    
    # 设置服务器连接信息（如果提供）
    if args.server_host:
        os.environ["NEXTALK_SERVER_HOST"] = args.server_host
    if args.server_port:
        os.environ["NEXTALK_SERVER_PORT"] = str(args.server_port)
    
    try:
        # 检查xdotool是否已安装
        if not shutil.which("xdotool"):
            print("\033[1;31m警告: xdotool未安装，文本注入功能将不可用\033[0m")
            print("\033[1;31m请安装: sudo apt install xdotool\033[0m")
            choice = input("是否继续? (y/n): ")
            if choice.lower() != 'y':
                print("已取消启动")
                return 1
        
        # 尝试导入客户端模块
        spec = importlib.util.find_spec("nextalk_client.main")
        if spec is None:
            logger.error("无法导入nextalk_client模块，请确保已安装或PYTHONPATH设置正确")
            print("\033[1;31m错误: 无法找到nextalk_client模块\033[0m")
            return 1
        
        # 构建启动命令
        cmd = [sys.executable, "-m", "nextalk_client.main"]
        
        if args.debug:
            cmd.append("--debug")
        
        if args.log_file:
            cmd.extend(["--log-file", args.log_file])
        
        # 执行客户端命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        return subprocess.call(cmd)
        
    except Exception as e:
        logger.exception(f"启动客户端时发生错误: {e}")
        print(f"\033[1;31m错误: 启动客户端失败: {e}\033[0m")
        return 1


def start_workflow(args):
    """启动完整NexTalk工作流（服务器+客户端）"""
    print("\033[1;36m===== 启动NexTalk完整工作流 =====\033[0m")
    print("1. 启动服务器")
    print("2. 等待服务器初始化")
    print("3. 启动客户端")
    print()
    
    # 检查依赖
    missing = check_dependencies()
    if missing:
        print("\033[1;31m警告: 以下依赖项未安装:\033[0m")
        for item in missing:
            print(f"\033[1;31m  - {item}\033[0m")
        choice = input("是否继续? (y/n): ")
        if choice.lower() != 'y':
            print("已取消启动")
            return 1
    
    # 设置环境变量
    log_level = args.log_level.lower()
    if log_level == "debug":
        os.environ["NEXTALK_DEBUG"] = "1"
        print("\033[1;33m调试模式已启用，将显示详细日志\033[0m")
    
    try:
        # 创建服务器进程参数
        server_cmd = [sys.executable, os.path.abspath(__file__), "server"]
        server_cmd.extend(["--log-level", log_level])
        if args.log_file_server:
            server_cmd.extend(["--log-file", args.log_file_server])
        if args.host:
            server_cmd.extend(["--host", args.host])
        if args.port:
            server_cmd.extend(["--port", str(args.port)])
        
        # 在新终端中启动服务器
        if sys.platform == "linux":
            # 检查可用的终端模拟器
            terminal = None
            for term in ["gnome-terminal", "konsole", "xterm"]:
                if shutil.which(term):
                    terminal = term
                    break
            
            if terminal:
                if terminal == "gnome-terminal":
                    server_process = subprocess.Popen([
                        terminal, "--", "bash", "-c", f"{' '.join(server_cmd)}; echo '按Enter键关闭此窗口...'; read"
                    ])
                else:
                    server_process = subprocess.Popen([
                        terminal, "-e", f"bash -c \"{' '.join(server_cmd)}; echo '按Enter键关闭此窗口...'; read\""
                    ])
            else:
                # 如果没有可用的终端模拟器，直接在后台启动
                print("\033[1;33m警告: 未找到可用的终端模拟器，将在后台启动服务器\033[0m")
                server_process = subprocess.Popen(
                    server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
        else:
            # 其他平台直接在后台启动
            server_process = subprocess.Popen(
                server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        
        print("\033[1;32m服务器启动中...\033[0m")
        
        # 等待服务器启动
        print("等待服务器初始化 (3秒)...")
        time.sleep(3)
        
        # 创建客户端进程参数
        client_cmd = [sys.executable, os.path.abspath(__file__), "client"]
        if args.debug:
            client_cmd.append("--debug")
        if args.log_file_client:
            client_cmd.extend(["--log-file", args.log_file_client])
        if args.host:
            client_cmd.extend(["--server-host", args.host])
        if args.port:
            client_cmd.extend(["--server-port", str(args.port)])
        
        # 启动客户端（在当前终端）
        print("\033[1;36m正在启动客户端...\033[0m")
        client_exit_code = subprocess.call(client_cmd)
        
        # 如果客户端已退出，发送信号终止服务器
        if sys.platform == "linux" and isinstance(server_process.pid, int):
            try:
                os.kill(server_process.pid, 15)  # SIGTERM
                server_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                pass
        
        if client_exit_code != 0:
            print(f"\033[1;31m客户端以非零状态退出: {client_exit_code}\033[0m")
            return client_exit_code
        
        return 0
        
    except Exception as e:
        logger.exception(f"启动工作流时发生错误: {e}")
        print(f"\033[1;31m错误: 启动工作流失败: {e}\033[0m")
        return 1


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 将src目录添加到Python路径
    if not add_src_to_path():
        print("\033[1;31m警告: 无法找到项目src目录，模块导入可能失败\033[0m")
    
    # 根据命令执行相应操作
    if args.command == "server":
        return start_server(args)
    elif args.command == "client":
        return start_client(args)
    elif args.command == "start":
        return start_workflow(args)
    else:
        print(f"\033[1;31m错误: 未知命令 '{args.command}'\033[0m")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\033[1;33m操作已取消\033[0m")
        sys.exit(130)  # 130是UNIX中表示被SIGINT中断的标准退出码
    except Exception as e:
        print(f"\033[1;31m发生未捕获的错误: {e}\033[0m")
        logger.exception("未捕获的错误")
        sys.exit(1) 