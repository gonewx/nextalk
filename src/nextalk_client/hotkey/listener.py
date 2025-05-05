"""
热键监听模块。

此模块使用pynput库实现全局热键监听功能，用于激活和停用NexTalk的语音识别。
"""

import logging
import threading
import asyncio
import time
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from pynput import keyboard

# 设置日志记录器
logger = logging.getLogger(__name__)

# 定义热键组合类型
HotkeyCombination = Union[List[str], str]


class HotkeyListener:
    """
    热键监听器，用于监听全局热键并触发回调函数。
    
    支持单个或组合键作为热键，当热键被按下和释放时分别触发不同的回调函数。
    """
    
    def __init__(self):
        """初始化热键监听器。"""
        self._listener: Optional[keyboard.Listener] = None
        self._is_listening = False
        
        # 当前按下的键集合
        self._pressed_keys: Set[keyboard.Key] = set()
        
        # 热键组合配置
        self._hotkey_combo: List[keyboard.Key] = []
        
        # 回调函数
        self._on_activate: Optional[Callable] = None
        self._on_deactivate: Optional[Callable] = None
        
        # 热键当前状态
        self._is_active = False
        
        # 线程锁，用于保护状态更新
        self._lock = threading.Lock()
    
    def start(self, hotkey_combination: HotkeyCombination, 
              on_activate: Callable, on_deactivate: Callable) -> bool:
        """
        启动热键监听。
        
        Args:
            hotkey_combination: 热键组合，可以是单个键字符串或键列表，例如"ctrl+shift+space"
            on_activate: 热键被按下时触发的回调函数
            on_deactivate: 热键被释放时触发的回调函数
            
        Returns:
            bool: 是否成功启动监听
        """
        if self._is_listening:
            logger.warning("热键监听器已在运行")
            return False
        
        # 保存回调函数
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        
        # 解析热键组合
        try:
            self._hotkey_combo = self._parse_hotkey(hotkey_combination)
            logger.info(f"热键组合已配置: {hotkey_combination}")
        except Exception as e:
            logger.error(f"解析热键组合失败: {e}")
            return False
        
        # 启动键盘监听器
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._listener.start()
            self._is_listening = True
            logger.info("热键监听器已启动")
            return True
        except Exception as e:
            logger.error(f"启动热键监听器失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止热键监听。
        
        Returns:
            bool: 是否成功停止监听
        """
        if not self._is_listening or self._listener is None:
            logger.warning("热键监听器未运行")
            return False
        
        try:
            self._listener.stop()
            self._listener = None
            self._is_listening = False
            self._pressed_keys.clear()
            self._is_active = False
            logger.info("热键监听器已停止")
            return True
        except Exception as e:
            logger.error(f"停止热键监听器失败: {e}")
            return False
    
    def _parse_hotkey(self, hotkey_combination: HotkeyCombination) -> List[keyboard.Key]:
        """
        解析热键组合字符串或列表为pynput键对象列表。
        
        Args:
            hotkey_combination: 热键组合，格式如"ctrl+shift+space"或["ctrl", "shift", "space"]
            
        Returns:
            List[keyboard.Key]: 解析后的键对象列表
            
        Raises:
            ValueError: 如果热键无法被解析
        """
        # 创建键映射字典
        special_keys = {
            'alt': keyboard.Key.alt,
            'alt_l': keyboard.Key.alt_l,
            'alt_r': keyboard.Key.alt_r,
            'alt_gr': keyboard.Key.alt_gr,
            'backspace': keyboard.Key.backspace,
            'caps_lock': keyboard.Key.caps_lock,
            'cmd': keyboard.Key.cmd,
            'cmd_l': keyboard.Key.cmd_l,
            'cmd_r': keyboard.Key.cmd_r,
            'ctrl': keyboard.Key.ctrl,
            'ctrl_l': keyboard.Key.ctrl_l,
            'ctrl_r': keyboard.Key.ctrl_r,
            'delete': keyboard.Key.delete,
            'down': keyboard.Key.down,
            'end': keyboard.Key.end,
            'enter': keyboard.Key.enter,
            'esc': keyboard.Key.esc,
            'f1': keyboard.Key.f1,
            'f2': keyboard.Key.f2,
            'f3': keyboard.Key.f3,
            'f4': keyboard.Key.f4,
            'f5': keyboard.Key.f5,
            'f6': keyboard.Key.f6,
            'f7': keyboard.Key.f7,
            'f8': keyboard.Key.f8,
            'f9': keyboard.Key.f9,
            'f10': keyboard.Key.f10,
            'f11': keyboard.Key.f11,
            'f12': keyboard.Key.f12,
            'home': keyboard.Key.home,
            'insert': keyboard.Key.insert,
            'left': keyboard.Key.left,
            'menu': keyboard.Key.menu,
            'num_lock': keyboard.Key.num_lock,
            'page_down': keyboard.Key.page_down,
            'page_up': keyboard.Key.page_up,
            'pause': keyboard.Key.pause,
            'print_screen': keyboard.Key.print_screen,
            'right': keyboard.Key.right,
            'scroll_lock': keyboard.Key.scroll_lock,
            'shift': keyboard.Key.shift,
            'shift_l': keyboard.Key.shift_l,
            'shift_r': keyboard.Key.shift_r,
            'space': keyboard.Key.space,
            'tab': keyboard.Key.tab,
            'up': keyboard.Key.up,
            'super': keyboard.Key.cmd,
            'super_l': keyboard.Key.cmd_l,
            'super_r': keyboard.Key.cmd_r,
        }
        
        result = []
        
        # 如果是字符串，分割为列表
        if isinstance(hotkey_combination, str):
            key_strings = hotkey_combination.lower().split('+')
        else:
            key_strings = [k.lower() for k in hotkey_combination]
        
        logger.debug(f"解析热键组合: {hotkey_combination}, 分割后: {key_strings}")
        
        # 解析每个键
        for key_str in key_strings:
            key_str = key_str.strip()
            
            # 检查是否是特殊键
            if key_str in special_keys:
                logger.debug(f"解析特殊键: {key_str} -> {special_keys[key_str]}")
                result.append(special_keys[key_str])
            # 检查是否是单个字符键
            elif len(key_str) == 1:
                logger.debug(f"解析字符键: {key_str}")
                result.append(keyboard.KeyCode.from_char(key_str))
            else:
                logger.warning(f"无法解析键: {key_str}")
                raise ValueError(f"无法解析键: {key_str}")
        
        if not result:
            logger.warning("热键组合为空")
            raise ValueError("热键组合为空")
        
        logger.debug(f"成功解析热键组合，结果: {result}")    
        return result
    
    def _on_key_press(self, key):
        """
        按键按下事件处理函数。
        
        Args:
            key: 被按下的键
        """
        with self._lock:
            try:
                # 向按下的键集合中添加当前键
                self._pressed_keys.add(key)
                logger.debug(f"键被按下: {key}, 当前按下的键: {self._pressed_keys}")
                
                # 检查是否所有热键都被按下
                if self._is_hotkey_matched() and not self._is_active:
                    self._is_active = True
                    logger.debug("热键组合被按下，触发激活回调")
                    if self._on_activate:
                        self._on_activate()
            except Exception as e:
                logger.error(f"处理按键按下事件时出错: {e}")
    
    def _on_key_release(self, key):
        """
        按键释放事件处理函数。
        
        Args:
            key: 被释放的键
        """
        with self._lock:
            try:
                # 尝试从按下的键集合中移除当前键
                if key in self._pressed_keys:
                    self._pressed_keys.remove(key)
                    logger.debug(f"键被释放: {key}, 当前按下的键: {self._pressed_keys}")
                
                # 只有当热键处于激活状态时才处理热键释放
                # 并且确保是热键组合中的键被释放时才触发停用回调
                if self._is_active and key in self._hotkey_combo:
                    # 标记热键为非激活状态（防止多次触发）
                    self._is_active = False
                    logger.debug("热键组合被释放，触发停用回调")
                    
                    # 添加独立的标志，避免在热键处理期间重复触发回调
                    # 使用原子操作检查和设置标志
                    deactivate_in_progress = getattr(self, '_deactivate_in_progress', False)
                    if not deactivate_in_progress:
                        # 设置处理中标志
                        self._deactivate_in_progress = True
                        try:
                            # 处理热键释放
                            self._handle_deactivate()
                        finally:
                            # 在完成处理后重置标志
                            self._deactivate_in_progress = False
            except Exception as e:
                logger.error(f"处理按键释放事件时出错: {e}")
                # 确保在发生错误时也重置标志
                if hasattr(self, '_deactivate_in_progress'):
                    self._deactivate_in_progress = False
    
    def _is_hotkey_matched(self) -> bool:
        """
        检查当前按下的键是否匹配热键组合。
        
        Returns:
            bool: 是否匹配
        """
        # 检查热键组合中的每个键是否都在按下的键集合中
        result = all(k in self._pressed_keys for k in self._hotkey_combo)
        logger.debug(f"热键匹配检查: {result} (热键组合: {self._hotkey_combo}, 当前按下的键: {self._pressed_keys})")
        return result 
        
    def is_hotkey_released(self) -> bool:
        """
        检查热键组合中的所有键是否都已释放。
        
        Returns:
            bool: 如果热键组合中的所有键都已释放，则返回True，否则返回False
        """
        with self._lock:
            # 检查是否有任何热键组合中的键仍然被按下
            for key in self._hotkey_combo:
                if key in self._pressed_keys:
                    logger.debug(f"热键 {key} 仍在按下状态")
                    return False
            logger.debug("所有热键都已释放")
            return True

    def _handle_deactivate(self):
        """处理热键释放事件"""
        logger.info(f"热键释放: {self._hotkey_combo}")
        if self._on_deactivate:
            if asyncio.iscoroutinefunction(self._on_deactivate):
                # 如果是协程函数，使用run_coroutine_threadsafe在主事件循环中执行
                try:
                    from nextalk_client.client_logic import NexTalkClient
                    client = self._on_deactivate.__self__
                    if isinstance(client, NexTalkClient) and client.loop:
                        logger.debug("使用run_coroutine_threadsafe执行异步热键释放回调")
                        try:
                            # 检查事件循环是否仍在运行
                            if client.loop.is_running() and not client.loop.is_closed():
                                # 添加重试逻辑，最多尝试3次
                                max_retries = 3
                                retry_count = 0
                                success = False
                                
                                while retry_count < max_retries and not success:
                                    try:
                                        future = asyncio.run_coroutine_threadsafe(
                                            self._on_deactivate(),
                                            client.loop
                                        )
                                        
                                        # 这里不能直接等待异步结果，因为这是在一个非异步上下文中调用的
                                        # 但我们可以添加一个回调来处理完成情况
                                        def done_callback(fut):
                                            try:
                                                fut.result()  # 获取结果，如果有异常会抛出
                                                logger.debug("热键释放回调执行完成")
                                            except asyncio.CancelledError:
                                                logger.warning("热键释放回调被取消")
                                            except Exception as e:
                                                logger.error(f"热键释放回调执行失败: {e}")
                                        
                                        future.add_done_callback(done_callback)
                                        success = True
                                    except Exception as e:
                                        logger.warning(f"尝试执行热键释放回调失败(尝试 {retry_count+1}/{max_retries}): {e}")
                                        retry_count += 1
                                        # 短暂等待后重试
                                        time.sleep(0.1)
                                
                                if not success:
                                    logger.error("热键释放回调执行失败，达到最大重试次数")
                            else:
                                logger.warning("事件循环已停止或关闭，无法执行热键释放回调")
                        except RuntimeError as e:
                            logger.error(f"执行热键释放回调时发生运行时错误: {e}")
                    else:
                        logger.error("无法获取事件循环执行异步热键释放回调")
                except Exception as e:
                    logger.error(f"执行异步热键释放回调时出错: {str(e)}")
            else:
                # 如果是普通函数，直接调用
                self._on_deactivate() 