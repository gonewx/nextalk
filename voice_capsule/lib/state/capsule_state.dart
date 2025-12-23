import '../services/fcitx_client.dart';

/// 胶囊状态枚举
/// Story 3-3: 状态机与动画系统
/// Story 3-7: 新增初始化状态
enum CapsuleState {
  /// 空闲/隐藏状态 - 窗口不可见
  idle,

  /// 聆听中 - 正在录音，等待用户说话
  /// 视觉: 红点呼吸 + 波纹扩散 + 光标闪烁
  listening,

  /// 处理中 - VAD 触发，正在提交文本
  /// 视觉: 红点快速脉冲 + 文字变暗
  processing,

  /// 错误状态 - 包含子类型
  /// 视觉: 黄色(警告)/灰色(无设备) + 错误文字
  error,

  /// 初始化中 - 首次运行检测
  /// Story 3-7: 新增
  initializing,

  /// 模型下载中
  /// Story 3-7: 新增
  downloading,

  /// 模型解压中
  /// Story 3-7: 新增
  extracting,
}

/// 错误子类型
/// Story 3-7: 细化错误类型
enum CapsuleErrorType {
  // === 音频相关 (细化) ===

  /// 未检测到麦克风
  audioNoDevice,

  /// 设备被占用
  audioDeviceBusy,

  /// 权限不足
  audioPermissionDenied,

  /// 运行时设备丢失
  audioDeviceLost,

  /// 初始化失败 (通用)
  audioInitFailed,

  // === 模型相关 (细化) ===

  /// 模型未找到
  modelNotFound,

  /// 模型不完整
  modelIncomplete,

  /// 模型损坏
  modelCorrupted,

  /// 加载失败
  modelLoadFailed,

  // === 连接相关 ===

  /// Socket/Fcitx5 错误 (使用 fcitxError 字段细化)
  socketError,

  // === 其他 ===

  /// 未知错误
  unknown,
}

/// 状态数据封装
/// [Source: docs/front-end-spec.md#3.1]
/// Story 3-7: 扩展支持 fcitxError 和 preservedText
class CapsuleStateData {
  const CapsuleStateData({
    required this.state,
    this.errorType,
    this.errorMessage,
    this.recognizedText = '',
    this.fcitxError,
    this.preservedText,
  });

  final CapsuleState state;
  final CapsuleErrorType? errorType;
  final String? errorMessage;
  final String recognizedText;

  /// Story 3-7: Socket 错误细化
  final FcitxError? fcitxError;

  /// Story 3-7: 提交失败时保护的文本
  final String? preservedText;

  /// 错误消息映射
  String get displayMessage {
    if (state != CapsuleState.error) return recognizedText;

    // Socket 错误使用 FcitxError 细化消息
    if (errorType == CapsuleErrorType.socketError && fcitxError != null) {
      return switch (fcitxError!) {
        FcitxError.socketNotFound => 'Fcitx5 未运行，请先启动输入法',
        FcitxError.connectionFailed => 'Fcitx5 连接失败',
        FcitxError.connectionTimeout => 'Fcitx5 连接超时',
        FcitxError.sendFailed => '文本发送失败',
        FcitxError.messageTooLarge => '消息过大',
        FcitxError.reconnectFailed => 'Fcitx5 重连失败，请检查服务状态',
        FcitxError.socketPermissionInsecure => 'Socket 权限不安全',
      };
    }

    return errorMessage ?? _defaultErrorMessage;
  }

  String get _defaultErrorMessage {
    switch (errorType) {
      // 音频相关
      case CapsuleErrorType.audioNoDevice:
        return '未检测到麦克风';
      case CapsuleErrorType.audioDeviceBusy:
        return '麦克风被其他应用占用';
      case CapsuleErrorType.audioPermissionDenied:
        return '麦克风权限不足';
      case CapsuleErrorType.audioDeviceLost:
        return '麦克风已断开';
      case CapsuleErrorType.audioInitFailed:
        return '音频设备初始化失败';
      // 模型相关
      case CapsuleErrorType.modelNotFound:
        return '未找到语音模型';
      case CapsuleErrorType.modelIncomplete:
        return '模型文件不完整';
      case CapsuleErrorType.modelCorrupted:
        return '模型文件损坏';
      case CapsuleErrorType.modelLoadFailed:
        return '模型加载失败';
      // Socket 相关
      case CapsuleErrorType.socketError:
        return 'Fcitx5 连接错误';
      // 其他
      case CapsuleErrorType.unknown:
      case null:
        return '未知错误';
    }
  }

  /// 工厂构造函数
  factory CapsuleStateData.idle({String text = ''}) =>
      CapsuleStateData(state: CapsuleState.idle, recognizedText: text);

  factory CapsuleStateData.listening({String text = ''}) =>
      CapsuleStateData(state: CapsuleState.listening, recognizedText: text);

  factory CapsuleStateData.processing({String text = ''}) =>
      CapsuleStateData(state: CapsuleState.processing, recognizedText: text);

  /// Story 3-7: 扩展 error 工厂支持 fcitxError 和 preservedText
  factory CapsuleStateData.error(
    CapsuleErrorType type, {
    String? message,
    FcitxError? fcitxError,
    String? preservedText,
  }) =>
      CapsuleStateData(
        state: CapsuleState.error,
        errorType: type,
        errorMessage: message,
        fcitxError: fcitxError,
        preservedText: preservedText,
      );

  /// copyWith 用于状态更新
  CapsuleStateData copyWith({
    CapsuleState? state,
    CapsuleErrorType? errorType,
    String? errorMessage,
    String? recognizedText,
    FcitxError? fcitxError,
    String? preservedText,
  }) {
    return CapsuleStateData(
      state: state ?? this.state,
      errorType: errorType ?? this.errorType,
      errorMessage: errorMessage ?? this.errorMessage,
      recognizedText: recognizedText ?? this.recognizedText,
      fcitxError: fcitxError ?? this.fcitxError,
      preservedText: preservedText ?? this.preservedText,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CapsuleStateData &&
        other.state == state &&
        other.errorType == errorType &&
        other.errorMessage == errorMessage &&
        other.recognizedText == recognizedText &&
        other.fcitxError == fcitxError &&
        other.preservedText == preservedText;
  }

  @override
  int get hashCode =>
      state.hashCode ^
      errorType.hashCode ^
      errorMessage.hashCode ^
      recognizedText.hashCode ^
      fcitxError.hashCode ^
      preservedText.hashCode;

  @override
  String toString() =>
      'CapsuleStateData(state: $state, errorType: $errorType, text: $recognizedText)';
}



