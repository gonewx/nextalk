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
        self._xdotool_available = self._check_xdotool()
        if not self._xdotool_available:
            logger.error("xdotool工具不可用，文本注入功能将不可用")
            logger.info("请通过包管理器安装xdotool，例如: sudo apt install xdotool")
    
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
            return False
        
        try:
            # 使用subprocess.run执行xdotool命令
            # --clearmodifiers: 清除所有修饰键状态（如Shift, Control等）
            # --delay: 按键间延迟（毫秒）
            result = subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", "10", text],
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"xdotool执行成功，文本已注入: {text[:30]}...")
            return True
        
        except subprocess.CalledProcessError as e:
            logger.error(f"xdotool执行失败: {e}")
            logger.error(f"错误输出: {e.stderr}")
            return False
        
        except Exception as e:
            logger.error(f"文本注入过程中发生未知错误: {e}")
            return False 