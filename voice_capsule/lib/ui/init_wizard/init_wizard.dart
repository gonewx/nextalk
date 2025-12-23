import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../services/model_manager.dart';
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
  InitStateData _state = InitStateData.selectMode();
  StreamSubscription<DownloadProgress>? _downloadSubscription;

  @override
  void dispose() {
    _downloadSubscription?.cancel();
    super.dispose();
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

    try {
      final error = await widget.modelManager.ensureModelReady(
        onProgress: (progress, status) {
          setState(() {
            // 从进度计算下载字节数 (假设总大小约 150MB)
            const estimatedTotal = 150 * 1024 * 1024;
            final downloaded = (progress * estimatedTotal).toInt();
            _state = InitStateData.downloading(
              progress: progress,
              downloaded: downloaded,
              total: estimatedTotal,
            );
          });
        },
      );

      if (error == ModelError.none) {
        // 下载完成
        setState(() {
          _state = InitStateData.completed();
        });
        // 通知父组件
        widget.onCompleted();
      } else {
        // 下载失败
        setState(() {
          _state = InitStateData.error(error);
        });
      }
    } on Exception catch (e) {
      // 下载失败
      setState(() {
        _state = InitStateData.error(
          ModelError.networkError,
          message: e.toString(),
        );
      });
    }
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
  }

  /// 复制下载链接
  Future<void> _copyLink() async {
    await Clipboard.setData(
      ClipboardData(text: ModelManager.downloadUrl),
    );
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('链接已复制到剪贴板'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  /// 打开模型目录
  Future<void> _openDirectory() async {
    await widget.modelManager.openModelDirectory();
  }

  /// 验证模型
  Future<void> _verifyModel() async {
    setState(() {
      _state = InitStateData.verifying();
    });

    final status = widget.modelManager.checkModelStatus();

    if (status == ModelStatus.ready) {
      setState(() {
        _state = InitStateData.completed();
      });
      widget.onCompleted();
    } else {
      setState(() {
        _state = InitStateData.error(
          ModelError.none,
          message: '未检测到有效模型，请确认文件已正确放置',
        );
      });

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
    return Center(
      child: _buildContent(),
    );
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
      case InitPhase.error:
        return DownloadProgress(
          state: _state,
          onSwitchToManual: _switchToManual,
          onCancel: _cancelDownload,
          onRetry: _state.canRetry ? _startAutoDownload : null,
        );

      case InitPhase.manualGuide:
        return ManualInstallGuide(
          onCopyLink: _copyLink,
          onOpenDirectory: _openDirectory,
          onVerifyModel: _verifyModel,
          onSwitchToAuto: _switchToAuto,
          modelUrl: ModelManager.downloadUrl,
          targetPath: ModelManager.modelDirectory,
        );

      case InitPhase.verifying:
        return const CircularProgressIndicator();

      case InitPhase.checkingModel:
      case InitPhase.completed:
        return const SizedBox.shrink();
    }
  }
}
