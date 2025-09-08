"""
文本处理器单元测试 - 确保文本处理逻辑的准确性。

测试中文、英文、混合文本的处理逻辑，验证CJK字符检测和优化功能。
"""

import pytest
import unittest
from typing import Dict, Any

from nextalk.output.text_processor import (
    TextProcessor, TextType, ProcessedText
)
from nextalk.output.ime_base import IMEInfo, IMEFramework


class TestTextProcessor(unittest.TestCase):
    """文本处理器测试类."""
    
    def setUp(self):
        """设置测试环境."""
        self.processor = TextProcessor()
        self.config_processor = TextProcessor({
            'format_text': True,
            'strip_whitespace': True,
            'normalize_punctuation': True,
            'segment_mixed_text': True
        })
    
    def test_text_type_detection(self):
        """测试文本类型检测."""
        # 纯中文
        chinese_text = "这是一个纯中文文本测试"
        result = self.processor.preprocess_for_ime(chinese_text)
        self.assertEqual(result.text_type, TextType.PURE_CHINESE)
        
        # 纯英文
        english_text = "This is a pure English text test"
        result = self.processor.preprocess_for_ime(english_text)
        self.assertEqual(result.text_type, TextType.PURE_ENGLISH)
        
        # 混合文本
        mixed_text = "这是mixed text测试"
        result = self.processor.preprocess_for_ime(mixed_text)
        self.assertEqual(result.text_type, TextType.MIXED_CHINESE_ENGLISH)
        
        # 数字文本
        numeric_text = "123456789 001 999"
        result = self.processor.preprocess_for_ime(numeric_text)
        self.assertEqual(result.text_type, TextType.NUMERIC)
        
        # 标点符号重的文本
        punct_text = "!!!! ???? ,,,, ;;;;"
        result = self.processor.preprocess_for_ime(punct_text)
        self.assertEqual(result.text_type, TextType.PUNCTUATION_HEAVY)
    
    def test_cjk_character_detection(self):
        """测试CJK字符检测."""
        # 中文字符
        self.assertTrue(self.processor._contains_cjk("你好"))
        self.assertTrue(self.processor._contains_cjk("测试中文"))
        self.assertTrue(self.processor._contains_cjk("Hello 世界"))
        
        # 日文字符
        self.assertTrue(self.processor._contains_cjk("こんにちは"))
        self.assertTrue(self.processor._contains_cjk("カタカナ"))
        
        # 韩文字符
        self.assertTrue(self.processor._contains_cjk("안녕하세요"))
        
        # 非CJK字符
        self.assertFalse(self.processor._contains_cjk("Hello World"))
        self.assertFalse(self.processor._contains_cjk("123456"))
        self.assertFalse(self.processor._contains_cjk("!@#$%"))
    
    def test_mixed_text_detection(self):
        """测试混合文本检测."""
        # 混合文本
        self.assertTrue(self.processor._is_mixed_text("Hello 世界"))
        self.assertTrue(self.processor._is_mixed_text("这是English text"))
        self.assertTrue(self.processor._is_mixed_text("中文ABC英文"))
        
        # 非混合文本
        self.assertFalse(self.processor._is_mixed_text("纯中文文本"))
        self.assertFalse(self.processor._is_mixed_text("Pure English text"))
        self.assertFalse(self.processor._is_mixed_text("123456"))
    
    def test_chinese_punctuation_normalization(self):
        """测试中文标点符号标准化."""
        # 测试标点符号转换
        test_cases = [
            ("你好,世界!", "你好，世界！"),
            ("这是什么?", "这是什么？"),
            ("测试:结果", "测试：结果"),
            ("说明;注释", "说明；注释"),
            ('他说"你好"', '他说"你好"'),
            ("括号(内容)", "括号（内容）"),
            ("方括号[内容]", "方括号【内容】")
        ]
        
        for input_text, expected in test_cases:
            result = self.processor._normalize_chinese_punctuation(input_text)
            self.assertEqual(result, expected, f"Failed for: {input_text}")
    
    def test_cjk_spacing_optimization(self):
        """测试CJK间距优化."""
        # 测试中文字符间多余空格移除
        text_with_spaces = "你 好 世 界"
        result = self.processor._optimize_cjk_spacing(text_with_spaces)
        self.assertEqual(result, "你好世界")
        
        # 测试中英文间空格添加
        mixed_no_space = "你好World测试"
        result = self.processor._optimize_cjk_spacing(mixed_no_space)
        self.assertEqual(result, "你好 World 测试")
        
        # 测试中文数字间空格添加
        chinese_number = "今年2024年测试"
        result = self.processor._optimize_cjk_spacing(chinese_number)
        self.assertEqual(result, "今年 2024 年测试")
    
    def test_mixed_language_spacing(self):
        """测试混合语言间距处理."""
        test_cases = [
            ("HelloWorld", "HelloWorld"),  # 纯英文不变
            ("你好world", "你好 world"),
            ("Hello世界", "Hello 世界"),
            ("测试123数字", "测试 123 数字"),
            ("year2024年份", "year 2024 年份")
        ]
        
        for input_text, expected in test_cases:
            result = self.processor._add_mixed_language_spacing(input_text)
            self.assertEqual(result, expected, f"Failed for: {input_text}")
    
    def test_text_segmentation(self):
        """测试文本分段."""
        mixed_text = "这是 English text 和 123 数字"
        segments = self.processor._segment_text(mixed_text, TextType.MIXED_CHINESE_ENGLISH)
        
        # 验证分段结果
        self.assertGreater(len(segments), 1)
        
        # 检查分段类型
        segment_types = [seg_type for _, seg_type in segments]
        self.assertIn('cjk', segment_types)
        self.assertIn('english', segment_types)
        self.assertIn('numeric', segment_types)
    
    def test_cjk_input_handling(self):
        """测试CJK输入处理."""
        chinese_text = "你好，世界！这是测试文本。"
        result = self.processor.handle_cjk_input(chinese_text)
        
        # 结果应该包含正确的中文标点
        self.assertIn("，", result)
        self.assertIn("！", result)
        self.assertIn("。", result)
        
        # 测试非CJK文本不受影响
        english_text = "Hello, World!"
        result = self.processor.handle_cjk_input(english_text)
        self.assertEqual(result, english_text)
    
    def test_mixed_text_optimization(self):
        """测试混合文本优化."""
        mixed_text = "这是mixed text和123数字"
        result = self.processor.optimize_mixed_text(mixed_text)
        
        # 应该添加适当的空格
        self.assertIn("mixed text", result)
        self.assertIn("和 123", result)
        
        # 测试非混合文本不受影响
        pure_chinese = "纯中文文本"
        result = self.processor.optimize_mixed_text(pure_chinese)
        self.assertEqual(result, pure_chinese)
    
    def test_ime_hints_generation(self):
        """测试IME提示生成."""
        # 创建测试IME信息
        ibus_ime = IMEInfo(
            name="IBus Pinyin",
            framework=IMEFramework.IBUS,
            language="zh-CN",
            is_active=True
        )
        
        # 测试纯中文文本
        chinese_text = "你好世界"
        result = self.processor.preprocess_for_ime(chinese_text, ibus_ime)
        
        hints = result.ime_hints
        self.assertEqual(hints['text_type'], TextType.PURE_CHINESE.value)
        self.assertTrue(hints['contains_cjk'])
        self.assertIn('ibus_engine_preference', hints)
        self.assertEqual(hints['ibus_engine_preference'], 'pinyin')
        
        # 测试混合文本
        mixed_text = "Hello 世界"
        result = self.processor.preprocess_for_ime(mixed_text, ibus_ime)
        
        hints = result.ime_hints
        self.assertEqual(hints['text_type'], TextType.MIXED_CHINESE_ENGLISH.value)
        self.assertTrue(hints['requires_ime_switch'])
        self.assertIn('switch_points', hints)
    
    def test_fcitx_hints_generation(self):
        """测试Fcitx提示生成."""
        fcitx_ime = IMEInfo(
            name="Fcitx Pinyin",
            framework=IMEFramework.FCITX,
            language="zh-CN",
            is_active=True
        )
        
        chinese_text = "测试文本"
        result = self.processor.preprocess_for_ime(chinese_text, fcitx_ime)
        
        hints = result.ime_hints
        self.assertIn('fcitx_mode', hints)
        self.assertEqual(hints['fcitx_mode'], 'chinese')
        self.assertIn('punctuation_mode', hints)
    
    def test_empty_text_handling(self):
        """测试空文本处理."""
        empty_texts = ["", "   ", None]
        
        for text in empty_texts:
            if text is None:
                continue
            result = self.processor.preprocess_for_ime(text)
            
            if not text or not text.strip():
                self.assertEqual(result.text_type, TextType.UNKNOWN)
                self.assertEqual(result.processed, "" if not text else "")
                self.assertEqual(len(result.segments), 0)
    
    def test_configuration_options(self):
        """测试配置选项影响."""
        test_text = "  你好,世界!  "
        
        # 测试默认配置
        default_processor = TextProcessor()
        result = default_processor.preprocess_for_ime(test_text)
        
        # 测试禁用格式化的配置
        no_format_processor = TextProcessor({
            'format_text': False,
            'strip_whitespace': False,
            'normalize_punctuation': False
        })
        result_no_format = no_format_processor.preprocess_for_ime(test_text)
        
        # 结果应该不同
        self.assertNotEqual(result.processed, result_no_format.processed)
    
    def test_punctuation_heavy_text(self):
        """测试标点符号重的文本处理."""
        punct_text = "!!!什么???...真的吗???"
        result = self.processor.preprocess_for_ime(punct_text)
        
        # 应该被识别为标点符号重的文本
        self.assertEqual(result.text_type, TextType.PUNCTUATION_HEAVY)
    
    def test_numeric_text_processing(self):
        """测试数字文本处理."""
        numeric_texts = [
            "123456789",
            "2024年10月15日",
            "价格: 999元",
            "电话 13800138000"
        ]
        
        for text in numeric_texts:
            result = self.processor.preprocess_for_ime(text)
            
            # 验证结果不为空
            self.assertIsNotNone(result.processed)
            self.assertGreater(len(result.segments), 0)
    
    def test_ime_switch_points_detection(self):
        """测试IME切换点检测."""
        segments = [
            ("这是", "cjk"),
            (" ", "whitespace"),
            ("English", "english"),
            (" ", "whitespace"),
            ("文本", "cjk"),
            ("123", "numeric"),
            ("测试", "cjk")
        ]
        
        switch_points = self.processor._find_ime_switch_points(segments)
        
        # 应该找到CJK和英文之间的切换点
        self.assertGreater(len(switch_points), 0)
    
    def test_complex_mixed_text(self):
        """测试复杂混合文本处理."""
        complex_text = "使用Python 3.9开发Web应用，支持REST API和WebSocket连接"
        result = self.processor.preprocess_for_ime(complex_text)
        
        self.assertEqual(result.text_type, TextType.MIXED_CHINESE_ENGLISH)
        self.assertGreater(len(result.segments), 5)
        self.assertTrue(result.ime_hints['contains_cjk'])
        self.assertTrue(result.ime_hints['requires_ime_switch'])
    
    def test_cjk_text_formatting(self):
        """测试CJK文本格式化."""
        messy_text = "你好   ，    世界   ！   测试    。"
        result = self.processor._format_cjk_text(messy_text)
        
        # 应该清理多余空格并正确格式化标点
        self.assertNotIn("   ", result)  # 不应该有多个连续空格
        self.assertIn("你好，", result)
        self.assertIn("世界！", result)
    
    def test_basic_text_formatting(self):
        """测试基本文本格式化."""
        messy_english = "Hello   ,,,   world  !!!  How   are you???"
        result = self.processor._format_basic_text(messy_english)
        
        # 应该清理重复标点和多余空格
        self.assertNotIn(",,,", result)
        self.assertNotIn("!!!", result)
        self.assertNotIn("???", result)
        self.assertNotIn("   ", result)
    
    def test_performance_with_long_text(self):
        """测试长文本处理性能."""
        import time
        
        # 生成较长的测试文本
        long_text = "这是一个很长的文本测试。" * 100 + "This is English text. " * 100
        
        start_time = time.time()
        result = self.processor.preprocess_for_ime(long_text)
        end_time = time.time()
        
        # 处理时间应该合理（小于1秒）
        processing_time = end_time - start_time
        self.assertLess(processing_time, 1.0, f"Processing took too long: {processing_time}s")
        
        # 结果应该正确
        self.assertIsNotNone(result.processed)
        self.assertEqual(result.text_type, TextType.MIXED_CHINESE_ENGLISH)


