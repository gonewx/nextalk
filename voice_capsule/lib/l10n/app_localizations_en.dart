// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Nextalk';

  @override
  String get trayShowHide => 'Show / Hide';

  @override
  String get trayReconnect => 'Reconnect Fcitx5';

  @override
  String get trayModelInt8 => 'int8 Model (Faster)';

  @override
  String get trayModelStandard => 'Standard Model (More Accurate)';

  @override
  String get traySettings => 'Settings';

  @override
  String get trayLanguage => '语言 / Language';

  @override
  String get trayExit => 'Exit';

  @override
  String get trayModelSwitchNotice =>
      'Model switched, restart app to take effect';

  @override
  String get trayAsrEngine => 'ASR Engine';

  @override
  String get trayEngineZipformer => 'Zipformer (Streaming)';

  @override
  String get trayEngineSensevoice => 'SenseVoice (Offline)';

  @override
  String get trayEngineSwitching => 'Switching...';

  @override
  String trayEngineSwitchSuccess(Object engine) {
    return 'Engine switched to $engine';
  }

  @override
  String trayEngineSwitchFallback(Object engine) {
    return 'Switch failed, fallback to $engine';
  }

  @override
  String get trayModelSettings => 'Model Settings';

  @override
  String get trayEngineActual => 'In Use';

  @override
  String get wizardDownloading => 'Downloading...';

  @override
  String get wizardExtracting => 'Extracting...';

  @override
  String get wizardVerifying => 'Verifying...';

  @override
  String get wizardCompleted => 'Initialization Complete!';

  @override
  String get wizardSwitchManual => 'Switch to Manual Install';

  @override
  String get wizardCancel => 'Cancel';

  @override
  String get wizardRetry => 'Retry';

  @override
  String get wizardCopyLink => 'Copy Link';

  @override
  String get wizardOpenDir => 'Open Directory';

  @override
  String get wizardVerify => 'Verify Model';

  @override
  String get wizardAutoDownload => 'Auto Download';

  @override
  String get wizardCheckingStatus => 'Checking download status...';

  @override
  String get wizardPressHotkeyHint => 'Press Right Alt to start voice input';

  @override
  String get wizardStartUsing => 'Start Using';

  @override
  String get wizardTitle => 'Voice Model Installation';

  @override
  String get wizardAutoDownloadDesc =>
      'Automatically download and install model';

  @override
  String get wizardManualInstallDesc => 'Manually download and install model';

  @override
  String get wizardAutoMode => 'Auto Mode';

  @override
  String get wizardManualMode => 'Manual Mode';

  @override
  String get wizardModelVerifyFailed =>
      'No valid model detected, please confirm files are placed correctly';

  @override
  String get wizardResumingDownload =>
      'Detected downloaded file, preparing to verify...';

  @override
  String get wizardFirstLaunch => 'Nextalk First Launch';

  @override
  String get wizardModelSizeHint => 'Voice model download required';

  @override
  String get wizardRecommended => '(Recommended)';

  @override
  String get wizardManualInstallTitle => 'Manual Install Model';

  @override
  String get wizardStep1Download => 'Download model file:';

  @override
  String get wizardStep2Extract => 'Extract and place to:';

  @override
  String get wizardStep3Structure => 'Directory structure should be:';

  @override
  String get wizardBackToAuto => 'Back to Auto Download';

  @override
  String get wizardDownloadFailed => 'Download Failed';

  @override
  String get wizardExtractingModel => 'Extracting model...';

  @override
  String get wizardVerifyingFile => 'Verifying file...';

  @override
  String get wizardDownloadingModel => 'Downloading model...';

  @override
  String get errorMicNoDevice => 'Microphone Not Detected';

  @override
  String get errorMicBusy => 'Microphone In Use by Another App';

  @override
  String get errorMicPermissionDenied => 'Microphone Permission Denied';

  @override
  String get errorMicLost => 'Microphone Disconnected';

  @override
  String get errorMicInitFailed => 'Audio Device Initialization Failed';

  @override
  String get errorModelNotFound => 'Voice Model Not Found';

  @override
  String get errorModelIncomplete => 'Model Files Incomplete';

  @override
  String get errorModelCorrupted => 'Model Files Corrupted';

  @override
  String get errorModelLoadFailed => 'Model Loading Failed';

  @override
  String get errorFcitxNotRunning =>
      'Fcitx5 Not Running, Please Start Input Method';

  @override
  String get errorFcitxConnectFailed => 'Fcitx5 Connection Failed';

  @override
  String get errorFcitxTimeout => 'Fcitx5 Connection Timeout';

  @override
  String get errorFcitxSendFailed => 'Text Send Failed';

  @override
  String get errorFcitxMsgTooLarge => 'Message Too Large';

  @override
  String get errorFcitxReconnectFailed =>
      'Fcitx5 Reconnect Failed, Check Service Status';

  @override
  String get errorFcitxPermInsecure => 'Socket Permission Insecure';

  @override
  String get errorFcitxGeneral => 'Fcitx5 Connection Error';

  @override
  String get errorUnknown => 'Unknown Error';

  @override
  String get errorNetwork => 'Network Error';

  @override
  String get notifyModelSwitched => 'Model Switched';

  @override
  String get notifyCopied => 'Copied to Clipboard';

  @override
  String get notifyLinkCopied => 'Link Copied to Clipboard';

  @override
  String get notifyTextCopied => 'Text Copied to Clipboard';

  @override
  String get listening => 'Listening...';

  @override
  String get actionRefresh => 'Refresh Detection';

  @override
  String get actionCopyText => 'Copy Text';

  @override
  String get actionClose => 'Close';

  @override
  String get actionRetrySubmit => 'Retry Submit';

  @override
  String get actionDiscard => 'Discard';

  @override
  String get actionRedownload => 'Re-download';

  @override
  String get actionDeleteAndRedownload => 'Delete and Re-download';

  @override
  String get actionRetry => 'Retry';

  @override
  String get actionExit => 'Exit';
}
