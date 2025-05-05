"""
简单窗口模块。

提供一个不依赖 Tkinter 的简单窗口，作为焦点窗口的备用方案。
使用命令行输出作为临时解决方案。
"""

import logging
import threading
import time
from typing import Optional

# 设置日志记录器
logger = logging.getLogger(__name__)

class SimpleWindow:
    """
    简单窗口类。
    
    提供一个基于命令行的文本显示功能，作为焦点窗口的备用方案。
    """
    
    def __init__(self, title="NexTalk转录"):
        """
        初始化简单窗口。
        
        Args:
            title: 窗口标题
        """
        self._title = title
        self._lock = threading.Lock()
        self._is_active = False
        self._last_text = ""
        self._last_display_time = 0
        
    def start(self):
        """
        启动简单窗口。
        
        Returns:
            bool: 启动是否成功
        """
        with self._lock:
            self._is_active = True
            logger.info("简单窗口已启动")
            print("\n" + "=" * 50)
            print(f"  {self._title}  ")
            print("=" * 50)
            return True
    
    def stop(self):
        """
        停止简单窗口。
        """
        with self._lock:
            if not self._is_active:
                logger.warning("简单窗口未运行")
                return
            
            self._is_active = False
            print("\n" + "=" * 50)
            print("  窗口已关闭  ")
            print("=" * 50 + "\n")
            logger.info("简单窗口已关闭")
    
    def display_text(self, text, duration_seconds=5, is_temporary=False):
        """
        在简单窗口中显示文本。
        
        Args:
            text: 要显示的文本
            duration_seconds: 显示持续时间（秒），在简单窗口中无效
            is_temporary: 是否是临时文本（如中间结果）
        
        Returns:
            bool: 显示是否成功
        """
        with self._lock:
            if not self._is_active:
                logger.warning("简单窗口未运行，无法显示文本")
                return False
            
            try:
                current_time = time.time()
                
                # 如果是临时文本且与上次相同，不重复显示
                if is_temporary and text == self._last_text and current_time - self._last_display_time < 1.0:
                    return True
                
                # 更新最后显示的文本和时间
                self._last_text = text
                self._last_display_time = current_time
                
                # 清除当前行并显示文本
                print("\r" + " " * 80, end="")  # 清除当前行
                print(f"\r[{'临时' if is_temporary else '最终'}] {text}", end="")
                if not is_temporary:
                    print()  # 最终结果后换行
                
                return True
                
            except Exception as e:
                logger.error(f"在简单窗口显示文本时发生错误: {e}")
                return False

# 单例模式实现
_simple_window_instance = None

def get_simple_window():
    """
    获取简单窗口单例。
    
    Returns:
        SimpleWindow: 简单窗口实例
    """
    global _simple_window_instance
    if _simple_window_instance is None:
        _simple_window_instance = SimpleWindow()
    return _simple_window_instance

def show_text(text, duration_seconds=5, is_temporary=False):
    """
    在简单窗口中显示文本的便捷函数。
    
    Args:
        text: 要显示的文本
        duration_seconds: 显示持续时间（秒）
        is_temporary: 是否是临时文本（如中间结果）
    
    Returns:
        bool: 显示是否成功
    """
    window = get_simple_window()
    
    # 如果窗口未启动，先启动窗口
    if not window._is_active:
        window.start()
        
    return window.display_text(text, duration_seconds, is_temporary) 