"""
Linux平台的文本注入器实现。

使用xdotool工具将文本输入到当前活动窗口。
"""

import logging
import shutil
import subprocess
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
        # 检查并设置xdotool路径
        self._xdotool_path = shutil.which("xdotool")
        self._xdotool_available = self._xdotool_path is not None
        
        if not self._xdotool_available:
            logger.error("xdotool工具不可用，文本注入功能将不可用")
            logger.error("请通过包管理器安装xdotool，例如: sudo apt install xdotool")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: xdotool工具不可用，文本注入功能将不可用\033[0m")
            print("\033[31m请安装xdotool: sudo apt install xdotool\033[0m")
        else:
            logger.info(f"xdotool工具已可用，路径: {self._xdotool_path}")
            # 检查xdotool版本
            try:
                version_info = subprocess.run(
                    [self._xdotool_path, "--version"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info(f"xdotool版本: {version_info.stdout.strip()}")
            except Exception as e:
                logger.warning(f"无法获取xdotool版本信息: {e}")
    
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
            return False
        
        try:
            logger.info(f"正在使用xdotool注入文本，长度: {len(text)}")
            
            # 直接执行xdotool type命令
            command = [self._xdotool_path, "type", text]
            logger.debug(f"执行命令: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=5  # 合理的超时时间
            )
            
            if result.returncode == 0:
                logger.info("文本注入成功")
                return True
            else:
                logger.error(f"文本注入失败: 命令返回非零状态: {result.returncode}")
                if result.stderr:
                    logger.error(f"错误输出: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("文本注入超时")
            return False
        except Exception as e:
            logger.error(f"文本注入过程中发生错误: {e}")
            return False 