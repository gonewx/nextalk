"""
文本注入器基类和工厂函数。

提供抽象基类定义标准接口，工厂函数返回适合当前平台的实现。
"""

import abc
import logging
import platform
import sys
from typing import Optional

# 设置日志记录器
logger = logging.getLogger(__name__)


class BaseInjector(abc.ABC):
    """
    文本注入器抽象基类。

    定义所有文本注入器实现必须提供的接口。
    """

    @abc.abstractmethod
    def inject_text(self, text: str) -> bool:
        """
        将文本注入到当前激活的应用程序或窗口。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        pass


def get_injector() -> Optional[BaseInjector]:
    """
    工厂函数，返回适合当前平台的文本注入器实例。

    目前仅支持Linux平台。未来将添加Windows和macOS支持。

    Returns:
        BaseInjector: 文本注入器实例，如果平台不支持则返回None
    """
    os_name = platform.system().lower()

    if os_name == "linux":
        try:
            # 动态导入，避免未使用Linux注入器时的导入错误
            from .injector_linux import LinuxInjector

            logger.info("使用Linux文本注入器")
            return LinuxInjector()
        except ImportError as e:
            logger.error(f"无法导入Linux文本注入器: {e}")
            return None
    else:
        logger.warning(f"平台 '{os_name}' 目前不支持文本注入")
        return None
