import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('zh')
  ];

  /// No description provided for @appName.
  ///
  /// In zh, this message translates to:
  /// **'Nextalk'**
  String get appName;

  /// No description provided for @trayShowHide.
  ///
  /// In zh, this message translates to:
  /// **'显示 / 隐藏'**
  String get trayShowHide;

  /// No description provided for @trayReconnect.
  ///
  /// In zh, this message translates to:
  /// **'重新连接 Fcitx5'**
  String get trayReconnect;

  /// No description provided for @trayModelInt8.
  ///
  /// In zh, this message translates to:
  /// **'int8 模型 (更快)'**
  String get trayModelInt8;

  /// No description provided for @trayModelStandard.
  ///
  /// In zh, this message translates to:
  /// **'标准模型 (更准)'**
  String get trayModelStandard;

  /// No description provided for @traySettings.
  ///
  /// In zh, this message translates to:
  /// **'设置'**
  String get traySettings;

  /// No description provided for @trayLanguage.
  ///
  /// In zh, this message translates to:
  /// **'语言 / Language'**
  String get trayLanguage;

  /// No description provided for @trayExit.
  ///
  /// In zh, this message translates to:
  /// **'退出'**
  String get trayExit;

  /// No description provided for @trayModelSwitchNotice.
  ///
  /// In zh, this message translates to:
  /// **'模型已切换，重启应用后生效'**
  String get trayModelSwitchNotice;

  /// No description provided for @trayAsrEngine.
  ///
  /// In zh, this message translates to:
  /// **'ASR 引擎'**
  String get trayAsrEngine;

  /// No description provided for @trayEngineZipformer.
  ///
  /// In zh, this message translates to:
  /// **'Zipformer (流式)'**
  String get trayEngineZipformer;

  /// No description provided for @trayEngineSensevoice.
  ///
  /// In zh, this message translates to:
  /// **'SenseVoice (离线)'**
  String get trayEngineSensevoice;

  /// No description provided for @trayEngineSwitching.
  ///
  /// In zh, this message translates to:
  /// **'切换中...'**
  String get trayEngineSwitching;

  /// No description provided for @trayEngineSwitchSuccess.
  ///
  /// In zh, this message translates to:
  /// **'引擎已切换为 {engine}'**
  String trayEngineSwitchSuccess(Object engine);

  /// No description provided for @trayEngineSwitchFallback.
  ///
  /// In zh, this message translates to:
  /// **'切换失败，已回退到 {engine}'**
  String trayEngineSwitchFallback(Object engine);

  /// No description provided for @trayModelSettings.
  ///
  /// In zh, this message translates to:
  /// **'模型设置'**
  String get trayModelSettings;

  /// No description provided for @trayEngineActual.
  ///
  /// In zh, this message translates to:
  /// **'当前使用'**
  String get trayEngineActual;

  /// No description provided for @wizardDownloading.
  ///
  /// In zh, this message translates to:
  /// **'正在下载...'**
  String get wizardDownloading;

  /// No description provided for @wizardExtracting.
  ///
  /// In zh, this message translates to:
  /// **'正在解压...'**
  String get wizardExtracting;

  /// No description provided for @wizardVerifying.
  ///
  /// In zh, this message translates to:
  /// **'正在校验...'**
  String get wizardVerifying;

  /// No description provided for @wizardCompleted.
  ///
  /// In zh, this message translates to:
  /// **'初始化完成！'**
  String get wizardCompleted;

  /// No description provided for @wizardSwitchManual.
  ///
  /// In zh, this message translates to:
  /// **'切换手动安装'**
  String get wizardSwitchManual;

  /// No description provided for @wizardCancel.
  ///
  /// In zh, this message translates to:
  /// **'取消'**
  String get wizardCancel;

  /// No description provided for @wizardRetry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get wizardRetry;

  /// No description provided for @wizardCopyLink.
  ///
  /// In zh, this message translates to:
  /// **'复制链接'**
  String get wizardCopyLink;

  /// No description provided for @wizardOpenDir.
  ///
  /// In zh, this message translates to:
  /// **'打开目录'**
  String get wizardOpenDir;

  /// No description provided for @wizardVerify.
  ///
  /// In zh, this message translates to:
  /// **'检测模型'**
  String get wizardVerify;

  /// No description provided for @wizardAutoDownload.
  ///
  /// In zh, this message translates to:
  /// **'自动下载'**
  String get wizardAutoDownload;

  /// No description provided for @wizardCheckingStatus.
  ///
  /// In zh, this message translates to:
  /// **'检查下载状态...'**
  String get wizardCheckingStatus;

  /// No description provided for @wizardPressHotkeyHint.
  ///
  /// In zh, this message translates to:
  /// **'按下 Right Alt 键开始语音输入'**
  String get wizardPressHotkeyHint;

  /// No description provided for @wizardStartUsing.
  ///
  /// In zh, this message translates to:
  /// **'开始使用'**
  String get wizardStartUsing;

  /// No description provided for @wizardTitle.
  ///
  /// In zh, this message translates to:
  /// **'语音模型安装'**
  String get wizardTitle;

  /// No description provided for @wizardAutoDownloadDesc.
  ///
  /// In zh, this message translates to:
  /// **'自动下载安装模型'**
  String get wizardAutoDownloadDesc;

  /// No description provided for @wizardManualInstallDesc.
  ///
  /// In zh, this message translates to:
  /// **'手动下载并安装模型'**
  String get wizardManualInstallDesc;

  /// No description provided for @wizardAutoMode.
  ///
  /// In zh, this message translates to:
  /// **'自动模式'**
  String get wizardAutoMode;

  /// No description provided for @wizardManualMode.
  ///
  /// In zh, this message translates to:
  /// **'手动模式'**
  String get wizardManualMode;

  /// No description provided for @wizardModelVerifyFailed.
  ///
  /// In zh, this message translates to:
  /// **'未检测到有效模型，请确认文件已正确放置'**
  String get wizardModelVerifyFailed;

  /// No description provided for @wizardResumingDownload.
  ///
  /// In zh, this message translates to:
  /// **'检测到已下载文件，准备校验...'**
  String get wizardResumingDownload;

  /// No description provided for @wizardFirstLaunch.
  ///
  /// In zh, this message translates to:
  /// **'Nextalk 首次启动'**
  String get wizardFirstLaunch;

  /// No description provided for @wizardModelSizeHint.
  ///
  /// In zh, this message translates to:
  /// **'需要下载语音识别模型'**
  String get wizardModelSizeHint;

  /// No description provided for @wizardRecommended.
  ///
  /// In zh, this message translates to:
  /// **'(推荐)'**
  String get wizardRecommended;

  /// No description provided for @wizardManualInstallTitle.
  ///
  /// In zh, this message translates to:
  /// **'手动安装模型'**
  String get wizardManualInstallTitle;

  /// No description provided for @wizardStep1Download.
  ///
  /// In zh, this message translates to:
  /// **'下载模型文件:'**
  String get wizardStep1Download;

  /// No description provided for @wizardStep2Extract.
  ///
  /// In zh, this message translates to:
  /// **'解压并放置到:'**
  String get wizardStep2Extract;

  /// No description provided for @wizardStep3Structure.
  ///
  /// In zh, this message translates to:
  /// **'目录结构应为:'**
  String get wizardStep3Structure;

  /// No description provided for @wizardBackToAuto.
  ///
  /// In zh, this message translates to:
  /// **'返回自动下载'**
  String get wizardBackToAuto;

  /// No description provided for @wizardDownloadFailed.
  ///
  /// In zh, this message translates to:
  /// **'下载失败'**
  String get wizardDownloadFailed;

  /// No description provided for @wizardExtractingModel.
  ///
  /// In zh, this message translates to:
  /// **'解压模型...'**
  String get wizardExtractingModel;

  /// No description provided for @wizardVerifyingFile.
  ///
  /// In zh, this message translates to:
  /// **'校验文件...'**
  String get wizardVerifyingFile;

  /// No description provided for @wizardDownloadingModel.
  ///
  /// In zh, this message translates to:
  /// **'正在下载模型...'**
  String get wizardDownloadingModel;

  /// No description provided for @errorMicNoDevice.
  ///
  /// In zh, this message translates to:
  /// **'未检测到麦克风'**
  String get errorMicNoDevice;

  /// No description provided for @errorMicBusy.
  ///
  /// In zh, this message translates to:
  /// **'麦克风被其他应用占用'**
  String get errorMicBusy;

  /// No description provided for @errorMicPermissionDenied.
  ///
  /// In zh, this message translates to:
  /// **'麦克风权限不足'**
  String get errorMicPermissionDenied;

  /// No description provided for @errorMicLost.
  ///
  /// In zh, this message translates to:
  /// **'麦克风已断开'**
  String get errorMicLost;

  /// No description provided for @errorMicInitFailed.
  ///
  /// In zh, this message translates to:
  /// **'音频设备初始化失败'**
  String get errorMicInitFailed;

  /// No description provided for @errorModelNotFound.
  ///
  /// In zh, this message translates to:
  /// **'未找到语音模型'**
  String get errorModelNotFound;

  /// No description provided for @errorModelIncomplete.
  ///
  /// In zh, this message translates to:
  /// **'模型文件不完整'**
  String get errorModelIncomplete;

  /// No description provided for @errorModelCorrupted.
  ///
  /// In zh, this message translates to:
  /// **'模型文件损坏'**
  String get errorModelCorrupted;

  /// No description provided for @errorModelLoadFailed.
  ///
  /// In zh, this message translates to:
  /// **'模型加载失败'**
  String get errorModelLoadFailed;

  /// No description provided for @errorFcitxNotRunning.
  ///
  /// In zh, this message translates to:
  /// **'Fcitx5 未运行，请先启动输入法'**
  String get errorFcitxNotRunning;

  /// No description provided for @errorFcitxConnectFailed.
  ///
  /// In zh, this message translates to:
  /// **'Fcitx5 连接失败'**
  String get errorFcitxConnectFailed;

  /// No description provided for @errorFcitxTimeout.
  ///
  /// In zh, this message translates to:
  /// **'Fcitx5 连接超时'**
  String get errorFcitxTimeout;

  /// No description provided for @errorFcitxSendFailed.
  ///
  /// In zh, this message translates to:
  /// **'文本发送失败'**
  String get errorFcitxSendFailed;

  /// No description provided for @errorFcitxMsgTooLarge.
  ///
  /// In zh, this message translates to:
  /// **'消息过大'**
  String get errorFcitxMsgTooLarge;

  /// No description provided for @errorFcitxReconnectFailed.
  ///
  /// In zh, this message translates to:
  /// **'Fcitx5 重连失败，请检查服务状态'**
  String get errorFcitxReconnectFailed;

  /// No description provided for @errorFcitxPermInsecure.
  ///
  /// In zh, this message translates to:
  /// **'Socket 权限不安全'**
  String get errorFcitxPermInsecure;

  /// No description provided for @errorFcitxGeneral.
  ///
  /// In zh, this message translates to:
  /// **'Fcitx5 连接错误'**
  String get errorFcitxGeneral;

  /// No description provided for @errorUnknown.
  ///
  /// In zh, this message translates to:
  /// **'未知错误'**
  String get errorUnknown;

  /// No description provided for @errorNetwork.
  ///
  /// In zh, this message translates to:
  /// **'网络错误'**
  String get errorNetwork;

  /// No description provided for @notifyModelSwitched.
  ///
  /// In zh, this message translates to:
  /// **'模型已切换'**
  String get notifyModelSwitched;

  /// No description provided for @notifyCopied.
  ///
  /// In zh, this message translates to:
  /// **'已复制到剪贴板'**
  String get notifyCopied;

  /// No description provided for @notifyLinkCopied.
  ///
  /// In zh, this message translates to:
  /// **'链接已复制到剪贴板'**
  String get notifyLinkCopied;

  /// No description provided for @notifyTextCopied.
  ///
  /// In zh, this message translates to:
  /// **'文本已复制到剪贴板'**
  String get notifyTextCopied;

  /// No description provided for @listening.
  ///
  /// In zh, this message translates to:
  /// **'正在聆听...'**
  String get listening;

  /// No description provided for @actionRefresh.
  ///
  /// In zh, this message translates to:
  /// **'刷新检测'**
  String get actionRefresh;

  /// No description provided for @actionCopyText.
  ///
  /// In zh, this message translates to:
  /// **'复制文本'**
  String get actionCopyText;

  /// No description provided for @actionClose.
  ///
  /// In zh, this message translates to:
  /// **'关闭'**
  String get actionClose;

  /// No description provided for @actionRetrySubmit.
  ///
  /// In zh, this message translates to:
  /// **'重试提交'**
  String get actionRetrySubmit;

  /// No description provided for @actionDiscard.
  ///
  /// In zh, this message translates to:
  /// **'放弃'**
  String get actionDiscard;

  /// No description provided for @actionRedownload.
  ///
  /// In zh, this message translates to:
  /// **'重新下载'**
  String get actionRedownload;

  /// No description provided for @actionDeleteAndRedownload.
  ///
  /// In zh, this message translates to:
  /// **'删除并重新下载'**
  String get actionDeleteAndRedownload;

  /// No description provided for @actionRetry.
  ///
  /// In zh, this message translates to:
  /// **'重试'**
  String get actionRetry;

  /// No description provided for @actionExit.
  ///
  /// In zh, this message translates to:
  /// **'退出'**
  String get actionExit;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
