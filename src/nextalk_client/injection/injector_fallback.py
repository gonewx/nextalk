"""
后备文本注入器实现。

提供多种后备注入方式：
1. 剪贴板粘贴
2. 模拟键盘输入
3. xdotool（Linux特定）
"""

import logging
import platform
import shutil
import subprocess
import time
from typing import Literal, Optional

from .injector_base import BaseInjector

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


class FallbackInjector(BaseInjector):
    """
    后备文本注入器，提供多种注入方式。
    """

    def __init__(self, method: Optional[Literal["paste", "type", "xdotool"]] = None):
        """
        初始化后备注入器。

        Args:
            method: 指定注入方法，None表示自动选择
        """
        self.method = method
        self.available = False
        self._init_methods()

    def _init_methods(self):
        """初始化可用的注入方法。"""
        self.has_paste = False
        self.has_type = False
        self.has_xdotool = False

        # 检查剪贴板粘贴
        if HAS_PYCLIP:
            self.has_paste = True
            self.clipboard_module = "pyclip"
        elif HAS_PYPERCLIP:
            self.has_paste = True
            self.clipboard_module = "pyperclip"

        # 检查模拟键入
        if HAS_PYAUTOGUI:
            self.has_type = True

        # 检查xdotool（仅Linux）
        if platform.system() == "Linux" and shutil.which("xdotool"):
            self.has_xdotool = True

        # 确定是否有可用方法
        self.available = self.has_paste or self.has_type or self.has_xdotool

        if self.available:
            logger.info(
                f"后备注入器初始化成功 - 可用方法: "
                f"粘贴={self.has_paste}, 键入={self.has_type}, xdotool={self.has_xdotool}"
            )
        else:
            logger.warning("后备注入器无可用方法")

    def inject_text(self, text: str) -> bool:
        """
        使用后备方法注入文本。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        if not text:
            return True

        if not self.available:
            logger.error("后备注入器无可用方法")
            return False

        # 根据指定方法或优先级尝试注入
        if self.method == "paste" or (self.method is None and self.has_paste):
            if self._inject_via_paste(text):
                return True

        if self.method == "xdotool" or (self.method is None and self.has_xdotool):
            if self._inject_via_xdotool(text):
                return True

        if self.method == "type" or (self.method is None and self.has_type):
            if self._inject_via_type(text):
                return True

        # 如果没有指定方法，尝试所有可用方法
        if self.method is None:
            # 优先尝试粘贴（最快）
            if self.has_paste and self._inject_via_paste(text):
                return True
            # 然后尝试xdotool（Linux特定但可靠）
            if self.has_xdotool and self._inject_via_xdotool(text):
                return True
            # 最后尝试模拟键入（最慢）
            if self.has_type and self._inject_via_type(text):
                return True

        logger.error("所有后备注入方法均失败")
        return False

    def _inject_via_paste(self, text: str) -> bool:
        """通过剪贴板粘贴注入文本。"""
        if not self.has_paste:
            return False

        try:
            # 保存原剪贴板内容
            original_clipboard = None
            try:
                if self.clipboard_module == "pyclip":
                    original_clipboard = pyclip.paste()
                    if isinstance(original_clipboard, bytes):
                        original_clipboard = original_clipboard.decode("utf-8", errors="ignore")
                else:  # pyperclip
                    original_clipboard = pyperclip.paste()
            except Exception as e:
                logger.debug(f"无法保存剪贴板内容: {e}")

            # 复制文本到剪贴板
            if self.clipboard_module == "pyclip":
                pyclip.copy(text)
            else:  # pyperclip
                pyperclip.copy(text)

            # 短暂延迟确保复制完成
            time.sleep(0.05)

            # 执行粘贴操作 - 先尝试终端快捷键，再尝试普通快捷键
            paste_success = False

            if HAS_PYAUTOGUI:
                if platform.system() == "Darwin":
                    pyautogui.hotkey("command", "v")
                    paste_success = True
                else:
                    # Linux: 先尝试终端粘贴快捷键
                    try:
                        pyautogui.hotkey("ctrl", "shift", "v")
                        paste_success = True
                    except Exception:
                        # 如果失败，尝试普通粘贴快捷键
                        try:
                            pyautogui.hotkey("ctrl", "v")
                            paste_success = True
                        except Exception:
                            paste_success = False
            else:
                # 使用xdotool作为后备
                if self.has_xdotool:
                    # 先尝试终端粘贴快捷键
                    result = subprocess.run(
                        ["xdotool", "key", "ctrl+shift+v"], capture_output=True, timeout=3
                    )
                    if result.returncode == 0:
                        paste_success = True
                    else:
                        # 尝试普通粘贴快捷键
                        result = subprocess.run(
                            ["xdotool", "key", "ctrl+v"], capture_output=True, timeout=3
                        )
                        paste_success = result.returncode == 0
                else:
                    return False

            if not paste_success:
                return False

            # 恢复原剪贴板内容
            if original_clipboard is not None:
                time.sleep(0.1)
                try:
                    if self.clipboard_module == "pyclip":
                        pyclip.copy(original_clipboard)
                    else:  # pyperclip
                        pyperclip.copy(original_clipboard)
                except Exception:
                    pass

            logger.debug(f"通过剪贴板粘贴成功注入文本，长度: {len(text)}")
            return True

        except Exception as e:
            logger.debug(f"剪贴板粘贴注入失败: {e}")
            return False

    def _inject_via_type(self, text: str) -> bool:
        """通过模拟键盘输入注入文本。"""
        if not self.has_type or not HAS_PYAUTOGUI:
            return False

        try:
            # 使用pyautogui模拟键入
            pyautogui.write(text)
            logger.debug(f"通过模拟键入成功注入文本，长度: {len(text)}")
            return True

        except Exception as e:
            logger.debug(f"模拟键入注入失败: {e}")
            return False

    def _inject_via_xdotool(self, text: str) -> bool:
        """通过xdotool注入文本（Linux特定）。"""
        if not self.has_xdotool:
            return False

        try:
            # 使用xdotool type命令
            result = subprocess.run(
                ["xdotool", "type", "--", text], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                logger.debug(f"通过xdotool成功注入文本，长度: {len(text)}")
                return True
            else:
                logger.debug(f"xdotool返回错误: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.debug("xdotool执行超时")
            return False
        except Exception as e:
            logger.debug(f"xdotool注入失败: {e}")
            return False

    def is_available(self) -> bool:
        """检查后备注入器是否可用。"""
        return self.available

    def get_available_methods(self) -> list[str]:
        """获取所有可用的注入方法。"""
        methods = []
        if self.has_paste:
            methods.append("paste")
        if self.has_type:
            methods.append("type")
        if self.has_xdotool:
            methods.append("xdotool")
        return methods
