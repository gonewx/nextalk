/// 识别文本后处理 (自动纠错)
///
/// ASR 模型的原始输出存在几类稳定可修的问题，这里在上屏前统一修正：
/// - Zipformer 双语模型输出全大写英文 ("HELLO WORLD")，与正常书写习惯不符
/// - 口头禅/填充词 ("嗯，" "呃" "um") 被原样识别
/// - 英文重复词 ("the the")、中文语境下的半角标点、重复标点、多余空格
/// - 专有名词/同音词识别错误 → 由用户在 settings.yaml 中配置替换词典
///
/// 纯函数、无 IO，便于单测；预览与最终上屏走同一个处理器，
/// 保证用户在胶囊中看到的就是最终上屏的内容。
class TextPostProcessor {
  const TextPostProcessor({
    this.enabled = true,
    this.normalizeCase = true,
    this.removeFillers = true,
    this.removeRepeatedWords = true,
    this.normalizePunctuation = true,
    this.cjkSpacing = false,
    this.stripTrailingPeriod = false,
    this.replacements = const {},
  });

  /// 总开关
  final bool enabled;

  /// 全大写英文 → 小写 (保留 "I" / "I'm" 等)
  final bool normalizeCase;

  /// 移除独立出现的填充词
  final bool removeFillers;

  /// 合并连续重复的英文单词
  final bool removeRepeatedWords;

  /// 中文语境下标点全角化、去重复标点、清理多余空格
  final bool normalizePunctuation;

  /// 中英文/数字之间自动加空格
  final bool cjkSpacing;

  /// 去掉末尾的句号 (适合在句子中间插入片段)
  final bool stripTrailingPeriod;

  /// 用户自定义替换词典 (错误写法 → 正确写法)
  ///
  /// 英文按单词边界、忽略大小写匹配；中文按字面匹配。长词优先。
  final Map<String, String> replacements;

  /// 不做任何处理的实例
  static const TextPostProcessor disabled = TextPostProcessor(enabled: false);

  /// 从 settings.yaml 的 `text:` 节解析配置；缺省项使用默认值
  factory TextPostProcessor.fromConfig(Map<String, dynamic>? config) {
    if (config == null) return const TextPostProcessor();

    bool flag(String key, bool fallback) {
      final value = config[key];
      return value is bool ? value : fallback;
    }

    final replacements = <String, String>{};
    final raw = config['replacements'];
    if (raw is Map) {
      raw.forEach((key, value) {
        final from = key?.toString() ?? '';
        if (from.trim().isEmpty || value == null) return;
        replacements[from] = value.toString();
      });
    }

    return TextPostProcessor(
      enabled: flag('auto_correct', true),
      normalizeCase: flag('normalize_case', true),
      removeFillers: flag('remove_fillers', true),
      removeRepeatedWords: flag('remove_repeated_words', true),
      normalizePunctuation: flag('normalize_punctuation', true),
      cjkSpacing: flag('cjk_spacing', false),
      stripTrailingPeriod: flag('strip_trailing_period', false),
      replacements: replacements,
    );
  }

  // ===== 正则 (静态编译一次) =====

  static const String _cjk = r'㐀-䶿一-鿿豈-﫿';
  static final RegExp _hasCjk = RegExp('[$_cjk]');
  static final RegExp _hasLower = RegExp(r'[a-z]');
  static final RegExp _upperWord = RegExp(r"[A-Z][A-Z']*");
  static final RegExp _multiSpace = RegExp(r'[ \t　]{2,}');
  static final RegExp _spaceBeforePunct = RegExp(r'\s+([，。！？、；：,.!?;:])');
  static final RegExp _repeatedWord =
      RegExp(r"\b([A-Za-z][A-Za-z']*)(?:\s+\1\b)+", caseSensitive: false);
  static final RegExp _cjkThenLatin = RegExp('([$_cjk])([A-Za-z0-9])');
  static final RegExp _latinThenCjk = RegExp('([A-Za-z0-9])([$_cjk])');

  /// 中文填充词：只在句首或标点之后独立出现时移除，
  /// 避免误伤 "嗯嗯好的" 之外的正常用字 (如 "额外"、"额度")
  static final RegExp _cjkFiller = RegExp(
      r'(^|[，。！？、；：,.!?;:\s])(?:嗯+|呃+|唔+|额(?=[，,。\s]|$))[，,、。\s]*');