class TestTextProcessorEdgeCases(unittest.TestCase):
    """文本处理器边界情况测试."""
    
    def setUp(self):
        self.processor = TextProcessor()
    
    def test_single_character_texts(self):
        """测试单字符文本处理."""
        single_chars = ["你", "A", "1", "!", "？", "。"]
        
        for char in single_chars:
            result = self.processor.preprocess_for_ime(char)
            self.assertIsNotNone(result.processed)
            self.assertEqual(len(result.segments), 1)
    
    def test_special_characters(self):
        """测试特殊字符处理."""
        special_texts = [
            "🎉 庆祝 🎊",
            "测试@email.com地址",
            "网址https://www.test.com测试",
            "标签#测试#内容"
        ]
        
        for text in special_texts:
            result = self.processor.preprocess_for_ime(text)
            self.assertIsNotNone(result.processed)
            # 特殊字符应该被保留
            self.assertIn(result.original, text)
    
    def test_whitespace_only_text(self):
        """测试仅包含空白字符的文本."""
        whitespace_texts = ["   ", "\t\t", "\n\n", " \t \n "]
        
        for text in whitespace_texts:
            result = self.processor.preprocess_for_ime(text)
            # 处理后应该是空字符串
            self.assertEqual(result.processed.strip(), "")
    
    def test_all_punctuation_text(self):
        """测试全标点符号文本."""
        punct_text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = self.processor.preprocess_for_ime(punct_text)
        
        self.assertEqual(result.text_type, TextType.PUNCTUATION_HEAVY)
        self.assertIsNotNone(result.processed)
    
    def test_repeated_characters(self):
        """测试重复字符处理."""
        repeated_texts = [
            "哈哈哈哈哈哈哈哈哈哈",
            "aaaaaaaaaaa",
            "1111111111",
            "!!!!!!!!!!!"
        ]
        
        for text in repeated_texts:
            result = self.processor.preprocess_for_ime(text)
            self.assertIsNotNone(result.processed)
            # 原始文本应该被保留
            self.assertTrue(len(result.processed) > 0)


