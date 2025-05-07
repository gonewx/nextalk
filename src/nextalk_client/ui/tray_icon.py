"""
NexTalk系统托盘图标实现。

该模块使用pystray库实现系统托盘图标功能，提供：
- 显示当前NexTalk状态的图标
- 基本的系统托盘菜单（包括退出选项）
- 状态变化时的图标更新
- 模型选择子菜单（可以切换语音识别模型）
"""

import os
import logging
import threading
import platform
from pathlib import Path
from PIL import Image
import cairosvg
from io import BytesIO
from pystray import Icon, Menu, MenuItem
from typing import Callable, Dict, Optional, List

from nextalk_shared.constants import (
    STATUS_IDLE,
    STATUS_LISTENING,
    STATUS_PROCESSING,
    STATUS_ERROR,
    STATUS_DISCONNECTED,
    STATUS_CONNECTED
)

# 设置日志记录器
logger = logging.getLogger(__name__)

class SystemTrayIcon:
    """
    NexTalk系统托盘图标类。
    
    在系统托盘中显示应用图标，根据应用状态变化图标，
    并提供基本的菜单操作，包括模型选择菜单。
    """
    
    # 可用的语音识别模型列表
    AVAILABLE_MODELS = ["tiny.en", "small.en", "base.en"]
    
    # Ubuntu默认图标尺寸
    ICON_SIZE = 22
    
    # 内部使用的实际图标尺寸
    _INTERNAL_ICON_SIZE = 96  # 增大内部图标尺寸以确保足够清晰
    
    def __init__(self, name: str = "NexTalk"):
        """
        初始化系统托盘图标。
        
        Args:
            name: 应用名称，显示在图标旁边
        """
        self.name = name
        self.icon: Optional[Icon] = None
        self._icon_thread: Optional[threading.Thread] = None
        self._thread_stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 图标路径使用原来的路径
        self.icon_dir = Path(__file__).parent / "assets" / "icons"
        self.icons: Dict[str, Image.Image] = {}
        
        # 检测系统环境
        self._is_ubuntu = 'ubuntu' in platform.platform().lower()
        logger.debug(f"检测到操作系统: {platform.platform()}, 是否为Ubuntu: {self._is_ubuntu}")
        
        # 加载所有图标
        self._load_icons()
        
        # 当前状态
        self.current_state = STATUS_IDLE
        
        # 当前选中的模型
        self.current_model = "small.en"
    
    def _load_icons(self) -> None:
        """加载所有状态图标，支持SVG格式并处理尺寸问题。"""
        icon_files = {
            STATUS_IDLE: "idle.svg",
            STATUS_LISTENING: "listening.svg",
            STATUS_PROCESSING: "processing.svg",
            STATUS_ERROR: "error.svg"
        }
        
        # 在Ubuntu上pystray的AppIndicator后端可能会忽略图标的实际尺寸
        # 使用更大的内部尺寸可以确保图标清晰
        actual_size = self._INTERNAL_ICON_SIZE
        logger.debug(f"使用图标尺寸: {actual_size}x{actual_size}")
        
        # 尝试加载所有图标
        for state, filename in icon_files.items():
            icon_path = self.icon_dir / filename
            try:
                if icon_path.exists():
                    # 处理SVG格式图标
                    if filename.lower().endswith('.svg'):
                        png_data = cairosvg.svg2png(
                            url=str(icon_path), 
                            output_width=actual_size, 
                            output_height=actual_size
                        )
                        self.icons[state] = Image.open(BytesIO(png_data))
                    else:
                        # 对于非SVG图标，加载后调整尺寸
                        img = Image.open(icon_path)
                        self.icons[state] = img.resize((actual_size, actual_size))
                    logger.debug(f"已加载图标: {filename}, 尺寸: {self.icons[state].width}x{self.icons[state].height}")
                else:
                    logger.warning(f"图标文件不存在: {icon_path}")
            except Exception as e:
                logger.error(f"加载图标文件 {filename} 失败: {e}")
        
        # 确保至少有一个图标可用（用IDLE作为默认）
        if STATUS_IDLE not in self.icons and len(self.icons) > 0:
            # 使用任何可用的图标作为IDLE状态的图标
            self.icons[STATUS_IDLE] = next(iter(self.icons.values()))
            logger.warning("使用替代图标作为IDLE状态图标")
        elif len(self.icons) == 0:
            logger.error("没有可用的图标文件！系统托盘图标将无法正常显示")
    
    def start(self, on_quit: Callable[[], None], model_select_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        启动系统托盘图标。
        
        Args:
            on_quit: 当用户点击退出菜单项时的回调函数
            model_select_callback: 当用户选择语音识别模型时的回调函数
            
        Returns:
            启动是否成功
        """
        if not self.icons:
            logger.error("没有图标可用，无法启动系统托盘图标")
            return False
            
        try:
            # 创建模型选择子菜单
            model_menu_items = []
            if model_select_callback:
                for model in self.AVAILABLE_MODELS:
                    model_menu_items.append(
                        MenuItem(
                            model, 
                            lambda item, model_name=model: self._handle_model_select(model_name, model_select_callback),
                            checked=lambda item, model_name=model: self.current_model == model_name
                        )
                    )
                logger.debug(f"已创建模型选择子菜单，包含 {len(model_menu_items)} 个选项")
            
            # 创建主菜单
            menu_items = []
            
            # 添加模型选择子菜单（如果回调函数存在）
            if model_select_callback and model_menu_items:
                menu_items.append(
                    MenuItem("选择模型", Menu(*model_menu_items))
                )
            
            # 添加退出菜单项
            menu_items.append(
                MenuItem("退出", lambda: self._handle_quit(on_quit))
            )
            
            # 创建菜单
            menu = Menu(*menu_items)
            
            # 创建图标
            with self._lock:
                # 使用当前状态的图标，如果不存在则使用IDLE状态的图标
                icon_image = self.icons.get(self.current_state, self.icons.get(STATUS_IDLE))
                if not icon_image:
                    logger.error("无法获取系统托盘图标图像")
                    return False
                
                # 创建pystray图标
                self.icon = Icon(
                    name=self.name,
                    icon=icon_image,
                    title=f"NexTalk - {self.current_state or 'idle'}",  # 确保空状态时显示为idle
                    menu=menu
                )
            
            # 在新线程中运行图标
            self._thread_stop_event.clear()
            self._icon_thread = threading.Thread(
                target=self._run_icon,
                name="NexTalk-TrayIcon",
                daemon=True
            )
            self._icon_thread.start()
            
            logger.debug("系统托盘图标已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动系统托盘图标失败: {e}")
            return False
    
    def _handle_model_select(self, model_name: str, callback: Callable[[str], None]) -> None:
        """
        处理模型选择菜单项点击。
        
        Args:
            model_name: 选择的模型名称
            callback: 回调函数
        """
        if model_name == self.current_model:
            logger.debug(f"模型 {model_name} 已经是当前模型，不做更改")
            return
            
        logger.debug(f"用户选择了语音识别模型: {model_name}")
        
        # 更新当前模型
        self.current_model = model_name
        
        # 调用回调函数
        try:
            callback(model_name)
        except Exception as e:
            logger.error(f"执行模型选择回调时出错: {e}")
    
    def _run_icon(self) -> None:
        """在独立线程中运行图标。"""
        try:
            if self.icon:
                self.icon.run()
        except Exception as e:
            logger.error(f"图标运行失败: {e}")
        finally:
            logger.debug("图标线程退出")
    
    def _handle_quit(self, on_quit: Callable[[], None]) -> None:
        """
        处理退出菜单项点击。
        
        Args:
            on_quit: 退出回调函数
        """
        logger.debug("用户从系统托盘菜单请求退出")
        
        # 先停止图标
        self.stop()
        
        # 然后调用退出回调
        try:
            on_quit()
        except Exception as e:
            logger.error(f"执行退出回调时出错: {e}")
    
    def stop(self) -> None:
        """停止系统托盘图标。"""
        # 设置停止事件
        self._thread_stop_event.set()
        
        # 停止图标
        with self._lock:
            if self.icon:
                try:
                    self.icon.stop()
                    logger.debug("系统托盘图标已停止")
                except Exception as e:
                    logger.error(f"停止系统托盘图标时出错: {e}")
                finally:
                    self.icon = None
        
        # 等待线程结束（有超时）
        if self._icon_thread and self._icon_thread.is_alive():
            try:
                self._icon_thread.join(timeout=2.0)
                if self._icon_thread.is_alive():
                    logger.warning("图标线程未在预期时间内结束")
            except Exception as e:
                logger.error(f"等待图标线程结束时出错: {e}")
            finally:
                self._icon_thread = None
    
    def update_state(self, state: str) -> None:
        """
        更新图标状态。
        
        根据新的状态更新系统托盘图标的外观。
        
        Args:
            state: 新状态，应该是STATUS_*常量之一
        """
        # 记录状态变化
        old_state = self.current_state
        
        # 处理空状态情况
        if not state:
            logger.debug(f"收到空状态，保持当前状态: {old_state}")
            return
        
        self.current_state = state
        
        logger.debug(f"更新托盘图标状态: {old_state} -> {state}")
        
        # 如果图标还没有创建，就不需要更新
        if not self.icon:
            logger.warning("托盘图标未创建，跳过状态更新")
            return
            
        # 确保状态有对应的图标
        display_state = state
        if state not in self.icons:
            # 使用一些映射来处理没有专门图标的状态
            if state == STATUS_CONNECTED:
                display_state = STATUS_IDLE
                logger.debug(f"状态映射: {state} -> {display_state}")
            elif state == STATUS_DISCONNECTED:
                display_state = STATUS_ERROR
                logger.debug(f"状态映射: {state} -> {display_state}")
                
            # 如果仍然没有对应的图标，使用IDLE状态的图标
            if display_state not in self.icons:
                display_state = STATUS_IDLE
                logger.debug(f"状态映射(默认): {state} -> {display_state}")
                
        # 确认最终使用的图标状态
        logger.debug(f"最终托盘图标显示状态: {display_state}")
                
        # 更新图标
        with self._lock:
            if self.icon:
                try:
                    # 获取当前状态对应的图标
                    new_icon = self.icons.get(display_state)
                    if new_icon:
                        # 更新图标和标题
                        self.icon.icon = new_icon
                        self.icon.title = f"NexTalk - {state}"
                        logger.debug(f"托盘图标和标题已更新: 图标={display_state}, 标题={state}")
                    else:
                        logger.error(f"未找到状态 {display_state} 对应的图标")
                except Exception as e:
                    logger.error(f"更新图标状态时出错: {e}")
            else:
                logger.warning("托盘图标对象为空，无法更新状态")
    
    def update_current_model(self, model_name: str) -> None:
        """
        更新当前选中的模型。
        
        Args:
            model_name: 新的模型名称
        """
        if model_name not in self.AVAILABLE_MODELS:
            logger.warning(f"尝试设置未知模型: {model_name}")
            return
            
        if model_name == self.current_model:
            return
            
        logger.debug(f"更新当前模型: {self.current_model} -> {model_name}")
        self.current_model = model_name 