  /// 英文填充词：独立单词
  static final RegExp _enFiller =
      RegExp(r'\b(?:u+h+|u+m+|e+r+m+|h+m+)\b[,\s]*', caseSensitive: false);

  static const Map<String, String> _fullWidth = {
    ',': '，',
    '?': '？',
    '!': '！',
    ';': '；',
    ':': '：',
  };
  static final RegExp _duplicatePunct = RegExp(r'([，。！？、；：])\1+');
  static final RegExp _trailingPeriod = RegExp(r'[。.]+$');

  /// 处理一段识别文本
  String process(String input) {
    if (!enabled || input.isEmpty) return input;

    var text = input.trim();
    if (text.isEmpty) return text;

    if (normalizeCase) text = _normalizeCase(text);
    if (removeFillers) text = _removeFillers(text);
    if (removeRepeatedWords) {
      text = text.replaceAllMapped(_repeatedWord, (m) => m.group(1)!);
    }
    if (replacements.isNotEmpty) text = _applyReplacements(text);
    if (normalizePunctuation) text = _normalizePunctuation(text);
    if (cjkSpacing) text = _addCjkSpacing(text);
    if (stripTrailingPeriod) text = text.replaceFirst(_trailingPeriod, '');

    text = text.replaceAll(_multiSpace, ' ').trim();
    // 整段都被当成填充词删光 (如用户就只说了 "嗯")：保留原文，不吞输入
    return text.isEmpty ? input.trim() : text;
  }

  /// 仅当整段英文都是大写时才转换 (模型风格)，SenseVoice 等已有正常
  /// 大小写的输出不受影响
  String _normalizeCase(String text) {
    if (_hasLower.hasMatch(text) || !_upperWord.hasMatch(text)) return text;
    return text.replaceAllMapped(_upperWord, (m) {
      final word = m.group(0)!;
      if (word == 'I') return word;
      if (word.startsWith("I'")) return "I'${word.substring(2).toLowerCase()}";
      return word.toLowerCase();
    });
  }

  String _removeFillers(String text) {
    var result = text.replaceAllMapped(_cjkFiller, (m) => m.group(1)!);
    result = result.replaceAll(_enFiller, '');
    return result.trim();
  }

  String _applyReplacements(String text) {
    // 长词优先，避免短词先替换破坏长词
    final keys = replacements.keys.toList()
      ..sort((a, b) => b.length.compareTo(a.length));
    var result = text;
    for (final from in keys) {
      final to = replacements[from]!;
      final isLatin = !_hasCjk.hasMatch(from);
      final pattern = isLatin
          ? RegExp('(?<![A-Za-z0-9])${RegExp.escape(from)}(?![A-Za-z0-9])',
              caseSensitive: false)
          : RegExp(RegExp.escape(from));
      result = result.replaceAll(pattern, to);
    }
    return result;
  }

  String _normalizePunctuation(String text) {
    var result = text.replaceAllMapped(_spaceBeforePunct, (m) => m.group(1)!);

    // 半角标点仅在紧邻中文时全角化，保留 "3.14"、"e.g." 等英文语境
    if (_hasCjk.hasMatch(result)) {
      final buffer = StringBuffer();
      final chars = result.split('');
      for (var i = 0; i < chars.length; i++) {
        final c = chars[i];
        final full = _fullWidth[c];
        if (full != null) {
          final prevCjk = i > 0 && _hasCjk.hasMatch(chars[i - 1]);
          var next = i + 1;
          while (next < chars.length && chars[next] == ' ') {
            next++;
          }
          final nextCjk =
              next < chars.length && _hasCjk.hasMatch(chars[next]);
          if (prevCjk || nextCjk) {
            buffer.write(full);
            // 全角标点自带间距，吞掉其后的空格
            while (i + 1 < chars.length && chars[i + 1] == ' ') {
              i++;
            }
            continue;
          }
        }
        buffer.write(c);
      }
      result = buffer.toString();
    }

    return result.replaceAllMapped(_duplicatePunct, (m) => m.group(1)!);
  }

  String _addCjkSpacing(String text) {
    return text
        .replaceAllMapped(_cjkThenLatin, (m) => '${m.group(1)} ${m.group(2)}')
        .replaceAllMapped(_latinThenCjk, (m) => '${m.group(1)} ${m.group(2)}');
  }
}
