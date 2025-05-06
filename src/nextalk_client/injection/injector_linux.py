"""
Linux平台的文本注入器实现。

使用xdotool将文本输入到当前活动窗口。
"""

import logging
import threading
import subprocess
import shutil
from typing import Optional
from .injector_base import BaseInjector

# 设置日志记录器
logger = logging.getLogger(__name__)

class LinuxInjector(BaseInjector):
    """
    Linux平台的文本注入器实现。
    
    使用xdotool将文本输入到当前活动窗口。
    """
    
    def __init__(self):
        """
        初始化Linux文本注入器。
        
        检查xdotool是否可用。
        """
        # 检查xdotool是否可用
        self._xdotool_available = shutil.which('xdotool') is not None
        if not self._xdotool_available:
            logger.error("无法找到xdotool命令，文本注入功能将不可用")
            logger.error("请安装xdotool: sudo apt-get install xdotool")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: 无法找到xdotool命令，文本注入功能将不可用\033[0m")
            print("\033[31m请安装xdotool: sudo apt-get install xdotool\033[0m")
        else:
            logger.info("xdotool命令已找到，文本注入已准备就绪")
        
        # 初始化注入状态标志和锁
        self._is_injecting = False
        self._injecting_lock = threading.Lock()
    
    def inject_text(self, text: str) -> bool:
        """
        使用xdotool将文本输入到当前活动窗口。
        
        Args:
            text: 要注入的文本
            
        Returns:
            bool: 注入是否成功
        """
        if not text:
            logger.warning("尝试注入空文本，忽略")
            return True
        
        if not self._xdotool_available:
            logger.error("无法注入文本: xdotool不可用")
            return False
        
        # 获取锁并设置注入标志
        with self._injecting_lock:
            try:
                # 设置注入标志为True
                self._is_injecting = True
                logger.info(f"正在使用xdotool注入文本，长度: {len(text)}")
                
                # 使用xdotool --clearmodifiers确保没有修饰键被按下
                # 使用--delay 10添加微小延迟，提高稳定性
                result = subprocess.run(
                    ['xdotool', 'type', '--clearmodifiers', '--delay', '10', text], 
                    check=True, 
                    capture_output=True, 
                    text=True
                )
                
                logger.info("文本注入成功")
                logger.debug(f"xdotool输出: {result.stdout.strip() if result.stdout else '无输出'}")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"xdotool命令执行失败: {e}")
                if e.stderr:
                    logger.error(f"错误输出: {e.stderr}")
                return False
            except Exception as e:
                logger.error(f"文本注入过程中发生错误: {e}")
                return False
            finally:
                # 无论成功失败，最后都要重置注入标志
                self._is_injecting = False
                logger.debug("文本注入操作已完成")
            
    @property
    def is_injecting(self) -> bool:
        """
        返回一个标志，指示是否当前正在进行注入操作。
        
        Returns:
            bool: 如果当前正在注入文本，则返回True，否则返回False
        """
        with self._injecting_lock:
            return self._is_injecting 