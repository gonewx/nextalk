import 'package:flutter_test/flutter_test.dart';
import 'package:voice_capsule/services/model_manager.dart';
import 'package:voice_capsule/state/init_state.dart';

void main() {
  group('InitPhase Enum Tests', () {
    test('contains all expected phases', () {
      expect(InitPhase.values.length, 8);
      expect(InitPhase.values, contains(InitPhase.checkingModel));
      expect(InitPhase.values, contains(InitPhase.selectingMode));
      expect(InitPhase.values, contains(InitPhase.downloading));
      expect(InitPhase.values, contains(InitPhase.extracting));
      expect(InitPhase.values, contains(InitPhase.manualGuide));
      expect(InitPhase.values, contains(InitPhase.verifying));
      expect(InitPhase.values, contains(InitPhase.completed));
      expect(InitPhase.values, contains(InitPhase.error));
    });
  });

  group('InitStateData Factory Tests', () {
    test('checking() creates correct state', () {
      final state = InitStateData.checking();
      expect(state.phase, InitPhase.checkingModel);
      expect(state.statusMessage, '检测模型状态...');
      expect(state.progress, 0.0);
    });

    test('selectMode() creates correct state', () {
      final state = InitStateData.selectMode();
      expect(state.phase, InitPhase.selectingMode);
    });

    test('downloading() creates correct state with progress', () {
      final state = InitStateData.downloading(
        progress: 0.45,
        downloaded: 68 * 1024 * 1024, // 68MB
        total: 150 * 1024 * 1024, // 150MB
      );
      expect(state.phase, InitPhase.downloading);
      expect(state.progress, 0.45);
      expect(state.downloadedBytes, 68 * 1024 * 1024);
      expect(state.totalBytes, 150 * 1024 * 1024);
      expect(state.statusMessage, contains('45.0%'));
    });

    test('extracting() creates correct state with progress', () {
      final state = InitStateData.extracting(0.75);
      expect(state.phase, InitPhase.extracting);
      expect(state.progress, 0.75);
      expect(state.statusMessage, contains('75.0%'));
    });

    test('manualGuide() creates correct state', () {
      final state = InitStateData.manualGuide();
      expect(state.phase, InitPhase.manualGuide);
    });

    test('verifying() creates correct state', () {
      final state = InitStateData.verifying();
      expect(state.phase, InitPhase.verifying);
      expect(state.statusMessage, '验证模型...');
    });

    test('completed() creates correct state', () {
      final state = InitStateData.completed();
      expect(state.phase, InitPhase.completed);
      expect(state.progress, 1.0);
      expect(state.statusMessage, '初始化完成');
    });

    test('error() creates correct state with ModelError', () {
      final state = InitStateData.error(ModelError.networkError);
      expect(state.phase, InitPhase.error);
      expect(state.modelError, ModelError.networkError);
      expect(state.errorMessage, '网络错误，请检查网络连接');
      expect(state.canRetry, true);
    });

    test('error() with custom message uses it', () {
      final state = InitStateData.error(
        ModelError.diskSpaceError,
        message: '自定义磁盘错误',
      );
      expect(state.errorMessage, '自定义磁盘错误');
    });

    test('error() with permissionDenied cannot retry', () {
      final state = InitStateData.error(ModelError.permissionDenied);
      expect(state.canRetry, false);
    });
  });

  group('InitStateData Error Messages Tests', () {
    test('networkError has correct message', () {
      final state = InitStateData.error(ModelError.networkError);
      expect(state.errorMessage, '网络错误，请检查网络连接');
    });

    test('diskSpaceError has correct message', () {
      final state = InitStateData.error(ModelError.diskSpaceError);
      expect(state.errorMessage, '磁盘空间不足');
    });

    test('checksumMismatch has correct message', () {
      final state = InitStateData.error(ModelError.checksumMismatch);
      expect(state.errorMessage, '文件校验失败，请重新下载');
    });

    test('extractionFailed has correct message', () {
      final state = InitStateData.error(ModelError.extractionFailed);
      expect(state.errorMessage, '解压失败');
    });

    test('permissionDenied has correct message', () {
      final state = InitStateData.error(ModelError.permissionDenied);
      expect(state.errorMessage, '权限不足');
    });

    test('downloadCancelled has correct message', () {
      final state = InitStateData.error(ModelError.downloadCancelled);
      expect(state.errorMessage, '下载已取消');
    });
  });

  group('InitStateData formattedSize Tests', () {
    test('returns empty string when totalBytes is 0', () {
      final state = InitStateData.downloading(
        progress: 0.0,
        downloaded: 0,
        total: 0,
      );
      expect(state.formattedSize, '');
    });

    test('returns correct format for downloaded/total bytes', () {
      final state = InitStateData.downloading(
        progress: 0.45,
        downloaded: 68 * 1024 * 1024, // 68MB
        total: 150 * 1024 * 1024, // 150MB
      );
      expect(state.formattedSize, '68MB / 150MB');
    });

    test('handles partial MB values', () {
      final state = InitStateData.downloading(
        progress: 0.1,
        downloaded: 15 * 1024 * 1024 + 512 * 1024, // 15.5MB
        total: 100 * 1024 * 1024, // 100MB
      );
      // 15.5MB 应该四舍五入为 16MB 或 15MB (取决于 toStringAsFixed(0))
      expect(state.formattedSize, contains('MB / 100MB'));
    });
  });

  group('InitStateData canRetry Tests', () {
    test('networkError can retry', () {
      expect(InitStateData.error(ModelError.networkError).canRetry, true);
    });

    test('diskSpaceError can retry', () {
      expect(InitStateData.error(ModelError.diskSpaceError).canRetry, true);
    });

    test('checksumMismatch can retry', () {
      expect(InitStateData.error(ModelError.checksumMismatch).canRetry, true);
    });

    test('extractionFailed can retry', () {
      expect(InitStateData.error(ModelError.extractionFailed).canRetry, true);
    });

    test('downloadCancelled can retry', () {
      expect(InitStateData.error(ModelError.downloadCancelled).canRetry, true);
    });

    test('permissionDenied cannot retry', () {
      expect(InitStateData.error(ModelError.permissionDenied).canRetry, false);
    });
  });
}
