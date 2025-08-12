"""
测试文本注入器功能。
"""

import pytest
import sys
from unittest.mock import MagicMock, patch, Mock

# 添加源码路径
sys.path.insert(0, "src")

from nextalk_client.injection import BaseInjector, get_injector, SmartInjector, IMEDetector


class TestIMEDetector:
    """测试输入法检测器。"""

    def test_detect_ime_returns_valid_type(self):
        """测试检测输入法返回有效类型。"""
        ime_type = IMEDetector.detect_ime()
        assert ime_type in ["fcitx", "ibus", "unknown"]

    def test_get_ime_priority_list(self):
        """测试获取输入法优先级列表。"""
        priority = IMEDetector.get_ime_priority_list()
        assert isinstance(priority, list)
        assert len(priority) == 3
        assert set(priority) == {"fcitx", "ibus", "unknown"}

    @patch("nextalk_client.injection.ime_detector.os.environ.get")
    def test_check_env_variables_fcitx(self, mock_get):
        """测试环境变量检测Fcitx。"""
        mock_get.side_effect = lambda key, default="": {
            "GTK_IM_MODULE": "fcitx",
            "QT_IM_MODULE": "fcitx",
            "XMODIFIERS": "@im=fcitx",
            "INPUT_METHOD": "",
        }.get(key, default)

        ime_type = IMEDetector._check_env_variables()
        assert ime_type == "fcitx"

    @patch("nextalk_client.injection.ime_detector.os.environ.get")
    def test_check_env_variables_ibus(self, mock_get):
        """测试环境变量检测IBus。"""
        mock_get.side_effect = lambda key, default="": {
            "GTK_IM_MODULE": "ibus",
            "QT_IM_MODULE": "ibus",
            "XMODIFIERS": "@im=ibus",
            "INPUT_METHOD": "",
        }.get(key, default)

        ime_type = IMEDetector._check_env_variables()
        assert ime_type == "ibus"


class TestSmartInjector:
    """测试智能注入器。"""

    @patch("nextalk_client.injection.injector_manager.FcitxInjector")
    @patch("nextalk_client.injection.injector_manager.IBusInjector")
    @patch("nextalk_client.injection.injector_manager.FallbackInjector")
    def test_init_with_prefer_ime(self, mock_fallback, mock_ibus, mock_fcitx):
        """测试优先使用输入法框架初始化。"""
        # 设置模拟返回值
        mock_fcitx_instance = MagicMock()
        mock_fcitx_instance.is_available.return_value = True
        mock_fcitx.return_value = mock_fcitx_instance

        mock_fallback_instance = MagicMock()
        mock_fallback_instance.is_available.return_value = True
        mock_fallback.return_value = mock_fallback_instance

        # 创建智能注入器
        injector = SmartInjector(prefer_ime=True)

        # 验证是否尝试初始化Fcitx
        mock_fcitx.assert_called_once()
        assert len(injector.injectors) > 0
        assert injector.primary_injector is not None

    def test_inject_empty_text(self):
        """测试注入空文本。"""
        injector = SmartInjector()
        result = injector.inject_text("")
        assert result is True

    @patch("nextalk_client.injection.injector_manager.FallbackInjector")
    def test_inject_with_fallback(self, mock_fallback):
        """测试使用后备注入器注入。"""
        # 设置模拟返回值
        mock_fallback_instance = MagicMock()
        mock_fallback_instance.is_available.return_value = True
        mock_fallback_instance.inject_text.return_value = True
        mock_fallback.return_value = mock_fallback_instance

        # 创建智能注入器
        injector = SmartInjector(prefer_ime=False)

        # 测试注入
        result = injector.inject_text("测试文本")

        assert result is True
        mock_fallback_instance.inject_text.assert_called_once_with("测试文本")

    def test_get_status(self):
        """测试获取状态信息。"""
        injector = SmartInjector()
        status = injector.get_status()

        assert "available" in status
        assert "injector_count" in status
        assert "primary_injector" in status
        assert "all_injectors" in status
        assert isinstance(status["injector_count"], int)
        assert isinstance(status["all_injectors"], list)


class TestGetInjector:
    """测试get_injector工厂函数。"""

    @patch("nextalk_client.injection.injector_base.platform.system")
    def test_get_injector_linux_smart(self, mock_system):
        """测试Linux平台获取智能注入器。"""
        mock_system.return_value = "Linux"

        with patch("nextalk_client.injection.injector_base.SmartInjector") as mock_smart:
            mock_smart_instance = MagicMock()
            mock_smart.return_value = mock_smart_instance

            injector = get_injector(use_smart=True)

            mock_smart.assert_called_once()
            assert injector == mock_smart_instance

    @patch("nextalk_client.injection.injector_base.platform.system")
    def test_get_injector_linux_legacy(self, mock_system):
        """测试Linux平台获取旧版注入器。"""
        mock_system.return_value = "Linux"

        with patch("nextalk_client.injection.injector_base.LinuxInjector") as mock_linux:
            mock_linux_instance = MagicMock()
            mock_linux.return_value = mock_linux_instance

            injector = get_injector(use_smart=False, legacy=True)

            mock_linux.assert_called_once()
            assert injector == mock_linux_instance

    @patch("nextalk_client.injection.injector_base.platform.system")
    def test_get_injector_unsupported_platform(self, mock_system):
        """测试不支持的平台。"""
        mock_system.return_value = "Windows"

        injector = get_injector()

        assert injector is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
