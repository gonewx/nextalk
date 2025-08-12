"""
智能文本注入器管理器。

自动选择最合适的注入方法，支持多种注入器的级联尝试。
"""

import logging
from typing import Optional, List
from .injector_base import BaseInjector
from .injector_fcitx import FcitxInjector
from .injector_ibus import IBusInjector
from .injector_fallback import FallbackInjector
from .ime_detector import IMEDetector

logger = logging.getLogger(__name__)


class SmartInjector(BaseInjector):
    """
    智能文本注入器，自动选择最佳注入方法。

    优先级：
    1. 输入法框架（Fcitx/IBus）- 最可靠，支持中文
    2. 剪贴板粘贴 - 快速，支持所有字符
    3. xdotool - Linux特定，较可靠
    4. 模拟键入 - 最慢，可能有编码问题
    """

    def __init__(self, prefer_ime: bool = True, fallback_method: Optional[str] = None):
        """
        初始化智能注入器。

        Args:
            prefer_ime: 是否优先使用输入法框架
            fallback_method: 后备方法偏好（'paste', 'type', 'xdotool'）
        """
        self.prefer_ime = prefer_ime
        self.fallback_method = fallback_method
        self.injectors: List[BaseInjector] = []
        self.primary_injector: Optional[BaseInjector] = None

        self._init_injectors()

    def _init_injectors(self):
        """初始化所有可用的注入器。"""

        if self.prefer_ime:
            # 获取输入法优先级列表
            ime_priority = IMEDetector.get_ime_priority_list()

            for ime_type in ime_priority:
                if ime_type == "fcitx":
                    try:
                        fcitx = FcitxInjector()
                        if fcitx.is_available():
                            self.injectors.append(fcitx)
                            if not self.primary_injector:
                                self.primary_injector = fcitx
                                logger.info("使用Fcitx作为主要注入器")
                    except Exception as e:
                        logger.debug(f"初始化Fcitx注入器失败: {e}")

                elif ime_type == "ibus":
                    try:
                        ibus = IBusInjector()
                        if ibus.is_available():
                            self.injectors.append(ibus)
                            if not self.primary_injector:
                                self.primary_injector = ibus
                                logger.info("使用IBus作为主要注入器")
                    except Exception as e:
                        logger.debug(f"初始化IBus注入器失败: {e}")

        # 添加后备注入器
        try:
            fallback = FallbackInjector(method=self.fallback_method)
            if fallback.is_available():
                self.injectors.append(fallback)
                if not self.primary_injector:
                    self.primary_injector = fallback
                    logger.info("使用后备方法作为主要注入器")
        except Exception as e:
            logger.debug(f"初始化后备注入器失败: {e}")

        if not self.injectors:
            logger.error("没有可用的注入器")
        else:
            logger.info(f"初始化了 {len(self.injectors)} 个注入器")

    def inject_text(self, text: str) -> bool:
        """
        智能注入文本，自动尝试多种方法。

        Args:
            text: 要注入的文本

        Returns:
            bool: 注入是否成功
        """
        if not text:
            return True

        if not self.injectors:
            logger.error("没有可用的注入器")
            return False

        # 首先尝试主要注入器
        if self.primary_injector:
            try:
                if self.primary_injector.inject_text(text):
                    return True
            except Exception as e:
                logger.debug(f"主要注入器失败: {e}")

        # 尝试其他注入器
        for injector in self.injectors:
            if injector == self.primary_injector:
                continue  # 已经尝试过了

            try:
                if injector.inject_text(text):
                    # 成功后更新主要注入器
                    self.primary_injector = injector
                    logger.info(f"切换主要注入器为: {type(injector).__name__}")
                    return True
            except Exception as e:
                logger.debug(f"{type(injector).__name__} 失败: {e}")

        logger.error("所有注入方法均失败")
        return False

    def is_available(self) -> bool:
        """检查是否有可用的注入器。"""
        return len(self.injectors) > 0

    def get_status(self) -> dict:
        """获取注入器状态信息。"""
        return {
            "available": self.is_available(),
            "injector_count": len(self.injectors),
            "primary_injector": type(self.primary_injector).__name__
            if self.primary_injector
            else None,
            "all_injectors": [type(inj).__name__ for inj in self.injectors],
        }
