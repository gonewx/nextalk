import 'dart:io';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Story 3-8: 语言服务 - 管理应用国际化
///
/// 功能:
/// - 检测系统语言并自动设置
/// - 支持热切换语言 (无需重启)
/// - 持久化语言偏好
/// - 提供无 Context 的翻译方法 (用于托盘/通知)
class LanguageService {
  LanguageService._();

  static final LanguageService instance = LanguageService._();

  static const String _keyLanguageCode = 'language_code';

  SharedPreferences? _prefs;
  bool _isInitialized = false;

  /// 当前语言 Locale 通知器 (用于 MaterialApp 响应语言变化)
  final ValueNotifier<Locale> localeNotifier = ValueNotifier(const Locale('zh'));

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  /// 当前语言代码
  String get languageCode => localeNotifier.value.languageCode;

  /// 当前是否为中文
  bool get isZh => languageCode == 'zh';

  /// 初始化语言服务
  /// AC1: 首次启动检测系统语言
  /// AC4: 应用重启使用上次选择的语言
  Future<void> initialize() async {
    if (_isInitialized) return;

    _prefs = await SharedPreferences.getInstance();

    // 优先读取持久化的语言设置 (AC4)
    final savedCode = _prefs!.getString(_keyLanguageCode);
    if (savedCode != null) {
      localeNotifier.value = Locale(savedCode);
      debugPrint('LanguageService: 使用已保存的语言: $savedCode');
    } else {
      // 首次运行，检测系统语言 (AC1)
      final detected = _detectSystemLocale();
      localeNotifier.value = detected;
      debugPrint('LanguageService: 检测系统语言: ${detected.languageCode}');
    }

    _isInitialized = true;
  }

  /// 检测系统语言
  /// AC1: zh_CN → 中文, en_* → 英文, 其他 → 中文 (默认)
  Locale _detectSystemLocale() {
    try {
      final locale = Platform.localeName; // 例如 "zh_CN.UTF-8" 或 "en_US.UTF-8"
      debugPrint('LanguageService: 系统 localeName: $locale');

      if (locale.startsWith('zh')) {
        return const Locale('zh');
      } else if (locale.startsWith('en')) {
        return const Locale('en');
      }
    } catch (e) {
      debugPrint('LanguageService: 检测系统语言失败: $e');
    }

    // 默认回退到中文 (AC1)
    return const Locale('zh');
  }

  /// 切换语言
  /// AC3: 立即更新所有 UI 文本 (热切换)
  /// AC3: 语言偏好持久化到配置文件
  Future<void> switchLanguage(String languageCode) async {
    if (languageCode != 'zh' && languageCode != 'en') {
      debugPrint('LanguageService: 不支持的语言代码: $languageCode');
      return;
    }

    if (languageCode == localeNotifier.value.languageCode) {
      return; // 没有变化
    }

    // 更新 ValueNotifier，触发 UI 重建 (AC3)
    localeNotifier.value = Locale(languageCode);

    // 持久化到 SharedPreferences (AC3)
    await _prefs?.setString(_keyLanguageCode, languageCode);

    debugPrint('LanguageService: 语言已切换为 $languageCode');
  }

  /// 无 Context 翻译方法 (托盘/通知使用)
  /// AC5, AC6, AC10: 托盘菜单和通知使用对应语言
  ///
  /// 使用内置简化翻译映射，覆盖服务层需要的字符串
  String tr(String key) {
    final code = localeNotifier.value.languageCode;
    return _translations[code]?[key] ?? key;
  }

  /// 带参数替换的翻译方法 (Story 2-7: AC6)
  /// [key] 翻译键
  /// [params] 参数映射，例如 {'engine': 'SenseVoice'}
  String trWithParams(String key, Map<String, String> params) {
    String result = tr(key);
    params.forEach((paramKey, value) {
      result = result.replaceAll('{$paramKey}', value);
    });
    return result;
  }

