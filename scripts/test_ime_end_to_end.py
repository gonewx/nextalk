#!/usr/bin/env python3
"""
IME端到端功能验证脚本
运行完整的IME文本注入功能验证，包括：
1. IME管理器初始化
2. 文本处理器功能
3. 文本注入功能
4. 错误处理机制
5. 性能验证
"""

import asyncio
import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nextalk.config.models import IMEConfig
from nextalk.output.ime_manager import IMEManager, IMEManagerState
from nextalk.output.text_processor import TextProcessor
from nextalk.output.text_injector import TextInjector
from nextalk.output.ime_exceptions import IMEException


# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IMEEndToEndValidator:
    """IME端到端功能验证器"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.ime_manager: Optional[IMEManager] = None
        self.text_processor: Optional[TextProcessor] = None
        self.text_injector: Optional[TextInjector] = None
    
    def log_test_result(self, test_name: str, success: bool, details: str = "", duration: float = 0.0):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "duration": duration,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {details} ({duration:.3f}s)")
    
    async def test_ime_manager_initialization(self) -> bool:
        """测试IME管理器初始化"""
        test_name = "IME Manager Initialization"
        start_time = time.time()
        
        try:
            # 创建IME配置
            ime_config = IMEConfig(
                enabled=True,
                debug_mode=True,
                fallback_timeout=5.0,
                composition_timeout=1.0,
                auto_detect_ime=True
            )
            
            # 创建IME管理器
            self.ime_manager = IMEManager(ime_config)
            
            # 初始化
            success = await self.ime_manager.initialize()
            
            if success and self.ime_manager.is_ready():
                # 获取状态
                status = self.ime_manager.get_manager_status()
                details = f"State: {status.state.value}, Platform: {status.platform}"
                self.log_test_result(test_name, True, details, time.time() - start_time)
                return True
            else:
                self.log_test_result(test_name, False, "Initialization failed", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}", time.time() - start_time)
            return False
    
    async def test_text_processor_functionality(self) -> bool:
        """测试文本处理器功能"""
        test_name = "Text Processor Functionality"
        start_time = time.time()
        
        try:
            # 创建文本处理器
            processor_config = {
                "normalize_whitespace": True,
                "remove_duplicates": True,
                "min_length": 1
            }
            
            self.text_processor = TextProcessor(processor_config)
            
            # 测试文本处理
            test_texts = [
                "这是一个测试文本",
                "  带有多余空格的文本  ",
                "重复重复的文本",
                "",  # 空文本
                "混合Chinese and English文本"
            ]
            
            processed_count = 0
            for text in test_texts:
                processed = self.text_processor.preprocess_for_ime(text)
                if processed.is_valid:
                    processed_count += 1
            
            success = processed_count > 0
            details = f"Processed {processed_count}/{len(test_texts)} texts successfully"
            self.log_test_result(test_name, success, details, time.time() - start_time)
            return success
            
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}", time.time() - start_time)
            return False
    
    async def test_text_injection_functionality(self) -> bool:
        """测试文本注入功能"""
        test_name = "Text Injection Functionality"
        start_time = time.time()
        
        try:
            if not self.ime_manager or not self.ime_manager.is_ready():
                self.log_test_result(test_name, False, "IME Manager not ready", time.time() - start_time)
                return False
            
            # 测试基本文本注入
            test_text = "端到端功能验证测试文本"
            result = await self.ime_manager.inject_text(test_text)
            
            if result.success:
                details = f"Injected '{test_text}' using {result.ime_used} in {result.injection_time:.3f}s"
                self.log_test_result(test_name, True, details, time.time() - start_time)
                return True
            else:
                details = f"Injection failed: {result.error}"
                self.log_test_result(test_name, False, details, time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}", time.time() - start_time)
            return False
    
    async def test_error_handling(self) -> bool:
        """测试错误处理机制"""
        test_name = "Error Handling"
        start_time = time.time()
        
        try:
            if not self.ime_manager:
                self.log_test_result(test_name, False, "IME Manager not available", time.time() - start_time)
                return False
            
            # 测试空文本注入
            result = await self.ime_manager.inject_text("")
            
            # 根据实现，空文本可能成功（无操作）或失败
            # 重要的是不应该崩溃
            details = f"Empty text injection handled: success={result.success}"
            self.log_test_result(test_name, True, details, time.time() - start_time)
            return True
            
        except Exception as e:
            # 如果抛出适当的异常，这也是正确的错误处理
            if isinstance(e, IMEException):
                details = f"Proper IME exception raised: {e}"
                self.log_test_result(test_name, True, details, time.time() - start_time)
                return True
            else:
                self.log_test_result(test_name, False, f"Unexpected exception: {e}", time.time() - start_time)
                return False
    
    async def test_performance_benchmarks(self) -> bool:
        """测试性能基准"""
        test_name = "Performance Benchmarks"
        start_time = time.time()
        
        try:
            if not self.ime_manager or not self.ime_manager.is_ready():
                self.log_test_result(test_name, False, "IME Manager not ready", time.time() - start_time)
                return False
            
            # 性能测试文本
            test_texts = [
                "短",
                "中等长度的测试文本",
                "这是一个相对较长的测试文本，用于验证IME在处理较长文本时的性能表现，包含了多个中文字符和句子结构。"
            ]
            
            total_chars = 0
            total_time = 0.0
            successful_injections = 0
            
            for text in test_texts:
                text_start = time.time()
                result = await self.ime_manager.inject_text(text)
                text_duration = time.time() - text_start
                
                if result.success:
                    total_chars += len(text)
                    total_time += text_duration
                    successful_injections += 1
            
            if successful_injections > 0:
                avg_speed = total_chars / total_time if total_time > 0 else 0
                details = f"{successful_injections} injections, {avg_speed:.1f} chars/sec avg"
                
                # 性能阈值：至少100字符/秒
                success = avg_speed >= 100
                self.log_test_result(test_name, success, details, time.time() - start_time)
                return success
            else:
                self.log_test_result(test_name, False, "No successful injections", time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}", time.time() - start_time)
            return False
    
    async def test_text_injector_integration(self) -> bool:
        """测试TextInjector集成"""
        test_name = "TextInjector Integration"
        start_time = time.time()
        
        try:
            # 导入TextInjectionConfig
            from nextalk.config.models import TextInjectionConfig
            
            # 创建TextInjector配置
            config = TextInjectionConfig(
                use_ime=True,
                fallback_method="clipboard",
                timeout=5.0,
                retry_attempts=3
            )
            
            self.text_injector = TextInjector(config)
            await self.text_injector.initialize()
            
            # 测试通过TextInjector注入文本
            test_text = "通过TextInjector注入的测试文本"
            result = await self.text_injector.inject_text(test_text)
            
            if result.get("success", False):
                details = f"Method: {result.get('method')}, Text: '{result.get('text')}'"
                self.log_test_result(test_name, True, details, time.time() - start_time)
                return True
            else:
                details = f"Injection failed: {result.get('error', 'Unknown error')}"
                self.log_test_result(test_name, False, details, time.time() - start_time)
                return False
                
        except Exception as e:
            self.log_test_result(test_name, False, f"Exception: {e}", time.time() - start_time)
            return False
        finally:
            if self.text_injector:
                await self.text_injector.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.ime_manager:
                await self.ime_manager.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def generate_report(self) -> str:
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        report = [
            "=" * 60,
            "IME端到端功能验证报告",
            "=" * 60,
            f"总测试数: {total_tests}",
            f"通过: {passed_tests}",
            f"失败: {failed_tests}",
            f"成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            "",
            "详细结果:",
            "-" * 40
        ]
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            report.append(f"{status} {result['test_name']}")
            report.append(f"   {result['details']}")
            report.append(f"   耗时: {result['duration']:.3f}秒")
            report.append("")
        
        return "\n".join(report)


async def main():
    """主函数"""
    logger.info("开始IME端到端功能验证...")
    
    validator = IMEEndToEndValidator()
    
    try:
        # 执行所有测试
        tests = [
            validator.test_ime_manager_initialization,
            validator.test_text_processor_functionality,
            validator.test_text_injection_functionality,
            validator.test_error_handling,
            validator.test_performance_benchmarks,
            validator.test_text_injector_integration
        ]
        
        for test in tests:
            await test()
            # 短暂延迟，避免测试之间的干扰
            await asyncio.sleep(0.1)
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出现异常: {e}")
    finally:
        await validator.cleanup()
    
    # 生成并显示报告
    report = validator.generate_report()
    print(report)
    
    # 返回exit code
    passed_tests = sum(1 for r in validator.test_results if r["success"])
    total_tests = len(validator.test_results)
    
    if passed_tests == total_tests and total_tests > 0:
        logger.info("所有测试通过！IME功能验证成功。")
        return 0
    else:
        logger.error(f"部分测试失败 ({passed_tests}/{total_tests} 通过)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)