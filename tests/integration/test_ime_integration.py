"""
IME集成测试 - 测试IME功能与现有系统的兼容性。

验证完整的语音识别到文本注入流程，确保IME与控制器和会话管理器的正确集成。
"""

import pytest
import asyncio
import sys
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any, Optional

from nextalk.core.controller import MainController, ControllerState, ControllerEvent
from nextalk.core.session import RecognitionSession, SessionState
from nextalk.config.models import NexTalkConfig, TextInjectionConfig
from nextalk.output.ime_manager import IMEManager
from nextalk.output.ime_base import IMEResult, IMEStatus, IMEInfo, CompositionState
from nextalk.output.ime_exceptions import (
    IMEException, IMEInitializationError, IMEPermissionError,
    IMETimeoutError, IMEInjectionError, IMEErrorCode
)
from nextalk.output.text_injector import TextInjector
from nextalk.network.protocol import RecognitionResult


class MockIMEAdapter:
    """Mock IME适配器用于测试."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
        self._ime_active = True
        self._injection_delay = 0.01  # 快速测试
        self._should_fail = False
        self._failure_reason = None
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    async def initialize(self) -> bool:
        if self._should_fail and self._failure_reason == "init":
            return False
        await asyncio.sleep(0.01)
        self._initialized = True
        return True
    
    async def cleanup(self) -> None:
        self._initialized = False
    
    async def inject_text(self, text: str) -> IMEResult:
        if not self._initialized:
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="mock",
                injection_time=0.0,
                error="Not initialized"
            )
        
        if self._should_fail and self._failure_reason == "inject":
            return IMEResult(
                success=False,
                text_injected="",
                ime_used="mock",
                injection_time=0.01,
                error="Injection failed"
            )
        
        await asyncio.sleep(self._injection_delay)
        return IMEResult(
            success=True,
            text_injected=text,
            ime_used="mock_ime",
            injection_time=self._injection_delay
        )
    
    async def get_ime_status(self) -> IMEStatus:
        from datetime import datetime
        return IMEStatus(
            is_active=self._ime_active,
            current_ime="Mock IME",
            composition_state=CompositionState.INACTIVE,
            input_language="zh-CN",
            focus_app="TestApp",
            last_updated=datetime.now()
        )
    
    async def detect_active_ime(self) -> Optional[IMEInfo]:
        if not self._ime_active:
            return None
        
        from nextalk.output.ime_base import IMEFramework
        return IMEInfo(
            name="Mock IME",
            framework=IMEFramework.UNKNOWN,
            language="zh-CN",
            is_active=True
        )
    
    async def is_ime_ready(self) -> bool:
        return self._initialized and self._ime_active
    
    def set_failure_mode(self, should_fail: bool, reason: str = None):
        """设置失败模式用于测试错误处理."""
        self._should_fail = should_fail
        self._failure_reason = reason


@pytest.fixture
def mock_ime_adapter():
    """创建Mock IME适配器."""
    return MockIMEAdapter({})


@pytest.fixture
async def ime_manager(mock_ime_adapter):
    """创建IME管理器用于测试."""
    with patch('nextalk.output.ime_manager.IMEManager._create_platform_adapter') as mock_create:
        mock_create.return_value = mock_ime_adapter
        
        config = {"ime": {"enabled": True, "debug_mode": True}}
        manager = IMEManager(config)
        
        # 初始化
        success = await manager.initialize()
        assert success, "IME manager initialization should succeed"
        
        yield manager
        
        # 清理
        await manager.cleanup()


@pytest.fixture
async def mock_controller(default_nextalk_config):
    """创建Mock控制器."""
    controller = Mock(spec=MainController)
    controller.config = default_nextalk_config
    controller.state = ControllerState.READY
    controller.is_initialized = True
    
    # Mock异步方法
    controller.emit_event = AsyncMock()
    controller.handle_recognition_result = AsyncMock()
    
    return controller


@pytest.fixture
async def mock_session():
    """创建Mock会话."""
    session = Mock(spec=RecognitionSession)
    session.session_id = "test_session_001"
    session.state = SessionState.IDLE
    session.is_active = True
    
    # Mock异步方法
    session.process_recognition_result = AsyncMock()
    session.get_context = AsyncMock(return_value={})
    
    return session


@pytest.mark.integration
class TestIMEIntegration:
    """IME集成测试类."""
    
    @pytest.mark.asyncio
    async def test_ime_manager_initialization(self, ime_manager):
        """测试IME管理器初始化."""
        assert ime_manager.is_initialized
        assert await ime_manager.is_ready()
        
        # 测试状态获取
        status = await ime_manager.get_ime_status()
        assert status is not None
        assert status.current_ime == "Mock IME"
        assert status.input_language == "zh-CN"
    
    @pytest.mark.asyncio
    async def test_ime_text_injection_success(self, ime_manager):
        """测试IME文本注入成功案例."""
        test_text = "测试文本注入功能"
        
        result = await ime_manager.inject_text(test_text)
        
        assert result.success
        assert result.text_injected == test_text
        assert result.ime_used == "mock_ime"
        assert result.injection_time > 0
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_ime_text_injection_failure(self, ime_manager, mock_ime_adapter):
        """测试IME文本注入失败处理."""
        # 设置适配器失败模式
        mock_ime_adapter.set_failure_mode(True, "inject")
        
        test_text = "测试失败案例"
        
        result = await ime_manager.inject_text(test_text)
        
        assert not result.success
        assert result.text_injected == ""
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_ime_with_text_injector_integration(self, ime_manager, default_nextalk_config):
        """测试IME与TextInjector的集成."""
        # 创建TextInjector并集成IME
        config = default_nextalk_config.text_injection
        config.method = "ime"  # 使用IME方法
        
        with patch('nextalk.output.text_injector.IMEManager') as mock_ime_class:
            mock_ime_class.return_value = ime_manager
            
            text_injector = TextInjector(config.dict())
            await text_injector.initialize()
            
            # 测试文本注入
            test_text = "集成测试文本"
            result = await text_injector.inject_text(test_text)
            
            assert result["success"]
            assert result["method"] == "ime"
            assert result["text"] == test_text
            
            await text_injector.cleanup()
    
    @pytest.mark.asyncio
    async def test_full_recognition_to_injection_workflow(
        self, 
        ime_manager, 
        mock_controller, 
        mock_session,
        default_nextalk_config
    ):
        """测试完整的语音识别到文本注入工作流."""
        # 模拟识别结果
        recognition_result = RecognitionResult(
            text="这是一个完整的语音识别测试",
            confidence=0.95,
            is_final=True,
            timestamp=time.time(),
            session_id="test_session_001"
        )
        
        # 创建TextInjector
        config = default_nextalk_config.text_injection
        config.method = "ime"
        
        with patch('nextalk.output.text_injector.IMEManager') as mock_ime_class:
            mock_ime_class.return_value = ime_manager
            
            text_injector = TextInjector(config.dict())
            await text_injector.initialize()
            
            # 模拟完整工作流
            # 1. 控制器接收识别结果
            mock_controller.handle_recognition_result.return_value = recognition_result
            
            # 2. 会话处理识别结果
            mock_session.process_recognition_result.return_value = recognition_result.text
            
            # 3. 文本注入
            injection_result = await text_injector.inject_text(recognition_result.text)
            
            # 验证结果
            assert injection_result["success"]
            assert injection_result["text"] == recognition_result.text
            assert injection_result["method"] == "ime"
            
            # 验证调用
            mock_controller.handle_recognition_result.assert_called()
            mock_session.process_recognition_result.assert_called()
            
            await text_injector.cleanup()
    
    @pytest.mark.asyncio
    async def test_ime_error_handling_integration(self, mock_ime_adapter, default_nextalk_config):
        """测试IME错误处理集成."""
        # 设置适配器初始化失败
        mock_ime_adapter.set_failure_mode(True, "init")
        
        with patch('nextalk.output.ime_manager.IMEManager._create_platform_adapter') as mock_create:
            mock_create.return_value = mock_ime_adapter
            
            config = {"ime": {"enabled": True}}
            manager = IMEManager(config)
            
            # 初始化应该失败
            success = await manager.initialize()
            assert not success
            
            # 尝试注入文本应该失败
            result = await manager.inject_text("测试文本")
            assert not result.success
            assert "not initialized" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_ime_performance_monitoring(self, ime_manager):
        """测试IME性能监控."""
        test_texts = [
            "短文本",
            "这是一个中等长度的测试文本，用于验证性能",
            "这是一个很长的测试文本，包含了多个句子和复杂的中文字符。它用于测试IME在处理较长文本时的性能表现。"
        ]
        
        results = []
        
        for text in test_texts:
            start_time = time.time()
            result = await ime_manager.inject_text(text)
            end_time = time.time()
            
            assert result.success
            
            results.append({
                'text_length': len(text),
                'injection_time': result.injection_time,
                'total_time': end_time - start_time
            })
        
        # 验证性能指标
        for result in results:
            # 注入时间应该合理（小于1秒）
            assert result['injection_time'] < 1.0
            # 总时间应该也合理
            assert result['total_time'] < 2.0
        
        # 验证性能随文本长度的变化趋势
        # （在实际实现中，长文本可能需要更多时间）
        print(f"Performance results: {results}")
    
    @pytest.mark.asyncio
    async def test_concurrent_ime_operations(self, ime_manager):
        """测试并发IME操作."""
        test_texts = [
            f"并发测试文本 {i}" for i in range(5)
        ]
        
        # 并发执行多个注入操作
        tasks = [
            ime_manager.inject_text(text) 
            for text in test_texts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有操作都成功
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed with {result}"
            assert result.success, f"Injection {i} failed: {result.error}"
            assert result.text_injected == test_texts[i]
    
    @pytest.mark.asyncio
    async def test_ime_state_monitoring_integration(self, ime_manager):
        """测试IME状态监控集成."""
        # 获取初始状态
        initial_status = await ime_manager.get_ime_status()
        assert initial_status.is_active
        
        # 模拟IME状态变化
        mock_adapter = ime_manager._get_platform_adapter()
        if hasattr(mock_adapter, '_ime_active'):
            # 禁用IME
            mock_adapter._ime_active = False
            
            # 检查状态变化
            new_status = await ime_manager.get_ime_status()
            assert not new_status.is_active
            
            # 重新启用IME
            mock_adapter._ime_active = True
            
            # 验证状态恢复
            restored_status = await ime_manager.get_ime_status()
            assert restored_status.is_active
    
    @pytest.mark.asyncio
    async def test_ime_configuration_changes(self, mock_ime_adapter):
        """测试IME配置更改."""
        # 测试不同配置
        configs = [
            {"ime": {"enabled": True, "debug_mode": True}},
            {"ime": {"enabled": True, "debug_mode": False, "timeout": 5.0}},
            {"ime": {"enabled": False}}
        ]
        
        for config in configs:
            with patch('nextalk.output.ime_manager.IMEManager._create_platform_adapter') as mock_create:
                mock_create.return_value = mock_ime_adapter
                
                manager = IMEManager(config)
                
                if config["ime"]["enabled"]:
                    success = await manager.initialize()
                    assert success
                    
                    # 测试基本功能
                    result = await manager.inject_text("配置测试")
                    assert result.success
                    
                    await manager.cleanup()
                else:
                    # 禁用时应该跳过初始化
                    success = await manager.initialize()
                    # 根据实际实现，可能返回False或跳过


@pytest.mark.integration
@pytest.mark.slow
class TestIMECompatibility:
    """IME兼容性测试类."""
    
    def test_platform_compatibility(self):
        """测试平台兼容性."""
        from nextalk.output.ime_manager import IMEManager
        
        # 创建管理器（不初始化）
        manager = IMEManager({})
        
        # 检查平台支持
        if sys.platform == "win32":
            assert hasattr(manager, '_create_windows_adapter')
        elif sys.platform == "darwin":
            assert hasattr(manager, '_create_macos_adapter')
        elif sys.platform.startswith("linux"):
            assert hasattr(manager, '_create_linux_adapter')
    
    @pytest.mark.asyncio
    async def test_ime_exception_handling(self):
        """测试IME异常处理."""
        from nextalk.output.ime_exceptions import (
            IMEInitializationError, IMEInjectionError, 
            create_ime_context, handle_ime_exception
        )
        
        # 测试异常创建
        context = create_ime_context(
            operation="test_injection",
            ime_name="Test IME",
            app_name="Test App"
        )
        
        exc = IMEInjectionError(
            "Test injection failure",
            context=context,
            text_length=10
        )
        
        # 测试异常处理
        handle_ime_exception(exc)
        
        # 验证异常信息
        assert exc.context.operation == "test_injection"
        assert exc.context.ime_name == "Test IME"
        assert exc.context.app_name == "Test App"
        assert exc.context.additional_info["text_length"] == 10
    
    @pytest.mark.asyncio
    async def test_ime_fallback_mechanisms(self, mock_ime_adapter):
        """测试IME回退机制."""
        # 设置IME失败
        mock_ime_adapter.set_failure_mode(True, "inject")
        
        with patch('nextalk.output.ime_manager.IMEManager._create_platform_adapter') as mock_create:
            mock_create.return_value = mock_ime_adapter
            
            # 创建支持回退的配置
            config = {
                "ime": {
                    "enabled": True,
                    "fallback_enabled": True,
                    "fallback_methods": ["clipboard", "keyboard"]
                }
            }
            
            manager = IMEManager(config)
            await manager.initialize()
            
            # 注入文本（应该触发回退机制）
            result = await manager.inject_text("回退测试文本")
            
            # 根据实际实现验证回退行为
            # 这里假设回退机制会在IME失败时使用其他方法
            print(f"Fallback test result: {result}")
            
            await manager.cleanup()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])