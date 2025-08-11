"""
测试FunASR模型处理

此测试文件用于验证FunASR模型处理功能，特别是在处理空音频数据时的行为
"""

import os
import sys
import asyncio
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

# 添加src目录到系统路径，使能够导入模块
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from nextalk_server.funasr_model import FunASRModel


@pytest.mark.asyncio
async def test_process_empty_audio_data():
    """测试处理空音频数据的情况"""

    # 模拟FunASR的AutoModel
    mock_auto_model = MagicMock()
    mock_auto_model.return_value = MagicMock()

    # 使用patch来替换AutoModel
    with (
        patch("nextalk_server.funasr_model.AutoModel", mock_auto_model),
        patch("nextalk_server.funasr_model.FUNASR_AVAILABLE", True),
        patch("nextalk_server.funasr_model.get_config") as mock_config,
    ):
        # 配置mock_config
        mock_config.return_value = MagicMock(
            model_path="./models", device="cpu", funasr_disable_update=True, ncpu=1, ngpu=0
        )

        # 创建FunASRModel实例
        config = mock_config.return_value
        model = FunASRModel(config)

        # 手动设置模型已初始化
        model._initialized = True

        # 创建模拟的模型实例
        model.online_model = MagicMock()
        model.offline_model = MagicMock()

        # 生成空音频数据
        empty_audio_data = bytes()

        # 处理空音频数据
        result = await model.process_audio_chunk(empty_audio_data, is_final=True)

        # 验证结果包含错误信息
        assert result.get("error") == "空音频数据" or result.get("error_offline") == "空音频数据"
        assert result.get("text") == ""
        assert result.get("is_final") is True


@pytest.mark.asyncio
async def test_process_audio_with_empty_result():
    """测试模型返回空结果的情况"""

    # 模拟FunASR的AutoModel
    mock_auto_model = MagicMock()
    mock_auto_model.return_value = MagicMock()

    # 使用patch来替换AutoModel
    with (
        patch("nextalk_server.funasr_model.AutoModel", mock_auto_model),
        patch("nextalk_server.funasr_model.FUNASR_AVAILABLE", True),
        patch("nextalk_server.funasr_model.get_config") as mock_config,
    ):
        # 配置mock_config
        mock_config.return_value = MagicMock(
            model_path="./models", device="cpu", funasr_disable_update=True, ncpu=1, ngpu=0
        )

        # 创建FunASRModel实例
        config = mock_config.return_value
        model = FunASRModel(config)

        # 手动设置模型已初始化
        model._initialized = True

        # 创建模拟的模型实例
        model.online_model = MagicMock()
        model.offline_model = MagicMock()

        # 设置模型返回空列表
        model.online_model.generate.return_value = []
        model.offline_model.generate.return_value = []

        # 生成一些音频数据
        audio_data = np.zeros(1600, dtype=np.int16).tobytes()

        # 处理音频数据
        result = await model.process_audio_chunk(audio_data, is_final=True)

        # 验证结果能够处理空结果
        assert result.get("text") == ""
        assert result.get("is_final") is True


if __name__ == "__main__":
    asyncio.run(test_process_empty_audio_data())
    asyncio.run(test_process_audio_with_empty_result())
    print("所有测试通过")
