"""
NexTalk设置窗口实现。

该模块提供了一个简单的设置窗口，允许用户配置NexTalk的各种选项，
如热键、语音识别模型、VAD敏感度等。
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional, Any
from pathlib import Path

# 设置日志记录器
logger = logging.getLogger(__name__)

class SettingsWindow:
    """
    NexTalk设置窗口类。
    
    提供一个图形界面，允许用户修改NexTalk的配置选项。
    """
    
    def __init__(self, title: str = "NexTalk设置"):
        """
        初始化设置窗口。
        
        Args:
            title: 窗口标题
        """
        self.title = title
        self.window: Optional[tk.Tk] = None
        self.is_visible = False
        
        # 配置选项存储
        self.config_values: Dict[str, Any] = {}
        
        # 保存配置的回调函数
        self.save_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def show(self, config: Dict[str, Any] = None, save_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """
        显示设置窗口。
        
        Args:
            config: 当前配置值字典
            save_callback: 保存配置时调用的回调函数
        """
        if self.is_visible:
            logger.debug("设置窗口已经显示，将其置于前台")
            if self.window:
                self.window.lift()
            return
        
        # 保存配置和回调
        if config:
            self.config_values = config.copy()
        self.save_callback = save_callback
        
        # 创建主窗口
        self.window = tk.Tk()
        self.window.title(self.title)
        self.window.geometry("500x600")
        self.window.minsize(400, 500)
        
        # 设置窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # 创建标签页控件
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建各个设置页面
        general_frame = self._create_general_tab(notebook)
        model_frame = self._create_model_tab(notebook)
        advanced_frame = self._create_advanced_tab(notebook)
        
        # 添加标签页
        notebook.add(general_frame, text="常规设置")
        notebook.add(model_frame, text="模型设置")
        notebook.add(advanced_frame, text="高级设置")
        
        # 创建保存和取消按钮
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill=tk.X, pady=10)
        
        save_button = tk.Button(button_frame, text="保存", command=self._save_settings)
        save_button.pack(side=tk.RIGHT, padx=10)
        
        cancel_button = tk.Button(button_frame, text="取消", command=self.hide)
        cancel_button.pack(side=tk.RIGHT, padx=10)
        
        # 标记为可见
        self.is_visible = True
        
        # 启动主循环
        self.window.mainloop()
    
    def _create_general_tab(self, parent: ttk.Notebook) -> tk.Frame:
        """
        创建常规设置标签页。
        
        Args:
            parent: 父级控件
            
        Returns:
            Frame控件
        """
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 热键设置
        hotkey_label = tk.Label(frame, text="启动热键:")
        hotkey_label.grid(row=0, column=0, sticky=tk.W, pady=10)
        
        hotkey_entry = tk.Entry(frame)
        hotkey_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10)
        hotkey_entry.insert(0, self.config_values.get('hotkey', 'ctrl+shift+space'))
        
        # 服务器地址设置
        server_url_label = tk.Label(frame, text="服务器地址:")
        server_url_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        
        server_url_entry = tk.Entry(frame)
        server_url_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=10)
        server_url_entry.insert(0, self.config_values.get('server_url', 'ws://127.0.0.1:8000/ws/stream'))
        
        # 语言设置
        locale_label = tk.Label(frame, text="语言:")
        locale_label.grid(row=2, column=0, sticky=tk.W, pady=10)
        
        locale_combo = ttk.Combobox(frame, values=["英语", "中文", "自动检测"])
        locale_combo.grid(row=2, column=1, sticky=tk.W+tk.E, padx=10)
        locale_combo.current(0)  # 默认选择英语
        
        # 设置grid布局的列宽度
        frame.columnconfigure(1, weight=1)
        
        # 添加一些填充空间
        tk.Label(frame).grid(row=3, column=0, pady=10)
        
        # 这里可以添加更多设置...
        
        return frame
    
    def _create_model_tab(self, parent: ttk.Notebook) -> tk.Frame:
        """
        创建模型设置标签页。
        
        Args:
            parent: 父级控件
            
        Returns:
            Frame控件
        """
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 模型大小选择
        model_label = tk.Label(frame, text="模型大小:")
        model_label.grid(row=0, column=0, sticky=tk.W, pady=10)
        
        model_combo = ttk.Combobox(frame, values=["tiny.en", "small.en", "base.en"])
        model_combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10)
        model_combo.current(1)  # 默认选择small.en
        
        # 设备选择
        device_label = tk.Label(frame, text="计算设备:")
        device_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        
        device_combo = ttk.Combobox(frame, values=["cuda", "cpu"])
        device_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=10)
        device_combo.current(0)  # 默认选择cuda
        
        # 计算精度
        compute_type_label = tk.Label(frame, text="计算精度:")
        compute_type_label.grid(row=2, column=0, sticky=tk.W, pady=10)
        
        compute_type_combo = ttk.Combobox(frame, values=["int8", "float16", "float32"])
        compute_type_combo.grid(row=2, column=1, sticky=tk.W+tk.E, padx=10)
        compute_type_combo.current(0)  # 默认选择int8
        
        # 模型路径
        model_path_label = tk.Label(frame, text="模型路径:")
        model_path_label.grid(row=3, column=0, sticky=tk.W, pady=10)
        
        model_path_entry = tk.Entry(frame)
        model_path_entry.grid(row=3, column=1, sticky=tk.W+tk.E, padx=10)
        model_path_entry.insert(0, self.config_values.get('model_path', '~/.cache/NexTalk/models'))
        
        # 设置grid布局的列宽度
        frame.columnconfigure(1, weight=1)
        
        return frame
    
    def _create_advanced_tab(self, parent: ttk.Notebook) -> tk.Frame:
        """
        创建高级设置标签页。
        
        Args:
            parent: 父级控件
            
        Returns:
            Frame控件
        """
        frame = tk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # VAD敏感度
        vad_label = tk.Label(frame, text="VAD敏感度:")
        vad_label.grid(row=0, column=0, sticky=tk.W, pady=10)
        
        vad_scale = tk.Scale(frame, from_=0, to=3, orient=tk.HORIZONTAL)
        vad_scale.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10)
        vad_scale.set(int(self.config_values.get('vad_sensitivity', 2)))
        
        # 端口设置
        port_label = tk.Label(frame, text="服务器端口:")
        port_label.grid(row=1, column=0, sticky=tk.W, pady=10)
        
        port_entry = tk.Entry(frame)
        port_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=10)
        port_entry.insert(0, self.config_values.get('port', '8000'))
        
        # 自动启动设置
        autostart_var = tk.BooleanVar()
        autostart_var.set(self.config_values.get('autostart', False))
        autostart_check = tk.Checkbutton(frame, text="系统启动时自动运行", variable=autostart_var)
        autostart_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # 调试模式设置
        debug_var = tk.BooleanVar()
        debug_var.set(self.config_values.get('debug', False))
        debug_check = tk.Checkbutton(frame, text="启用调试模式", variable=debug_var)
        debug_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # 设置grid布局的列宽度
        frame.columnconfigure(1, weight=1)
        
        return frame
    
    def _save_settings(self) -> None:
        """保存设置并调用回调函数。"""
        # 这里应该从UI控件中获取设置值
        # 目前只是一个占位符，在实际实现中需要收集所有控件的值
        
        # 在实际实现中，这里会收集所有设置值并更新self.config_values
        logger.debug("保存设置")
        
        if self.save_callback:
            try:
                self.save_callback(self.config_values)
                messagebox.showinfo("保存成功", "设置已保存")
            except Exception as e:
                logger.error(f"保存设置时出错: {e}")
                messagebox.showerror("保存失败", f"保存设置时出错: {e}")
        
        # 隐藏窗口
        self.hide()
    
    def hide(self) -> None:
        """隐藏设置窗口。"""
        if self.window:
            self.window.destroy()
            self.window = None
        self.is_visible = False
        logger.debug("设置窗口已关闭") 