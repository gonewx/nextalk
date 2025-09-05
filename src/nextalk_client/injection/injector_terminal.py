"""
终端专用文本注入器。

专门处理终端应用程序的文本注入，支持终端特有的粘贴快捷键和行为。
"""

import logging
import os
import platform
import subprocess
import time
from typing import Any, Dict, Optional

from .injector_base import BaseInjector

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    import pyautogui

    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pyclip

    HAS_PYCLIP = True
except ImportError:
    HAS_PYCLIP = False

try:
    import pyperclip

    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


class TerminalInjector(BaseInjector):
    """
    终端专用文本注入器。

    专门针对终端应用程序进行优化，支持：
    - 终端特有的粘贴快捷键 (Ctrl+Shift+V)
    - 活动窗口检测
    - 多种后备方案
    """

    # 已知的终端应用程序
    TERMINAL_PROCESSES = {
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "lxterminal",
        "mate-terminal",
        "terminator",
        "tilix",
        "alacritty",
        "kitty",
        "urxvt",
        "rxvt",
        "xterm",
        "aterm",
        "eterm",
        "wezterm",
        "terminal",
        "iterm2",
        "hyper",
        "tabby",
    }

    # 终端窗口标题模式
    TERMINAL_WINDOW_PATTERNS = {"terminal", "console", "shell", "bash", "zsh", "fish", "cmd"}

    def __init__(self):
        """初始化终端注入器。"""
        self.available = False
        self.clipboard_module = None
        self.has_xdotool = False
        self.has_ydotool = False
        self._init_dependencies()

    def _init_dependencies(self):
        """初始化依赖项。"""
        # 检查剪贴板模块
        if HAS_PYCLIP:
            self.clipboard_module = "pyclip"
        elif HAS_PYPERCLIP:
            self.clipboard_module = "pyperclip"

        # 检查工具
        if platform.system() == "Linux":
            self.has_xdotool = (
                subprocess.run(["which", "xdotool"], capture_output=True).returncode == 0
            )

            self.has_ydotool = (
                subprocess.run(["which", "ydotool"], capture_output=True).returncode == 0
            )

        # 确定可用性
        self.available = self.clipboard_module is not None and (
            HAS_PYAUTOGUI or self.has_xdotool or self.has_ydotool
        )

        if self.available:
            logger.info(
                f"终端注入器初始化成功 - "
                f"剪贴板={self.clipboard_module}, "
                f"热键工具={'PyAutoGUI' if HAS_PYAUTOGUI else 'xdotool' if self.has_xdotool else 'ydotool'}"
            )
        else:
            logger.warning("终端注入器缺少依赖，不可用")

    def is_terminal_focused(self) -> bool:
        """检查当前是否有终端窗口获得焦点。"""
        try:
            if not self.has_xdotool:
                return False

            # 获取活动窗口ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=2
            )

            if result.returncode != 0:
                return False

            window_id = result.stdout.strip()

            # 获取窗口信息
            window_info = self._get_window_info(window_id)

            # 检查进程名
            if window_info.get("process_name", "").lower() in self.TERMINAL_PROCESSES:
                return True

            # 检查窗口标题
            window_title = window_info.get("window_title", "").lower()
            for pattern in self.TERMINAL_WINDOW_PATTERNS:
                if pattern in window_title:
                    return True

            return False

        except Exception as e:
            logger.debug(f"检测终端焦点失败: {e}")
            return False

    def _get_window_info(self, window_id: str) -> Dict[str, Any]:
        """获取窗口信息。"""
        info = {}

        try:
            # 获取窗口标题
            result = subprocess.run(
                ["xdotool", "getwindowname", window_id], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                info["window_title"] = result.stdout.strip()

            # 获取进程PID
            result = subprocess.run(
                ["xdotool", "getwindowpid", window_id], capture_output=True, text=True, timeout=2
            )

            if result.returncode == 0:
                pid = int(result.stdout.strip())
                if HAS_PSUTIL:
                    try:
                        process = psutil.Process(pid)
                        info["process_name"] = process.name()
                        info["process_exe"] = process.exe()
                    except Exception:
                        pass
                else:
                    # 后备方法：通过 /proc 文件系统获取进程信息
                    try:
                        with open(f"/proc/{pid}/comm", "r") as f:
                            info["process_name"] = f.read().strip()
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"获取窗口信息失败: {e}")

        return info

    def get_terminal_info(self) -> Dict[str, Any]:
        """获取终端环境信息。"""
        info = {
            "is_terminal_focused": self.is_terminal_focused(),
            "terminal_env_vars": {},
            "available_tools": [],
        }

        # 检查终端相关环境变量
        terminal_vars = ["TERM", "TERMINAL", "COLORTERM", "TERM_PROGRAM"]
        for var in terminal_vars:
            value = os.environ.get(var)
            if value:
                info["terminal_env_vars"][var] = value

        # 可用工具
        if HAS_PYAUTOGUI:
            info["available_tools"].append("pyautogui")
        if self.has_xdotool:
            info["available_tools"].append("xdotool")
        if self.has_ydotool:
            info["available_tools"].append("ydotool")
        if self.clipboard_module:
            info["available_tools"].append(self.clipboard_module)

        return info

    def inject_text(self, text: str) -> bool:
        """
        在终端中注入文本。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        if not text:
            return True

        if not self.available:
            logger.debug("终端注入器不可用")
            return False

        logger.debug(f"开始终端文本注入，长度: {len(text)}")

        # 优先尝试终端粘贴快捷键
        if self._inject_via_terminal_paste(text):
            return True

        # 后备到普通粘贴
        if self._inject_via_normal_paste(text):
            return True

        # 最后尝试xdotool/ydotool type
        if self._inject_via_tool_type(text):
            return True

        logger.error("所有终端注入方法均失败")
        return False

    def _inject_via_terminal_paste(self, text: str) -> bool:
        """使用终端粘贴快捷键注入文本。"""
        if not self.clipboard_module:
            return False

        try:
            # 保存原剪贴板内容
            original_clipboard = self._get_clipboard()

            # 复制文本到剪贴板
            self._set_clipboard(text)
            time.sleep(0.05)

            # 使用终端粘贴快捷键
            success = False

            if HAS_PYAUTOGUI:
                # 尝试终端粘贴快捷键 (Ctrl+Shift+V)
                pyautogui.hotkey("ctrl", "shift", "v")
                success = True
            elif self.has_xdotool:
                result = subprocess.run(
                    ["xdotool", "key", "ctrl+shift+v"], capture_output=True, timeout=3
                )
                success = result.returncode == 0
            elif self.has_ydotool:
                result = subprocess.run(
                    ["ydotool", "key", "ctrl+shift+v"], capture_output=True, timeout=3
                )
                success = result.returncode == 0

            # 恢复剪贴板
            if original_clipboard is not None:
                time.sleep(0.1)
                self._set_clipboard(original_clipboard)

            if success:
                logger.debug(f"通过终端粘贴成功注入文本，长度: {len(text)}")
                return True

        except Exception as e:
            logger.debug(f"终端粘贴注入失败: {e}")

        return False

    def _inject_via_normal_paste(self, text: str) -> bool:
        """使用普通粘贴快捷键注入文本。"""
        if not self.clipboard_module:
            return False

        try:
            # 保存原剪贴板内容
            original_clipboard = self._get_clipboard()

            # 复制文本到剪贴板
            self._set_clipboard(text)
            time.sleep(0.05)

            # 使用普通粘贴快捷键
            success = False

            if HAS_PYAUTOGUI:
                pyautogui.hotkey("ctrl", "v")
                success = True
            elif self.has_xdotool:
                result = subprocess.run(
                    ["xdotool", "key", "ctrl+v"], capture_output=True, timeout=3
                )
                success = result.returncode == 0
            elif self.has_ydotool:
                result = subprocess.run(
                    ["ydotool", "key", "ctrl+v"], capture_output=True, timeout=3
                )
                success = result.returncode == 0

            # 恢复剪贴板
            if original_clipboard is not None:
                time.sleep(0.1)
                self._set_clipboard(original_clipboard)

            if success:
                logger.debug(f"通过普通粘贴成功注入文本，长度: {len(text)}")
                return True

        except Exception as e:
            logger.debug(f"普通粘贴注入失败: {e}")

        return False

    def _inject_via_tool_type(self, text: str) -> bool:
        """使用工具模拟键入注入文本。"""
        try:
            if self.has_xdotool:
                result = subprocess.run(
                    ["xdotool", "type", "--", text], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    logger.debug(f"通过xdotool键入成功注入文本，长度: {len(text)}")
                    return True

            elif self.has_ydotool:
                result = subprocess.run(
                    ["ydotool", "type", text], capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    logger.debug(f"通过ydotool键入成功注入文本，长度: {len(text)}")
                    return True

            elif HAS_PYAUTOGUI:
                pyautogui.write(text)
                logger.debug(f"通过PyAutoGUI键入成功注入文本，长度: {len(text)}")
                return True

        except Exception as e:
            logger.debug(f"工具键入注入失败: {e}")

        return False

    def _get_clipboard(self) -> Optional[str]:
        """获取剪贴板内容。"""
        try:
            if self.clipboard_module == "pyclip":
                content = pyclip.paste()
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")
                return content
            elif self.clipboard_module == "pyperclip":
                return pyperclip.paste()
        except Exception as e:
            logger.debug(f"获取剪贴板内容失败: {e}")
        return None

    def _set_clipboard(self, text: str):
        """设置剪贴板内容。"""
        if self.clipboard_module == "pyclip":
            pyclip.copy(text)
        elif self.clipboard_module == "pyperclip":
            pyperclip.copy(text)

    def is_available(self) -> bool:
        """检查终端注入器是否可用。"""
        return self.available

    def get_available_methods(self) -> list[str]:
        """获取所有可用的注入方法。"""
        methods = []

        if self.clipboard_module and (HAS_PYAUTOGUI or self.has_xdotool or self.has_ydotool):
            methods.append("terminal_paste")
            methods.append("normal_paste")

        if self.has_xdotool:
            methods.append("xdotool_type")
        elif self.has_ydotool:
            methods.append("ydotool_type")
        elif HAS_PYAUTOGUI:
            methods.append("pyautogui_type")

        return methods