class TestTextProcessorIntegration(unittest.TestCase):
    """文本处理器集成测试."""
    
    def test_realistic_voice_recognition_results(self):
        """测试真实语音识别结果处理."""
        # 模拟真实的语音识别结果
        realistic_texts = [
            "今天天气很好，我想出去走走",
            "请帮我打开Chrome浏览器",
            "发送邮件给张三，内容是明天开会时间改为上午10点",
            "搜索Python教程，找到最新的学习资料",
            "播放音乐，我想听周杰伦的歌曲",
            "设置闹钟，明天早上7点30分叫醒我"
        ]
        
        processor = TextProcessor({
            'format_text': True,
            'normalize_punctuation': True,
            'segment_mixed_text': True
        })
        
        for text in realistic_texts:
            result = processor.preprocess_for_ime(text)
            
            # 所有结果都应该成功处理
            self.assertIsNotNone(result.processed)
            self.assertGreater(len(result.processed), 0)
            self.assertNotEqual(result.text_type, TextType.UNKNOWN)
            
            # 检查基本质量
            self.assertFalse("  " in result.processed)  # 不应该有多余空格
            
            print(f"Original: {text}")
            print(f"Processed: {result.processed}")
            print(f"Type: {result.text_type}")
            print(f"Segments: {len(result.segments)}")
            print("---")


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)