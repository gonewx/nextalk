"""
IBus输入法框架的文本注入器实现。

使用IBus D-Bus接口直接提交文本到当前输入上下文。
"""

import logging
import subprocess
from typing import Optional
from .injector_base import BaseInjector

try:
    import dbus

    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

logger = logging.getLogger(__name__)


class IBusInjector(BaseInjector):
    """
    IBus输入法框架的文本注入器实现。

    通过D-Bus接口与IBus通信，将文本直接提交到当前输入上下文。
    """

    def __init__(self):
        """初始化IBus注入器。"""
        self.available = False
        self.ibus_interface = None
        self.input_context = None

        if not HAS_DBUS:
            logger.warning("python-dbus未安装，IBus注入器不可用")
            return

        try:
            # 连接到会话总线
            self.bus = dbus.SessionBus()

            # 检查IBus是否在运行
            if self._is_ibus_running():
                self._init_ibus()
            else:
                logger.debug("IBus未运行")

        except Exception as e:
            logger.debug(f"初始化IBus注入器失败: {e}")

    def _is_ibus_running(self) -> bool:
        """检查IBus是否在运行。"""
        try:
            # 检查IBus D-Bus服务
            obj = self.bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            iface = dbus.Interface(obj, "org.freedesktop.DBus")
            names = iface.ListNames()
            return "org.freedesktop.IBus" in names
        except:
            return False

    def _init_ibus(self):
        """初始化IBus接口。"""
        try:
            # 获取IBus主对象
            ibus_obj = self.bus.get_object("org.freedesktop.IBus", "/org/freedesktop/IBus")
            self.ibus_interface = dbus.Interface(ibus_obj, "org.freedesktop.IBus")

            # 尝试创建输入上下文
            context_path = self.ibus_interface.CreateInputContext("NextalkClient")
            if context_path:
                self.input_context = self.bus.get_object("org.freedesktop.IBus", context_path)
                self.available = True
                logger.info("IBus注入器初始化成功")
            else:
                logger.debug("无法创建IBus输入上下文")

        except Exception as e:
            logger.debug(f"初始化IBus接口失败: {e}")

    def inject_text(self, text: str) -> bool:
        """
        通过IBus提交文本到当前输入上下文。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        if not text:
            return True

        if not self.available or not self.input_context:
            logger.debug("IBus注入器不可用")
            return False

        try:
            # 获取输入上下文接口
            context_iface = dbus.Interface(self.input_context, "org.freedesktop.IBus.InputContext")

            # 提交文本
            # IBus使用Unicode码点，需要传入一个整数而不是字符串
            # 使用CommitText方法，传入IBus.Text对象

            # 创建IBus.Text对象
            text_variant = dbus.Struct(
                (
                    dbus.String(text),  # 文本内容
                    dbus.Array([], signature="v"),  # 属性列表（空）
                    dbus.UInt32(0),  # 光标位置
                    dbus.UInt32(len(text)),  # 锚点位置
                ),
                signature="savuu",
            )

            # 提交文本
            context_iface.CommitText(text_variant)

            logger.debug(f"通过IBus成功注入文本，长度: {len(text)}")
            return True

        except Exception as e:
            logger.debug(f"IBus文本注入失败: {e}")
            # 尝试备用方法
            try:
                # 某些IBus版本可能只需要简单的字符串
                context_iface = dbus.Interface(
                    self.input_context, "org.freedesktop.IBus.InputContext"
                )
                context_iface.CommitText(dbus.String(text))
                logger.debug(f"通过IBus备用方法成功注入文本")
                return True
            except:
                pass
            return False

    def is_available(self) -> bool:
        """检查IBus注入器是否可用。"""
        return self.available
