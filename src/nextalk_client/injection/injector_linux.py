"""
Linux平台的文本注入器实现。

使用 pyautogui 和 pyclip 库模拟键盘输入或剪贴板粘贴。
"""

import logging
import threading
import subprocess
import shutil
import time
from typing import Optional
from .injector_base import BaseInjector

# 新增依赖导入
import pyautogui
import pyclip
import platform

# 设置日志记录器
logger = logging.getLogger(__name__)

# 配置类，控制注入行为
class Config:
    paste = True  # 使用粘贴模式而不是直接模拟键盘输入
    restore_clip = True  # 是否在粘贴后恢复剪贴板内容
    paste_delay = 0.1  # 粘贴操作延迟时间(秒)

class LinuxInjector(BaseInjector):
    """
    Linux平台的文本注入器实现。
    
    使用 pyautogui 和 pyclip 库实现文本注入。
    """
    
    def __init__(self):
        """
        初始化Linux文本注入器。
        
        检查必要依赖是否可用。
        """
        # 检查依赖
        self._dependencies_available = True
        try:
            import pyautogui
            import pyclip
        except ImportError as e:
            self._dependencies_available = False
            logger.error(f"无法导入必要的依赖库: {e}")
            logger.error("请安装依赖: pip install pyautogui pyclip")
            # 尝试输出到标准输出，确保用户可以看到错误消息
            print("\033[31m错误: 无法导入必要的依赖库\033[0m")
            print("\033[31m请安装依赖: pip install pyautogui pyclip\033[0m")
        else:
            logger.debug("pyautogui 和 pyclip 库已找到，文本注入已准备就绪")
        
        # 初始化注入状态标志和锁
        self._is_injecting = False
        self._injecting_lock = threading.Lock()
    
    def _type_text(self, text):
        """
        使用 pyautogui 和 pyclip 库模拟文本输入。
        
        Args:
            text: 要注入的文本
        """
        # 模拟粘贴
        if Config.paste:
            # 保存剪切板
            try:
                temp = pyclip.paste().decode('utf-8')
            except Exception as e:
                logger.warning(f"保存剪贴板内容失败: {e}")
                temp = ''

            # 复制结果
            pyclip.copy(text)
            
            # 短暂延迟确保复制完成
            time.sleep(0.05)

            # 粘贴结果
            if platform.system() == 'Darwin':
                pyautogui.hotkey('command', 'v')
            else:
                pyautogui.hotkey('ctrl', 'v')

            # 还原剪贴板
            if Config.restore_clip:
                time.sleep(Config.paste_delay)
                pyclip.copy(temp)
        # 模拟打印
        else:
            pyautogui.write(text)
    
    def inject_text(self, text: str) -> bool:
        """
        使用 pyautogui 和 pyclip 库将文本输入到当前活动窗口。
        
        Args:
            text: 要注入的文本
            
        Returns:
            bool: 注入是否成功
        """
        if not text:
            logger.warning("尝试注入空文本，忽略")
            return True
        
        if not self._dependencies_available:
            logger.error("无法注入文本: 必要的依赖库不可用")
            return False
        
        # 获取锁并设置注入标志
        with self._injecting_lock:
            try:
                # 设置注入标志为True
                self._is_injecting = True
                logger.debug(f"正在使用 pyautogui/pyclip 注入文本，长度: {len(text)}")
                
                # 执行文本注入
                self._type_text(text)
                
                logger.debug("文本注入成功")
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