  /// 内置翻译映射 (服务层使用)
  /// 包含托盘菜单、通知等无法获取 BuildContext 的字符串
  static const Map<String, Map<String, String>> _translations = {
    'zh': {
      // 托盘菜单 (AC5)
      'tray_show_hide': '显示 / 隐藏',
      'tray_reconnect': '重新连接 Fcitx5',
      'tray_model_int8': 'int8 模型 (更快)',
      'tray_model_standard': '标准模型 (更准)',
      'tray_settings': '设置',
      'tray_language': '语言 / Language',
      'tray_exit': '退出',
      'tray_model_switch_notice': '模型已切换，重启应用后生效',
      // Story 2-7: 引擎切换 (AC6)
      'tray_asr_engine': 'ASR 引擎',
      'tray_engine_zipformer': 'Zipformer (流式)',
      'tray_engine_sensevoice': 'SenseVoice (离线)',
      'tray_engine_switching': '切换中...',
      'tray_engine_switch_success': '引擎已切换为 {engine}',
      'tray_engine_switch_fallback': '切换失败，已回退到 {engine}',
      'tray_engine_actual': '当前使用',
      'tray_model_not_found': '{engine} 模型未下载，请先下载模型',
      'tray_model_settings': '模型设置',
      // Story 3-9: 音频设备 (AC19)
      'tray_audio_device': '音频输入设备',
      'tray_audio_default': '系统默认',
      'tray_audio_restart_notice': '音频设备已更改，重启应用后生效',
      'audio_error_title': '音频设备不可用',
      'audio_error_device': '设备:',
      'audio_error_reason': '原因:',
      'audio_error_solution_title': '解决方法:',
      'audio_error_solution_1': '使用托盘菜单切换到其他音频设备',
      'audio_error_solution_2': '或执行 nextalk audio 命令配置设备',
      'audio_error_ok': '知道了',

      // 错误消息 (AC7)
      'error_fcitx_not_connected': 'Fcitx5 未连接',
      'error_mic_unavailable': '麦克风不可用',
      'error_mic_no_device': '未检测到麦克风',
      'error_mic_busy': '麦克风被其他应用占用',
      'error_mic_permission': '麦克风权限不足',
      'error_mic_lost': '麦克风已断开',
      'error_mic_init': '音频设备初始化失败',
      'error_model_not_found': '未找到语音模型',
      'error_model_incomplete': '模型文件不完整',
      'error_model_corrupted': '模型文件损坏',
      'error_model_load': '模型加载失败',
      'error_fcitx_not_running': 'Fcitx5 未运行，请先启动输入法',
      'error_fcitx_connect': 'Fcitx5 连接失败',
      'error_fcitx_timeout': 'Fcitx5 连接超时',
      'error_fcitx_send': '文本发送失败',
      'error_fcitx_msg_large': '消息过大',
      'error_fcitx_reconnect': 'Fcitx5 重连失败，请检查服务状态',
      'error_fcitx_perm': 'Socket 权限不安全',
      'error_fcitx_general': 'Fcitx5 连接错误',
      'error_unknown': '未知错误',

      // 通知 (AC10)
      'notify_model_switched': '模型已切换',
      'notify_copied': '已复制到剪贴板',
      'notify_link_copied': '链接已复制到剪贴板',
      'notify_text_copied': '文本已复制到剪贴板',
      'clipboard_paste_hint': '已复制到剪贴板，请粘贴',

      // 通用
      'listening': '正在聆听...',
      'app_name': 'Nextalk',
      'copy': '复制',
    },
    'en': {
      // 托盘菜单 (AC6)
      'tray_show_hide': 'Show / Hide',
      'tray_reconnect': 'Reconnect Fcitx5',
      'tray_model_int8': 'int8 Model (Faster)',
      'tray_model_standard': 'Standard Model (More Accurate)',
      'tray_settings': 'Settings',
      'tray_language': '语言 / Language',
      'tray_exit': 'Exit',
      'tray_model_switch_notice': 'Model switched, restart app to take effect',
      // Story 2-7: 引擎切换 (AC6)
      'tray_asr_engine': 'ASR Engine',
      'tray_engine_zipformer': 'Zipformer (Streaming)',
      'tray_engine_sensevoice': 'SenseVoice (Offline)',
      'tray_engine_switching': 'Switching...',
      'tray_engine_switch_success': 'Engine switched to {engine}',
      'tray_engine_switch_fallback': 'Switch failed, fallback to {engine}',
      'tray_engine_actual': 'In Use',
      'tray_model_not_found': '{engine} model not downloaded, please download first',
      'tray_model_settings': 'Model Settings',
      // Story 3-9: 音频设备 (AC19)
      'tray_audio_device': 'Audio Input Device',
      'tray_audio_default': 'System Default',
      'tray_audio_restart_notice': 'Audio device changed, restart app to take effect',
      'audio_error_title': 'Audio Device Unavailable',
      'audio_error_device': 'Device:',
      'audio_error_reason': 'Reason:',
      'audio_error_solution_title': 'Solutions:',
      'audio_error_solution_1': 'Use tray menu to switch to another audio device',
      'audio_error_solution_2': 'Or run nextalk audio command to configure device',
      'audio_error_ok': 'OK',

      // 错误消息 (AC8)
      'error_fcitx_not_connected': 'Fcitx5 Not Connected',
      'error_mic_unavailable': 'Microphone Unavailable',
      'error_mic_no_device': 'Microphone Not Detected',
      'error_mic_busy': 'Microphone In Use by Another App',
      'error_mic_permission': 'Microphone Permission Denied',
      'error_mic_lost': 'Microphone Disconnected',
      'error_mic_init': 'Audio Device Initialization Failed',
      'error_model_not_found': 'Voice Model Not Found',
      'error_model_incomplete': 'Model Files Incomplete',
      'error_model_corrupted': 'Model Files Corrupted',
      'error_model_load': 'Model Loading Failed',
      'error_fcitx_not_running': 'Fcitx5 Not Running, Please Start Input Method',
      'error_fcitx_connect': 'Fcitx5 Connection Failed',
      'error_fcitx_timeout': 'Fcitx5 Connection Timeout',
      'error_fcitx_send': 'Text Send Failed',
      'error_fcitx_msg_large': 'Message Too Large',
      'error_fcitx_reconnect': 'Fcitx5 Reconnect Failed, Check Service Status',
      'error_fcitx_perm': 'Socket Permission Insecure',
      'error_fcitx_general': 'Fcitx5 Connection Error',
      'error_unknown': 'Unknown Error',

      // 通知 (AC10)
      'notify_model_switched': 'Model Switched',
      'notify_copied': 'Copied to Clipboard',
      'notify_link_copied': 'Link Copied to Clipboard',
      'notify_text_copied': 'Text Copied to Clipboard',
      'clipboard_paste_hint': 'Copied to clipboard, please paste',

      // 通用
      'listening': 'Listening...',
      'app_name': 'Nextalk',
      'copy': 'Copy',
    },
  };
}
