// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appName => 'Nextalk';

  @override
  String get trayShowHide => '显示 / 隐藏';

  @override
  String get trayReconnect => '重新连接 Fcitx5';

  @override
  String get trayModelInt8 => 'int8 模型 (更快)';

  @override
  String get trayModelStandard => '标准模型 (更准)';

  @override
  String get traySettings => '设置';

  @override
  String get trayLanguage => '语言 / Language';

  @override
  String get trayExit => '退出';

  @override
  String get trayModelSwitchNotice => '模型已切换，重启应用后生效';

  @override
  String get wizardDownloading => '正在下载...';

  @override
  String get wizardExtracting => '正在解压...';

  @override
  String get wizardVerifying => '正在校验...';

  @override
  String get wizardCompleted => '初始化完成！';

  @override
  String get wizardSwitchManual => '切换手动安装';

  @override
  String get wizardCancel => '取消';

  @override
  String get wizardRetry => '重试';

  @override
  String get wizardCopyLink => '复制链接';

  @override
  String get wizardOpenDir => '打开目录';

  @override
  String get wizardVerify => '检测模型';

  @override
  String get wizardAutoDownload => '自动下载';

  @override
  String get wizardCheckingStatus => '检查下载状态...';

  @override
  String get wizardPressHotkeyHint => '按下 Right Alt 键开始语音输入';

  @override
  String get wizardStartUsing => '开始使用';

  @override
  String get wizardTitle => '语音模型安装';

  @override
  String get wizardAutoDownloadDesc => '自动下载安装模型 (约400MB)';

  @override
  String get wizardManualInstallDesc => '手动下载并安装模型';

  @override
  String get wizardAutoMode => '自动模式';

  @override
  String get wizardManualMode => '手动模式';

  @override
  String get wizardModelVerifyFailed => '未检测到有效模型，请确认文件已正确放置';

  @override
  String get wizardResumingDownload => '检测到已下载文件，准备校验...';

  @override
  String get wizardFirstLaunch => 'Nextalk 首次启动';

  @override
  String get wizardModelSizeHint => '需要下载语音识别模型 (~150MB)';

  @override
  String get wizardRecommended => '(推荐)';

  @override
  String get wizardManualInstallTitle => '手动安装模型';

  @override
  String get wizardStep1Download => '下载模型文件:';

  @override
  String get wizardStep2Extract => '解压并放置到:';

  @override
  String get wizardStep3Structure => '目录结构应为:';

  @override
  String get wizardBackToAuto => '返回自动下载';

  @override
  String get wizardDownloadFailed => '下载失败';

  @override
  String get wizardExtractingModel => '解压模型...';

  @override
  String get wizardVerifyingFile => '校验文件...';

  @override
  String get wizardDownloadingModel => '正在下载模型...';

  @override
  String get errorMicNoDevice => '未检测到麦克风';

  @override
  String get errorMicBusy => '麦克风被其他应用占用';

  @override
  String get errorMicPermissionDenied => '麦克风权限不足';

  @override
  String get errorMicLost => '麦克风已断开';

  @override
  String get errorMicInitFailed => '音频设备初始化失败';

  @override
  String get errorModelNotFound => '未找到语音模型';

  @override
  String get errorModelIncomplete => '模型文件不完整';

  @override
  String get errorModelCorrupted => '模型文件损坏';

  @override
  String get errorModelLoadFailed => '模型加载失败';

  @override
  String get errorFcitxNotRunning => 'Fcitx5 未运行，请先启动输入法';

  @override
  String get errorFcitxConnectFailed => 'Fcitx5 连接失败';

  @override
  String get errorFcitxTimeout => 'Fcitx5 连接超时';

  @override
  String get errorFcitxSendFailed => '文本发送失败';

  @override
  String get errorFcitxMsgTooLarge => '消息过大';

  @override
  String get errorFcitxReconnectFailed => 'Fcitx5 重连失败，请检查服务状态';

  @override
  String get errorFcitxPermInsecure => 'Socket 权限不安全';

  @override
  String get errorFcitxGeneral => 'Fcitx5 连接错误';

  @override
  String get errorUnknown => '未知错误';

  @override
  String get errorNetwork => '网络错误';

  @override
  String get notifyModelSwitched => '模型已切换';

  @override
  String get notifyCopied => '已复制到剪贴板';

  @override
  String get notifyLinkCopied => '链接已复制到剪贴板';

  @override
  String get notifyTextCopied => '文本已复制到剪贴板';

  @override
  String get listening => '正在聆听...';

  @override
  String get actionRefresh => '刷新检测';

  @override
  String get actionCopyText => '复制文本';

  @override
  String get actionClose => '关闭';

  @override
  String get actionRetrySubmit => '重试提交';

  @override
  String get actionDiscard => '放弃';

  @override
  String get actionRedownload => '重新下载';

  @override
  String get actionDeleteAndRedownload => '删除并重新下载';

  @override
  String get actionRetry => '重试';

  @override
  String get actionExit => '退出';
}
