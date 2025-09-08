"""
Text processor module for IME optimization.

Optimizes text processing for different types of input through IME frameworks.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from .ime_base import IMEInfo, IMEFramework


logger = logging.getLogger(__name__)


class TextType(Enum):
    """Types of text for processing optimization."""
    PURE_CHINESE = "pure_chinese"
    PURE_ENGLISH = "pure_english"
    MIXED_CHINESE_ENGLISH = "mixed_chinese_english"
    NUMERIC = "numeric"
    PUNCTUATION_HEAVY = "punctuation_heavy"
    UNKNOWN = "unknown"


@dataclass
class ProcessedText:
    """Result of text processing."""
    original: str
    processed: str
    text_type: TextType
    segments: List[Tuple[str, str]]  # (text_segment, segment_type)
    ime_hints: Dict[str, Any]  # Hints for IME processing


class TextProcessor:
    """
    Text processor for IME optimization.
    
    Handles preprocessing and optimization of different text types
    for better IME input experience.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize text processor.
        
        Args:
            config: Text processing configuration
        """
        self.config = config or {}
        
        # Text processing options
        self.format_text = self.config.get('format_text', True)
        self.strip_whitespace = self.config.get('strip_whitespace', True)
        self.normalize_punctuation = self.config.get('normalize_punctuation', True)
        self.segment_mixed_text = self.config.get('segment_mixed_text', True)
        
        # CJK character patterns
        self._cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]+')
        self._english_pattern = re.compile(r'[a-zA-Z]+')
        self._numeric_pattern = re.compile(r'\d+')
        
        # Punctuation mapping for Chinese IME
        self._chinese_punctuation_map = {
            '.': '。',
            ',': '，',
            '!': '！',
            '?': '？',
            ':': '：',
            ';': '；',
            '(': '（',
            ')': '）',
            '[': '【',
            ']': '】',
            '"': '"',  # Opening quote
            '"': '"',  # Closing quote - context dependent
        }
    
    def preprocess_for_ime(self, text: str, ime_info: Optional[IMEInfo] = None) -> ProcessedText:
        """
        Preprocess text for optimal IME input.
        
        Args:
            text: Original text to process
            ime_info: Information about the target IME
            
        Returns:
            ProcessedText with optimization results
        """
        if not text:
            return ProcessedText(
                original="",
                processed="",
                text_type=TextType.UNKNOWN,
                segments=[],
                ime_hints={}
            )
        
        original_text = text
        
        # Basic cleanup
        if self.strip_whitespace:
            text = text.strip()
        
        # Detect text type
        text_type = self._detect_text_type(text)
        
        # Segment text based on type
        segments = self._segment_text(text, text_type)
        
        # Apply type-specific processing
        processed_text = self._apply_type_processing(text, text_type, ime_info)
        
        # Generate IME hints
        ime_hints = self._generate_ime_hints(text, text_type, ime_info, segments)
        
        return ProcessedText(
            original=original_text,
            processed=processed_text,
            text_type=text_type,
            segments=segments,
            ime_hints=ime_hints
        )
    
    def handle_cjk_input(self, text: str) -> str:
        """
        Handle CJK (Chinese, Japanese, Korean) input optimization.
        
        Args:
            text: Text containing CJK characters
            
        Returns:
            Optimized text for CJK IME input
        """
        if not self._contains_cjk(text):
            return text
        
        processed_text = text
        
        # Normalize punctuation for Chinese input
        if self.normalize_punctuation:
            processed_text = self._normalize_chinese_punctuation(processed_text)
        
        # Handle spacing around CJK characters
        processed_text = self._optimize_cjk_spacing(processed_text)
        
        # Format text if requested
        if self.format_text:
            processed_text = self._format_cjk_text(processed_text)
        
        return processed_text
    
    def optimize_mixed_text(self, text: str) -> str:
        """
        Optimize mixed Chinese-English text for IME input.
        
        Args:
            text: Mixed language text
            
        Returns:
            Optimized text for mixed input
        """
        if not self._is_mixed_text(text):
            return text
        
        processed_text = text
        
        # Add appropriate spacing between Chinese and English
        processed_text = self._add_mixed_language_spacing(processed_text)
        
        # Handle punctuation context-sensitively
        processed_text = self._handle_mixed_punctuation(processed_text)
        
        return processed_text
    
    def _detect_text_type(self, text: str) -> TextType:
        """Detect the primary type of the input text."""
        cjk_chars = len(self._cjk_pattern.findall(text))
        english_chars = len(self._english_pattern.findall(text))
        numeric_chars = len(self._numeric_pattern.findall(text))
        
        total_chars = len(re.findall(r'\S', text))  # Non-whitespace characters
        
        if total_chars == 0:
            return TextType.UNKNOWN
        
        cjk_ratio = cjk_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        numeric_ratio = numeric_chars / total_chars if total_chars > 0 else 0
        
        # Determine primary type based on character distribution
        if cjk_ratio > 0.8:
            return TextType.PURE_CHINESE
        elif english_ratio > 0.8:
            return TextType.PURE_ENGLISH
        elif numeric_ratio > 0.6:
            return TextType.NUMERIC
        elif cjk_ratio > 0.3 and english_ratio > 0.3:
            return TextType.MIXED_CHINESE_ENGLISH
        elif len(re.findall(r'[^\w\s]', text)) / total_chars > 0.4:
            return TextType.PUNCTUATION_HEAVY
        else:
            return TextType.UNKNOWN
    
    def _segment_text(self, text: str, text_type: TextType) -> List[Tuple[str, str]]:
        """Segment text into logical parts for processing."""
        segments = []
        
        if text_type == TextType.MIXED_CHINESE_ENGLISH:
            # Segment mixed text by language boundaries
            parts = re.split(r'(\s+)', text)  # Preserve whitespace
            
            for part in parts:
                if not part:
                    continue
                elif part.isspace():
                    segments.append((part, 'whitespace'))
                elif self._contains_cjk(part):
                    segments.append((part, 'cjk'))
                elif self._english_pattern.match(part):
                    segments.append((part, 'english'))
                elif self._numeric_pattern.match(part):
                    segments.append((part, 'numeric'))
                else:
                    segments.append((part, 'punctuation'))
        else:
            # For other types, treat as single segment
            segments.append((text, text_type.value))
        
        return segments
    
    def _apply_type_processing(self, text: str, text_type: TextType, ime_info: Optional[IMEInfo]) -> str:
        """Apply type-specific text processing."""
        if text_type == TextType.PURE_CHINESE:
            return self.handle_cjk_input(text)
        elif text_type == TextType.MIXED_CHINESE_ENGLISH:
            return self.optimize_mixed_text(text)
        elif text_type in [TextType.PURE_ENGLISH, TextType.NUMERIC]:
            # For English and numeric text, minimal processing
            return self._format_basic_text(text)
        else:
            return text
    
    def _generate_ime_hints(self, text: str, text_type: TextType, 
                          ime_info: Optional[IMEInfo], segments: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Generate hints for IME processing."""
        hints = {
            'text_type': text_type.value,
            'segment_count': len(segments),
            'contains_cjk': self._contains_cjk(text),
            'requires_ime_switch': False,
            'preferred_input_mode': 'default'
        }
        
        # Add IME-specific hints
        if ime_info:
            if ime_info.framework == IMEFramework.IBUS:
                hints.update(self._generate_ibus_hints(text, text_type))
            elif ime_info.framework == IMEFramework.FCITX:
                hints.update(self._generate_fcitx_hints(text, text_type))
        
        # Determine if IME mode switching might be needed
        if text_type == TextType.MIXED_CHINESE_ENGLISH:
            hints['requires_ime_switch'] = True
            hints['switch_points'] = self._find_ime_switch_points(segments)
        
        return hints
    
    def _generate_ibus_hints(self, text: str, text_type: TextType) -> Dict[str, Any]:
        """Generate IBus-specific processing hints."""
        return {
            'ibus_engine_preference': 'pinyin' if self._contains_cjk(text) else 'english',
            'use_traditional': False  # Assume simplified Chinese
        }
    
    def _generate_fcitx_hints(self, text: str, text_type: TextType) -> Dict[str, Any]:
        """Generate Fcitx-specific processing hints."""
        return {
            'fcitx_mode': 'chinese' if self._contains_cjk(text) else 'english',
            'punctuation_mode': 'chinese' if text_type == TextType.PURE_CHINESE else 'english'
        }
    
    def _find_ime_switch_points(self, segments: List[Tuple[str, str]]) -> List[int]:
        """Find positions where IME mode switching might be beneficial."""
        switch_points = []
        
        for i, (segment, segment_type) in enumerate(segments):
            if i > 0:
                prev_type = segments[i-1][1]
                # Switch points between CJK and English
                if (prev_type == 'cjk' and segment_type == 'english') or \
                   (prev_type == 'english' and segment_type == 'cjk'):
                    switch_points.append(i)
        
        return switch_points
    
    def _contains_cjk(self, text: str) -> bool:
        """Check if text contains CJK characters."""
        return bool(self._cjk_pattern.search(text))
    
    def _is_mixed_text(self, text: str) -> bool:
        """Check if text contains both CJK and English characters."""
        has_cjk = bool(self._cjk_pattern.search(text))
        has_english = bool(self._english_pattern.search(text))
        return has_cjk and has_english
    
    def _normalize_chinese_punctuation(self, text: str) -> str:
        """Normalize punctuation for Chinese input."""
        result = text
        
        for english_punct, chinese_punct in self._chinese_punctuation_map.items():
            # Only replace if surrounded by Chinese characters or at boundaries
            pattern = f'(?<=[\\u4e00-\\u9fff]){re.escape(english_punct)}(?=[\\u4e00-\\u9fff])'
            result = re.sub(pattern, chinese_punct, result)
        
        return result
    
    def _optimize_cjk_spacing(self, text: str) -> str:
        """Optimize spacing around CJK characters."""
        # Remove unnecessary spaces between CJK characters
        text = re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)
        
        # Ensure proper spacing between CJK and English/numeric
        text = re.sub(r'(?<=[\u4e00-\u9fff])(?=[a-zA-Z0-9])', ' ', text)
        text = re.sub(r'(?<=[a-zA-Z0-9])(?=[\u4e00-\u9fff])', ' ', text)
        
        return text
    
    def _format_cjk_text(self, text: str) -> str:
        """Apply basic formatting to CJK text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure proper punctuation spacing
        punctuation = ['。', '，', '！', '？', '：', '；']
        for punct in punctuation:
            # Remove space before punctuation
            text = text.replace(f' {punct}', punct)
            # Ensure single space after punctuation if followed by text
            text = re.sub(f'{re.escape(punct)}(?=[\\u4e00-\\u9fff])', f'{punct} ', text)
        
        return text
    
    def _add_mixed_language_spacing(self, text: str) -> str:
        """Add appropriate spacing in mixed language text."""
        # Add space between Chinese and English if not present
        text = re.sub(r'(?<=[\u4e00-\u9fff])(?=[a-zA-Z])', ' ', text)
        text = re.sub(r'(?<=[a-zA-Z])(?=[\u4e00-\u9fff])', ' ', text)
        
        # Add space between Chinese and numbers
        text = re.sub(r'(?<=[\u4e00-\u9fff])(?=\d)', ' ', text)
        text = re.sub(r'(?<=\d)(?=[\u4e00-\u9fff])', ' ', text)
        
        return text
    
    def _handle_mixed_punctuation(self, text: str) -> str:
        """Handle punctuation in mixed language contexts."""
        # Use English punctuation when immediately following English text
        result = text
        
        for english_punct, chinese_punct in self._chinese_punctuation_map.items():
            # Keep English punctuation after English words
            pattern = f'(?<=[a-zA-Z]){re.escape(chinese_punct)}'
            result = re.sub(pattern, english_punct, result)
        
        return result
    
    def _format_basic_text(self, text: str) -> str:
        """Apply basic text formatting."""
        if not self.format_text:
            return text
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Fix common punctuation issues
        punctuation = ['.', '!', '?', ',', ';', ':']
        for punct in punctuation:
            # Remove multiple punctuation
            text = re.sub(f'{re.escape(punct)}+', punct, text)
            # Ensure single space after punctuation
            text = re.sub(f'{re.escape(punct)}(?=\\w)', f'{punct} ', text)
        
        return text