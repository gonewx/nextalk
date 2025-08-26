"""
文本注入器基类和工厂函数。

提供抽象基类定义标准接口，工厂函数返回适合当前平台的实现。
"""

import abc
import logging
import platform
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


def get_injector(use_smart: bool = True, legacy: bool = False) -> Optional[BaseInjector]:
    """
    工厂函数，返回适合当前平台的文本注入器实例。

    Args:
        use_smart: 是否使用智能注入器（自动选择最佳方法）
        legacy: 是否使用旧版注入器（兼容性选项）

    Returns:
        BaseInjector: 文本注入器实例，如果平台不支持则返回None
    """
    os_name = platform.system().lower()

    if os_name == "linux":
        # 如果指定使用旧版注入器
        if legacy:
            try:
                from .injector_linux import LinuxInjector

                logger.info("使用旧版Linux文本注入器")
                return LinuxInjector()
            except ImportError as e:
                logger.error(f"无法导入旧版Linux文本注入器: {e}")
                return None

        # 使用智能注入器
        if use_smart:
            try:
                from .injector_manager import SmartInjector

                logger.info("使用智能文本注入器")
                return SmartInjector()
            except ImportError as e:
                logger.error(f"无法导入智能注入器: {e}")
                # 尝试后备到旧版
                try:
                    from .injector_linux import LinuxInjector

                    logger.info("后备到旧版Linux文本注入器")
                    return LinuxInjector()
                except ImportError:
                    return None
        else:
            # 直接使用后备注入器
            try:
                from .injector_fallback import FallbackInjector

                logger.info("使用后备文本注入器")
                return FallbackInjector()
            except ImportError as e:
                logger.error(f"无法导入后备注入器: {e}")
                return None
    else:
        logger.warning(f"平台 '{os_name}' 目前不支持文本注入")
        return None
