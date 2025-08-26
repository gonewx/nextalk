"""
Fcitx输入法框架的文本注入器实现。

使用Fcitx5 D-Bus接口直接提交文本到当前输入上下文。
"""

import logging

from .injector_base import BaseInjector

try:
    import dbus

    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False

logger = logging.getLogger(__name__)


class FcitxInjector(BaseInjector):
    """
    Fcitx输入法框架的文本注入器实现。

    通过D-Bus接口与Fcitx5通信，将文本直接提交到当前输入上下文。
    """

    def __init__(self):
        """初始化Fcitx注入器。"""
        self.available = False
        self.fcitx_interface = None

        if not HAS_DBUS:
            logger.warning("python-dbus未安装，Fcitx注入器不可用")
            return

        try:
            # 连接到会话总线
            self.bus = dbus.SessionBus()

            # 检查Fcitx5是否在运行
            if self._is_fcitx5_running():
                self._init_fcitx5()
            elif self._is_fcitx_running():
                self._init_fcitx()
            else:
                logger.debug("Fcitx未运行")

        except Exception as e:
            logger.debug(f"初始化Fcitx注入器失败: {e}")

    def _is_fcitx5_running(self) -> bool:
        """检查Fcitx5是否在运行。"""
        try:
            # 检查Fcitx5 D-Bus服务
            obj = self.bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            iface = dbus.Interface(obj, "org.freedesktop.DBus")
            names = iface.ListNames()
            return "org.fcitx.Fcitx5" in names
        except:
            return False

    def _is_fcitx_running(self) -> bool:
        """检查Fcitx (v4)是否在运行。"""
        try:
            # 检查Fcitx D-Bus服务
            obj = self.bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            iface = dbus.Interface(obj, "org.freedesktop.DBus")
            names = iface.ListNames()
            return "org.fcitx.Fcitx" in names
        except:
            return False

    def _init_fcitx5(self):
        """初始化Fcitx5接口。"""
        try:
            # 获取Fcitx5控制器对象
            obj = self.bus.get_object("org.fcitx.Fcitx5", "/controller")
            self.fcitx_interface = dbus.Interface(obj, "org.fcitx.Fcitx.Controller1")
            self.available = True
            self.version = 5
            logger.info("Fcitx5注入器初始化成功")
        except Exception as e:
            logger.debug(f"初始化Fcitx5接口失败: {e}")

    def _init_fcitx(self):
        """初始化Fcitx (v4)接口。"""
        try:
            # 获取Fcitx输入上下文
            obj = self.bus.get_object("org.fcitx.Fcitx", "/inputcontext")
            self.fcitx_interface = dbus.Interface(obj, "org.fcitx.Fcitx.InputContext")
            self.available = True
            self.version = 4
            logger.info("Fcitx注入器初始化成功")
        except Exception as e:
            logger.debug(f"初始化Fcitx接口失败: {e}")

    def inject_text(self, text: str) -> bool:
        """
        通过Fcitx提交文本到当前输入上下文。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        if not text:
            return True

        if not self.available or not self.fcitx_interface:
            logger.debug("Fcitx注入器不可用")
            return False

        try:
            if self.version == 5:
                # Fcitx5: 使用CommitString方法
                self.fcitx_interface.CommitString(text)
            else:
                # Fcitx4: 使用CommitString方法
                self.fcitx_interface.CommitString(text)

            logger.debug(f"通过Fcitx成功注入文本，长度: {len(text)}")
            return True

        except Exception as e:
            logger.debug(f"Fcitx文本注入失败: {e}")
            return False

    def is_available(self) -> bool:
        """检查Fcitx注入器是否可用。"""
        return self.available
