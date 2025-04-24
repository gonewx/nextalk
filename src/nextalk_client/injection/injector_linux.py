"""
Linux平台的文本注入器实现。

使用xdotool工具将文本输入到当前活动窗口。
"""

import logging
import shutil
import subprocess
import os
from .injector_base import BaseInjector

# 设置日志记录器
logger = logging.getLogger(__name__)


class LinuxInjector(BaseInjector):
    """
    Linux平台的文本注入器实现。
    
    使用xdotool命令行工具将文本输入到当前活动窗口。
    要求系统安装了xdotool工具。
    """
    
    def __init__(self):
        """
        初始化Linux文本注入器。
        
        检查xdotool是否可用。
        """
        self._xdotool_available = self._check_xdotool()
        if not self._xdotool_available:
            logger.error("xdotool工具不可用，文本注入功能将不可用")
            logger.error("请通过包管理器安装xdotool，例如: sudo apt install xdotool")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: xdotool工具不可用，文本注入功能将不可用\033[0m")
            print("\033[31m请安装xdotool: sudo apt install xdotool\033[0m")
        else:
            logger.info("xdotool工具已可用，文本注入功能已启用")
            # 检查xdotool版本
            try:
                version_info = subprocess.run(
                    ["xdotool", "--version"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"xdotool版本: {version_info.stdout.strip()}")
            except Exception as e:
                logger.warning(f"无法获取xdotool版本信息: {e}")
    
    def _check_xdotool(self) -> bool:
        """
        检查xdotool工具是否可用。
        
        Returns:
            bool: 如果xdotool可用，返回True，否则返回False
        """
        return shutil.which("xdotool") is not None
    
    def inject_text(self, text: str) -> bool:
        """
        使用xdotool将文本注入到当前活动窗口。
        
        Args:
            text: 要注入的文本
            
        Returns:
            bool: 注入是否成功
        """
        if not text:
            logger.warning("尝试注入空文本，忽略")
            return True
        
        if not self._xdotool_available:
            logger.error("无法注入文本: xdotool工具不可用")
            logger.error("请安装xdotool: sudo apt install xdotool")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: 无法注入文本，xdotool工具不可用\033[0m")
            print("\033[31m请安装xdotool: sudo apt install xdotool\033[0m")
            return False
        
        try:
            # 设置环境变量以启用xdotool的调试输出（若需要）
            env = os.environ.copy()
            if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
                env['XDOTOOL_DEBUG'] = '1'
            
            logger.debug(f"准备使用xdotool注入文本，长度: {len(text)}")
            logger.debug(f"注入文本内容: {text}")
            
            # 获取当前活动窗口信息，用于调试
            try:
                window_info = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
                window_id = subprocess.run(
                    ["xdotool", "getactivewindow"],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
                logger.info(f"当前活动窗口ID: {window_id.stdout.strip()}, 名称: {window_info.stdout.strip()}")
                # 输出到标准输出，确保用户可以看到窗口信息
                print(f"当前活动窗口: {window_info.stdout.strip()}")
            except Exception as e:
                logger.warning(f"获取窗口信息失败: {e}")
                print(f"警告: 获取窗口信息失败: {e}")
            
            # 使用subprocess.run执行xdotool命令
            # --clearmodifiers: 清除所有修饰键状态（如Shift, Control等）
            # --delay: 按键间延迟（毫秒）
            command = ["xdotool", "type", "--clearmodifiers", "--delay", "10", text]
            logger.debug(f"执行命令: {' '.join(command)}")
            # 在标准输出显示命令
            print(f"执行xdotool命令: type --clearmodifiers --delay 10 [文本内容]")
            
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            logger.debug(f"xdotool返回码: {result.returncode}")
            logger.debug(f"xdotool标准输出: {result.stdout}")
            logger.info(f"xdotool执行成功，文本已注入: {text[:30]}...")
            print(f"\033[32mxdotool执行成功，文本已注入\033[0m")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"xdotool执行失败，返回码: {e.returncode}")
            logger.error(f"错误输出: {e.stderr}")
            logger.error(f"标准输出: {e.stdout}")
            # 输出到标准输出，确保用户可以看到错误消息
            print(f"\033[31m错误: xdotool执行失败，返回码: {e.returncode}\033[0m")
            print(f"\033[31m错误输出: {e.stderr}\033[0m")
            return False
        
        except Exception as e:
            logger.error(f"文本注入过程中发生未知错误: {e}")
            logger.error(f"异常详情:", exc_info=True)
            # 输出到标准输出，确保用户可以看到错误消息
            print(f"\033[31m错误: 文本注入过程中发生未知错误: {e}\033[0m")
            return False 