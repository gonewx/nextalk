"""
Linux平台的文本注入器实现。

使用pynput.keyboard.Controller将文本输入到当前活动窗口。
"""

import logging
import threading
from typing import Optional
from pynput.keyboard import Controller
from .injector_base import BaseInjector

# 设置日志记录器
logger = logging.getLogger(__name__)

class LinuxInjector(BaseInjector):
    """
    Linux平台的文本注入器实现。
    
    使用pynput.keyboard.Controller将文本输入到当前活动窗口。
    """
    
    def __init__(self):
        """
        初始化Linux文本注入器。
        
        创建pynput键盘控制器实例。
        """
        # 创建键盘控制器实例
        try:
            self._keyboard_controller: Optional[Controller] = Controller()
            self._controller_available = True
            logger.info("pynput.keyboard.Controller 实例已创建，文本注入已准备就绪")
        except Exception as e:
            self._keyboard_controller = None
            self._controller_available = False
            logger.error(f"无法创建 pynput.keyboard.Controller 实例: {e}")
            logger.error("文本注入功能将不可用")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: 无法初始化pynput键盘控制器，文本注入功能将不可用\033[0m")
            print("\033[31m请确认已安装pynput库: pip install pynput\033[0m")
        
        # 初始化注入状态标志和锁
        self._is_injecting = False
        self._injecting_lock = threading.Lock()
    
    def inject_text(self, text: str) -> bool:
        """
        使用pynput.keyboard.Controller将文本注入到当前活动窗口。
        
        Args:
            text: 要注入的文本
            
        Returns:
            bool: 注入是否成功
        """
        if not text:
            logger.warning("尝试注入空文本，忽略")
            return True
        
        if not self._controller_available or not self._keyboard_controller:
            logger.error("无法注入文本: pynput键盘控制器不可用")
            return False
        
        # 获取锁并设置注入标志
        with self._injecting_lock:
            try:
                # 设置注入标志为True
                self._is_injecting = True
                logger.info(f"正在使用pynput.keyboard.Controller注入文本，长度: {len(text)}")
                
                # 使用pynput控制器执行文本输入
                self._keyboard_controller.type(text)
                
                logger.info("文本注入成功")
                return True
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