import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../constants/capsule_colors.dart';
import '../../constants/settings_constants.dart';
import '../../l10n/app_localizations.dart';
import '../../services/model_manager.dart';
import '../../services/settings_service.dart';
import '../../services/tray_service.dart';
import '../../services/window_service.dart';
import '../../state/init_state.dart';
import 'download_progress.dart';
import 'init_mode_selector.dart';
import 'manual_install_guide.dart';

/// 初始化向导容器
/// Story 3-7: 协调初始化向导各阶段的 UI 显示
class InitWizard extends StatefulWidget {
  const InitWizard({
    super.key,
    required this.modelManager,
    required this.onCompleted,
  });

  /// 模型管理器
  final ModelManager modelManager;

  /// 初始化完成回调
  final VoidCallback onCompleted;

  @override
  State<InitWizard> createState() => _InitWizardState();
}

class _InitWizardState extends State<InitWizard> {
  InitStateData _state = InitStateData.checking();
  bool _windowSizeSet = false;

  @override
  void initState() {
    super.initState();
    // 首次渲染前设置足够大的窗口
    _ensureWindowSize();
    // 检查是否有待恢复的下载/解压
    _checkPendingDownload();
  }

  @override
  void dispose() {
    super.dispose();
  }

  /// 检查是否有待恢复的下载
  Future<void> _checkPendingDownload() async {
    final (exists, downloaded, expected) =
        await widget.modelManager.checkTempFileStatus();

    if (!mounted) return;

    if (exists && expected > 0) {
      if (downloaded >= expected) {
        // 文件已完整下载，直接开始校验和解压
        final l10n = AppLocalizations.of(context);
        setState(() {
          _state = InitStateData(
            phase: InitPhase.verifying,
            progress: 0.6,
            statusMessage: l10n?.wizardResumingDownload ?? '检测到已下载文件，准备校验...',
          );
        });
        // 自动继续校验和解压流程
        _resumeFromVerification();
      } else {
        // 文件部分下载，显示断点续传进度
        final progress = downloaded / expected;
        setState(() {
          _state = InitStateData.downloading(
            progress: progress * 0.6, // 下载占 60%
            downloaded: downloaded,
            total: expected,
          );
        });
        // 3秒后自动继续下载（给用户看到进度的时间）
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) {
          _startAutoDownload();
        }
      }
    } else {
      // 没有临时文件，显示选择界面
      setState(() {
        _state = InitStateData.selectMode();
      });
    }
  }

  /// 从校验阶段恢复（临时文件已完整）
  Future<void> _resumeFromVerification() async {
    try {
      // 根据当前配置的引擎类型选择下载方法
      final engineType = SettingsService.instance.isInitialized
          ? SettingsService.instance.engineType
          : EngineType.sensevoice; // 默认 SenseVoice

      final ModelError error;
      if (engineType == EngineType.sensevoice) {
        // SenseVoice 需要下载模型 + VAD
        error = await widget.modelManager.ensureSenseVoiceReady(
          onProgress: (progress, status, {int downloaded = 0, int total = 0}) {
            if (!mounted) return;
            setState(() {
              if (progress >= 0.7 || status.contains('解压')) {
                _state = InitStateData.extracting(progress);
              } else {
                _state = InitStateData(
                  phase: InitPhase.verifying,
                  progress: progress,
                  statusMessage: status,
                );
              }
            });
          },
        );
      } else {
        // Zipformer 只需要下载模型
        error = await widget.modelManager.ensureModelReadyForEngine(
          EngineType.zipformer,
          onProgress: (progress, status, {int downloaded = 0, int total = 0}) {
            if (!mounted) return;
            setState(() {
              if (progress >= 0.7 || status.contains('解压')) {
                _state = InitStateData.extracting(progress);
              } else {
                _state = InitStateData(
                  phase: InitPhase.verifying,
                  progress: progress,
                  statusMessage: status,
                );
              }
            });
          },
        );
      }

      if (!mounted) return;

      if (error == ModelError.none) {
        setState(() {
          _state = InitStateData.completed();
        });
        // 完成时确保托盘状态正常
        TrayService.instance.updateStatus(TrayStatus.normal);
      } else {
        setState(() {
          _state = InitStateData.error(error);
        });
        // 错误时更新托盘状态
        TrayService.instance.updateStatus(TrayStatus.error);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _state = InitStateData.error(
            ModelError.networkError,
            message: e.toString(),
          );
        });
        // 错误时更新托盘状态
        TrayService.instance.updateStatus(TrayStatus.error);
      }
    }
  }

  /// 确保窗口足够大以容纳内容
  void _ensureWindowSize() {
    if (!_windowSizeSet) {
      _windowSizeSet = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        WindowService.instance.setInitWizardSize();
      });
    }
  }

  /// 开始自动下载
  Future<void> _startAutoDownload() async {
    setState(() {
      _state = InitStateData.downloading(
        progress: 0,
        downloaded: 0,
        total: 0,
      );
    });

    // 确保 UI 有机会更新，显示下载开始状态
    await Future<void>.delayed(Duration.zero);

    if (!mounted) return;

    try {
      // 根据当前配置的引擎类型选择下载方法
      final engineType = SettingsService.instance.isInitialized
          ? SettingsService.instance.engineType
          : EngineType.sensevoice; // 默认 SenseVoice

      final ModelError error;
      if (engineType == EngineType.sensevoice) {
        // SenseVoice 需要下载模型 + VAD
        error = await widget.modelManager.ensureSenseVoiceReady(
          onProgress: _onDownloadProgress,
        );
      } else {
        // Zipformer 只需要下载模型
        error = await widget.modelManager.ensureModelReadyForEngine(
          EngineType.zipformer,
          onProgress: _onDownloadProgress,
        );
      }

      if (!mounted) return;

      if (error == ModelError.none) {
        // 下载完成，显示完成界面
        setState(() {
          _state = InitStateData.completed();
        });
        // 完成时确保托盘状态正常
        TrayService.instance.updateStatus(TrayStatus.normal);
      } else {
        // 下载失败
        setState(() {
          _state = InitStateData.error(error);
        });
        // 错误时更新托盘状态
        TrayService.instance.updateStatus(TrayStatus.error);
      }
    } on Exception catch (e) {
      if (!mounted) return;
      // 下载失败
      setState(() {
        _state = InitStateData.error(
          ModelError.networkError,
          message: e.toString(),
        );
      });
      // 错误时更新托盘状态
      TrayService.instance.updateStatus(TrayStatus.error);
    }
  }

  /// 下载进度回调
  void _onDownloadProgress(double progress, String status,
      {int downloaded = 0, int total = 0}) {
    if (!mounted) return;
    setState(() {
      // 根据进度和状态判断当前阶段
      if (progress >= 0.7 || status.contains('解压')) {
        _state = InitStateData.extracting(progress);
      } else if (progress >= 0.6 || status.contains('校验')) {
        _state = InitStateData(
          phase: InitPhase.verifying,
          progress: progress,
          statusMessage: status,
        );
      } else {
        _state = InitStateData.downloading(
          progress: progress,
          downloaded: downloaded,
          total: total,
        );
      }
    });
  }

  /// 切换到手动安装
  void _switchToManual() {
    setState(() {
      _state = InitStateData.manualGuide();
    });
  }

  /// 切换到自动下载
  void _switchToAuto() {
    setState(() {
      _state = InitStateData.selectMode();
    });
  }

  /// 取消下载
  void _cancelDownload() {
    widget.modelManager.cancelDownload();
    setState(() {
      _state = InitStateData.selectMode();
    });
    // 取消下载后恢复托盘状态为正常
    TrayService.instance.updateStatus(TrayStatus.normal);
  }

  /// 复制下载链接
  /// Story 3-8: 使用国际化文本
  /// Story 2-7: 支持复制不同引擎的 URL
  Future<void> _copyLink(String url) async {
    await Clipboard.setData(
      ClipboardData(text: url),
    );
    if (mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n?.notifyLinkCopied ?? '链接已复制到剪贴板'),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  /// 打开模型目录
  Future<void> _openDirectory() async {
    await widget.modelManager.openModelDirectory();
  }

  /// 验证模型
  /// Story 2-7: 支持验证当前引擎的模型（SenseVoice 还需要验证 VAD）
  Future<void> _verifyModel() async {
    setState(() {
      _state = InitStateData.verifying();
    });

    // 获取当前引擎类型
    final engineType = SettingsService.instance.isInitialized
        ? SettingsService.instance.engineType
        : EngineType.sensevoice;

    // 检查 ASR 模型状态
    final asrStatus = widget.modelManager.checkModelStatusForEngine(engineType);

    // 如果是 SenseVoice，还需要检查 VAD 模型
    bool vadReady = true;
    if (engineType == EngineType.sensevoice) {
      final vadStatus = widget.modelManager.checkVadModelStatus();
      vadReady = vadStatus == ModelStatus.ready;
    }

    if (asrStatus == ModelStatus.ready && vadReady) {
      setState(() {
        _state = InitStateData.completed();
      });
      // 完成时确保托盘状态正常
      TrayService.instance.updateStatus(TrayStatus.normal);
    } else {
      final l10n = AppLocalizations.of(context);
      String errorMsg = l10n?.wizardModelVerifyFailed ?? '未检测到有效模型，请确认文件已正确放置';
      if (asrStatus != ModelStatus.ready) {
        errorMsg = '${engineType == EngineType.sensevoice ? "SenseVoice" : "Zipformer"} 模型未就绪';
      } else if (!vadReady) {
        errorMsg = 'VAD 模型未就绪';
      }
      setState(() {
        _state = InitStateData.error(
          ModelError.none,
          message: errorMsg,
        );
      });
      // 验证失败时更新托盘状态为警告
      TrayService.instance.updateStatus(TrayStatus.warning);

      // 2秒后回到手动安装页面
      await Future.delayed(const Duration(seconds: 2));
      if (mounted) {
        setState(() {
          _state = InitStateData.manualGuide();
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      // 支持拖动窗口
      onPanStart: (_) => WindowService.instance.startDragging(),
      child: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Stack(
              children: [
                _buildContent(),
                // 关闭按钮
                Positioned(
                  top: 8,
                  right: 8,
                  child: IconButton(
                    onPressed: _onClose,
                    icon:
                        const Icon(Icons.close, color: Colors.white54, size: 20),
                    tooltip: '退出',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// 关闭/退出应用
  void _onClose() {
    // 如果已经完成初始化，则标记完成并隐藏窗口
    // 这样下次按快捷键时会直接显示主界面
    if (_state.phase == InitPhase.completed) {
      widget.onCompleted();
      return;
    }
    // 其他状态下退出应用
    SystemNavigator.pop();
  }

  Widget _buildContent() {
    switch (_state.phase) {
      case InitPhase.selectingMode:
        return InitModeSelector(
          onAutoDownload: _startAutoDownload,
          onManualInstall: _switchToManual,
        );

      case InitPhase.downloading:
      case InitPhase.extracting:
      case InitPhase.verifying:
      case InitPhase.error:
        return DownloadProgress(
          state: _state,
          onSwitchToManual: _switchToManual,
          onCancel: _cancelDownload,
          onRetry: _state.canRetry ? _startAutoDownload : null,
        );

      case InitPhase.manualGuide:
        // Story 2-7: 根据当前引擎类型动态显示下载说明
        final engineType = SettingsService.instance.isInitialized
            ? SettingsService.instance.engineType
            : EngineType.sensevoice;
        final isSenseVoice = engineType == EngineType.sensevoice;

        return ManualInstallGuide(
          onCopyLink: _copyLink,
          onOpenDirectory: _openDirectory,
          onVerifyModel: _verifyModel,
          onSwitchToAuto: _switchToAuto,
          engineType: engineType,
          modelUrl: widget.modelManager.getDownloadUrlForEngine(engineType),
          targetPath: ModelManager.modelDirectory,
          expectedStructure: widget.modelManager.getExpectedStructureForEngine(engineType),
          vadUrl: isSenseVoice ? widget.modelManager.vadDownloadUrl : null,
          vadExpectedStructure: isSenseVoice ? widget.modelManager.vadExpectedStructure : null,
        );

      case InitPhase.checkingModel:
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              Text(
                AppLocalizations.of(context)?.wizardCheckingStatus ?? '检查下载状态...',
                style: const TextStyle(color: Colors.white70),
              ),
            ],
          ),
        );

      case InitPhase.completed:
        return _buildCompletedUI();
    }
  }

  /// 构建完成提示界面
  /// Story 3-8: 使用国际化文本 (AC9)
  Widget _buildCompletedUI() {
    final l10n = AppLocalizations.of(context);

    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: CapsuleColors.background,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: CapsuleColors.borderGlow),
        boxShadow: [
          BoxShadow(
            color: CapsuleColors.shadow,
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.check_circle,
            color: Colors.green,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            '🎉 ${l10n?.wizardCompleted ?? '初始化完成！'}',
            style: TextStyle(
              color: CapsuleColors.textWhite,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            l10n?.wizardPressHotkeyHint ?? '按下 Right Alt 键开始语音输入',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: widget.onCompleted,
            style: ElevatedButton.styleFrom(
              backgroundColor: CapsuleColors.accentRed,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
            ),
            child: Text(l10n?.wizardStartUsing ?? '开始使用'),
          ),
        ],
      ),
    );
  }
}
