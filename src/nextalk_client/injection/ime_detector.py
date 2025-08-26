"""
输入法框架检测器。

自动检测系统正在使用的输入法框架(Fcitx/IBus)。
"""

import logging
import os
import subprocess
from typing import Literal

logger = logging.getLogger(__name__)

InputMethodType = Literal["fcitx", "ibus", "unknown"]


class IMEDetector:
    """
    输入法框架检测器。

    检测系统当前使用的输入法框架类型。
    """

    @staticmethod
    def detect_ime() -> InputMethodType:
        """
        检测当前系统使用的输入法框架。

        Returns:
            输入法类型: 'fcitx', 'ibus' 或 'unknown'
        """
        # 检查环境变量
        ime_type = IMEDetector._check_env_variables()
        if ime_type != "unknown":
            logger.info(f"通过环境变量检测到输入法: {ime_type}")
            return ime_type

        # 检查运行的进程
        ime_type = IMEDetector._check_running_processes()
        if ime_type != "unknown":
            logger.info(f"通过进程检测到输入法: {ime_type}")
            return ime_type

        # 检查D-Bus服务
        ime_type = IMEDetector._check_dbus_services()
        if ime_type != "unknown":
            logger.info(f"通过D-Bus服务检测到输入法: {ime_type}")
            return ime_type

        logger.debug("未检测到已知的输入法框架")
        return "unknown"

    @staticmethod
    def _check_env_variables() -> InputMethodType:
        """通过环境变量检测输入法。"""
        # 检查常见的输入法环境变量
        env_vars = {
            "GTK_IM_MODULE": os.environ.get("GTK_IM_MODULE", "").lower(),
            "QT_IM_MODULE": os.environ.get("QT_IM_MODULE", "").lower(),
            "XMODIFIERS": os.environ.get("XMODIFIERS", "").lower(),
            "INPUT_METHOD": os.environ.get("INPUT_METHOD", "").lower(),
        }

        # 统计各输入法出现次数
        fcitx_count = sum(1 for v in env_vars.values() if "fcitx" in v)
        ibus_count = sum(1 for v in env_vars.values() if "ibus" in v)

        if fcitx_count > ibus_count:
            return "fcitx"
        elif ibus_count > fcitx_count:
            return "ibus"

        return "unknown"

    @staticmethod
    def _check_running_processes() -> InputMethodType:
        """通过运行的进程检测输入法。"""
        try:
            # 检查fcitx进程
            fcitx_processes = ["fcitx5", "fcitx"]
            for proc_name in fcitx_processes:
                result = subprocess.run(
                    ["pgrep", "-x", proc_name], capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    return "fcitx"

            # 检查ibus进程
            result = subprocess.run(
                ["pgrep", "-x", "ibus-daemon"], capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                return "ibus"

        except Exception as e:
            logger.debug(f"进程检测失败: {e}")

        return "unknown"

    @staticmethod
    def _check_dbus_services() -> InputMethodType:
        """通过D-Bus服务检测输入法。"""
        try:
            import dbus

            bus = dbus.SessionBus()
            obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            iface = dbus.Interface(obj, "org.freedesktop.DBus")
            names = iface.ListNames()

            # 检查Fcitx服务
            if "org.fcitx.Fcitx5" in names or "org.fcitx.Fcitx" in names:
                return "fcitx"

            # 检查IBus服务
            if "org.freedesktop.IBus" in names:
                return "ibus"

        except Exception as e:
            logger.debug(f"D-Bus服务检测失败: {e}")

        return "unknown"

    @staticmethod
    def get_ime_priority_list() -> list[InputMethodType]:
        """
        获取输入法优先级列表。

        Returns:
            按优先级排序的输入法类型列表
        """
        detected = IMEDetector.detect_ime()

        if detected == "fcitx":
            # 如果检测到fcitx，优先使用fcitx
            return ["fcitx", "ibus", "unknown"]
        elif detected == "ibus":
            # 如果检测到ibus，优先使用ibus
            return ["ibus", "fcitx", "unknown"]
        else:
            # 默认优先级：fcitx > ibus
            return ["fcitx", "ibus", "unknown"]
