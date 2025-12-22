/// 胶囊状态枚举
/// Story 3-3: 状态机与动画系统
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
}

/// 错误子类型
enum CapsuleErrorType {
  /// 音频设备异常 (PortAudio 初始化失败)
  audioDeviceError,

  /// 模型加载失败
  modelError,

  /// Socket 连接断开
  socketDisconnected,

  /// 未知错误
  unknown,
}

/// 状态数据封装
/// [Source: docs/front-end-spec.md#3.1]
class CapsuleStateData {
  const CapsuleStateData({
    required this.state,
    this.errorType,
    this.errorMessage,
    this.recognizedText = '',
  });

  final CapsuleState state;
  final CapsuleErrorType? errorType;
  final String? errorMessage;
  final String recognizedText;

  /// 错误消息映射
  String get displayMessage {
    if (state != CapsuleState.error) return recognizedText;
    return errorMessage ?? _defaultErrorMessage;
  }

  String get _defaultErrorMessage {
    switch (errorType) {
      case CapsuleErrorType.audioDeviceError:
        return '音频设备异常';
      case CapsuleErrorType.modelError:
        return '模型损坏，请重启';
      case CapsuleErrorType.socketDisconnected:
        return 'Fcitx5 未连接';
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

  factory CapsuleStateData.error(CapsuleErrorType type, [String? message]) =>
      CapsuleStateData(
        state: CapsuleState.error,
        errorType: type,
        errorMessage: message,
      );

  /// copyWith 用于状态更新
  CapsuleStateData copyWith({
    CapsuleState? state,
    CapsuleErrorType? errorType,
    String? errorMessage,
    String? recognizedText,
  }) {
    return CapsuleStateData(
      state: state ?? this.state,
      errorType: errorType ?? this.errorType,
      errorMessage: errorMessage ?? this.errorMessage,
      recognizedText: recognizedText ?? this.recognizedText,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CapsuleStateData &&
        other.state == state &&
        other.errorType == errorType &&
        other.errorMessage == errorMessage &&
        other.recognizedText == recognizedText;
  }

  @override
  int get hashCode =>
      state.hashCode ^
      errorType.hashCode ^
      errorMessage.hashCode ^
      recognizedText.hashCode;

  @override
  String toString() =>
      'CapsuleStateData(state: $state, errorType: $errorType, text: $recognizedText)';
}
