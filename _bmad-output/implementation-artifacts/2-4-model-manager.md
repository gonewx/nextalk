# Story 2.4: 模型管理器 (Model Manager)

Status: done

## Prerequisites

> **前置条件**: Story 2-1 ~ 2-3 必须完成
> - ✅ Flutter Linux 构建系统已配置 (Story 2-1)
> - ✅ PortAudio FFI 绑定已完成 (Story 2-2)
> - ✅ SherpaService 已实现，需要 `modelDir` 路径参数 (Story 2-3)
> - ⚠️ 本 Story 完成后，SherpaService 可直接使用 `ModelManager.modelPath` 获取模型路径

## Story

As a **用户**,
I want **应用首次运行时自动下载所需的 AI 模型**,
So that **无需手动配置即可使用语音识别功能**。

## Acceptance Criteria

| AC | 描述 | 验证方法 |
|----|------|----------|
| AC1 | 模型状态检测: 检测模型目录是否存在且完整 | 删除模型目录后运行，确认返回"模型缺失" |
| AC2 | 模型下载: 从配置 URL 下载模型压缩包，提供进度回调 | 观察下载进度日志 (0% → 100%) |
| AC3 | 自动解压: 下载完成后自动解压到模型目录 | 检查 `~/.local/share/nextalk/models/` 目录结构 |
| AC4 | SHA256 校验: 验证下载文件完整性，失败时删除并提示重下载 | 手动损坏文件后验证校验失败处理 |
| AC5 | 跳过下载: 模型已存在且校验通过时直接返回路径 | 模型存在时确认无网络请求 |
| AC6 | 错误处理: 网络错误、磁盘空间不足等情况返回明确错误 | 断网后测试下载流程 |

## 开始前确认

```bash
# 执行以下检查，全部通过后方可开始
[ ] flutter pub deps 2>&1 | grep -q "dio"             # dio 包可用 (支持代理/重试)
[ ] flutter pub deps 2>&1 | grep -q "archive"         # archive 包可用
[ ] flutter pub deps 2>&1 | grep -q "crypto"          # crypto 包可用 (SHA256)
```

## 技术规格

### 模型信息

| 属性 | 值 |
|------|-----|
| 模型名称 | `sherpa-onnx-streaming-zipformer-bilingual-zh-en` |
| 下载 URL | `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2` |
| 文件大小 | ~70MB (压缩包) |
| 解压后大小 | ~230MB |
| SHA256 | `fb034d9c586c72c2b1e0c3c0cfcf68d0bfe7eec36f1e2073c7f2edbc1bc5b8e5` |

### 路径常量表 [Source: docs/architecture.md#4.4]

| 常量 | 值 | 说明 |
|------|-----|------|
| `XDG_DATA_HOME` | `$HOME/.local/share` | XDG 默认值 |
| `MODEL_BASE_DIR` | `$XDG_DATA_HOME/nextalk/models` | 模型根目录 |
| `MODEL_DIR` | `$MODEL_BASE_DIR/sherpa-onnx-streaming-zipformer-bilingual-zh-en` | 当前模型目录 |
| `TEMP_FILE` | `$XDG_DATA_HOME/nextalk/temp_model.tar.bz2` | 临时下载文件 |

> ⚠️ **关键**: 必须使用 `Platform.environment` 读取 XDG 环境变量，**不要使用** `path_provider` (它返回 `voice_capsule` 而非 `nextalk`)

### 模型文件结构 [Source: Story 2-3]

```text
sherpa-onnx-streaming-zipformer-bilingual-zh-en/
├── encoder-epoch-99-avg-1-chunk-16-left-128.onnx   # 编码器 (~30MB)
├── decoder-epoch-99-avg-1-chunk-16-left-128.onnx   # 解码器 (~20MB)
├── joiner-epoch-99-avg-1-chunk-16-left-128.onnx    # 联合器 (~15MB)
└── tokens.txt                                       # 词汇表 (~100KB)
```

> ⚠️ **tar.bz2 解压注意**: 压缩包内顶层目录为 `sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/`，解压时需**剥离此前缀**，直接写入 `MODEL_DIR`

## Tasks / Subtasks

> **执行顺序**: Task 1 → Task 2 → Task 3 → Task 4 → Task 5

- [x] **Task 1: 添加依赖并创建 ModelManager 类骨架** (AC: #1)
  - [x] 1.1 更新 `voice_capsule/pubspec.yaml` 添加依赖:
    ```yaml
    dependencies:
      dio: ^5.4.0           # HTTP 下载 (支持代理、重试、进度)
      archive: ^3.6.0       # tar.bz2 解压
      crypto: ^3.0.3        # SHA256 校验
    ```
  - [x] 1.2 创建 `voice_capsule/lib/services/model_manager.dart`

- [x] **Task 2: 实现模型状态检测** (AC: #1, #5)
  - [x] 2.1 实现灵活的模型文件检测 (与 SherpaService 一致)

- [x] **Task 3: 实现模型下载功能 (支持代理和重试)** (AC: #2, #6)
  - [x] 3.1 实现带重试和代理支持的下载

- [x] **Task 4: 实现 SHA256 校验和解压 (Isolate)** (AC: #3, #4)
  - [x] 4.1 实现流式 SHA256 校验 (内存优化)
  - [x] 4.2 实现 Isolate 解压 (避免阻塞主线程)
  - [x] 4.3 清理临时文件

- [x] **Task 5: 实现完整流程和单元测试** (AC: #1-6)
  - [x] 5.1 实现 `ensureModelReady()` 主入口
  - [x] 5.2 创建 `voice_capsule/test/model_manager_test.dart`
  - [x] 5.3 运行测试

## Dev Notes

### ⛔ DO NOT

| 禁止事项 | 原因 |
|----------|------|
| 使用 `path_provider` 获取路径 | 它返回 `voice_capsule` 而非 `nextalk`，与 SherpaService 不一致 |
| 硬编码检查固定文件名 | 使用前缀匹配 (`encoder*.onnx`)，与 SherpaService 保持一致 |
| 直接解压到 modelDir | tar.bz2 内有顶层目录，必须剥离前缀 |
| 在主 Isolate 解压 | 必须使用 `Isolate.run()` 避免 UI 阻塞 |
| 跳过 SHA256 校验 | 架构安全要求，必须验证文件完整性 |
| 忽略代理环境变量 | 用户可能需要代理访问 GitHub |

### 架构约束 [Source: docs/architecture.md#4.4]

| 约束 | 描述 |
|------|------|
| **存储路径** | `$XDG_DATA_HOME/nextalk/models` (不是 `voice_capsule`) |
| **校验策略** | 必须校验 SHA256，不可跳过 |
| **首次运行** | Download-on-Demand 策略 |
| **代理支持** | 检查 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量 |

### 与 SherpaService 的接口一致性 [Source: Story 2-3]

| 方面 | SherpaService | ModelManager | 说明 |
|------|---------------|--------------|------|
| 模型路径 | `config.modelDir` | `modelPath` | 必须返回相同路径 |
| 文件检测 | `_findModelFile(prefix)` | `_hasModelFile(prefix)` | 使用前缀匹配，不硬编码 |
| 路径格式 | `~/.local/share/nextalk/models/...` | 同左 | XDG 规范 |

### 依赖包说明

| 包名 | 版本 | 用途 | 替换原因 |
|------|------|------|----------|
| `dio` | ^5.4.0 | HTTP 下载 | 替换 `http`，支持代理、重试、超时 |
| `archive` | ^3.6.0 | tar.bz2 解压 | - |
| `crypto` | ^3.0.3 | SHA256 校验 | - |

### 快速验证脚本

```bash
#!/bin/bash
# scripts/verify-model-manager.sh
set -e
echo "=== Story 2-4 验证 ==="

echo "1. 检查依赖..."
cd voice_capsule
flutter pub deps | grep -q "dio" && echo "   ✅ dio 包存在"
flutter pub deps | grep -q "archive" && echo "   ✅ archive 包存在"
flutter pub deps | grep -q "crypto" && echo "   ✅ crypto 包存在"

echo "2. 运行测试..."
flutter test test/model_manager_test.dart

echo "3. 验证路径一致性..."
# 确保 ModelManager 和 SherpaService 使用相同路径
MODEL_DIR=~/.local/share/nextalk/models/sherpa-onnx-streaming-zipformer-bilingual-zh-en
if [ -d "$MODEL_DIR" ]; then
  echo "   ✅ 模型目录存在: $MODEL_DIR"
  ls "$MODEL_DIR"/*.onnx 2>/dev/null && echo "   ✅ ONNX 文件存在"
  ls "$MODEL_DIR"/tokens.txt 2>/dev/null && echo "   ✅ tokens.txt 存在"
else
  echo "   ⚠️ 模型目录不存在 (首次运行需下载)"
fi

echo "=== 验证完成 ==="
```

### 外部资源

- [Sherpa-onnx 预训练模型列表](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/index.html)
- [XDG Base Directory 规范](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Dart archive 包文档](https://pub.dev/packages/archive)
- [Dio 文档](https://pub.dev/packages/dio)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- 修复 AccumulatorSink 编译错误：使用 ChunkedConversionSink.withCallback 替代

### Completion Notes List

- ✅ Task 1: 添加 dio ^5.4.0, archive ^3.6.0, crypto ^3.0.3 依赖
- ✅ Task 2: 实现 checkModelStatus() 和 _hasModelFile() 使用前缀匹配
- ✅ Task 3: 实现 downloadModel() 支持代理检测和 3 次重试
- ✅ Task 4: 实现流式 SHA256 校验和 Isolate.run() 后台解压
- ✅ Task 5: 实现 ensureModelReady() 完整流程和 16 个单元测试
- ✅ 所有 66 个测试通过 (6 个跳过因模型未下载，属预期行为)

### Change Log

- 2025-12-22: Code Review 完成 (Amelia - Code Reviewer)
  - **H1 修复**: 添加 9 个新测试覆盖 SHA256 校验、错误处理、ensureModelReady、路径配置
  - **M1 修复**: 配置 Dio 实际使用 HTTP_PROXY/HTTPS_PROXY 代理 (via IOHttpClientAdapter)
  - **M3 修复**: 修复测试静态变量污染，每个测试使用独立目录
  - 测试数量: 7 → 16 个单元测试
  - 全部 66 个测试通过 (6 个跳过属预期)
- 2025-12-22: Story 实现完成 (Dev Agent - Amelia)
  - 实现 ModelManager 类，支持模型下载、校验、解压完整流程
  - 使用 dio 包实现带重试和代理检测的下载
  - 使用流式 SHA256 校验确保内存友好
  - 使用 Isolate.run() 后台解压避免 UI 阻塞
  - 创建 7 个单元测试覆盖核心功能
- 2025-12-22: Story Quality Review (Bob SM) - 应用全部改进
  - **C1**: 修复路径计算，使用 `Platform.environment['XDG_DATA_HOME']` 替代 `path_provider`
  - **C2**: 修复 tar.bz2 解压，剥离顶层目录前缀 `sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/`
  - **C3**: 添加实际 SHA256 值 `fb034d9c586c72c2b1e0c3c0cfcf68d0bfe7eec36f1e2073c7f2edbc1bc5b8e5`
  - **C4**: 使用 `dio` 包替代 `http`，支持代理和重试
  - **E1**: 使用前缀匹配检测模型文件，与 SherpaService 一致
  - **E2**: 添加下载重试机制 (默认 3 次)
  - **E4**: 使用 `Isolate.run()` 执行解压，避免主线程阻塞
  - **O1**: 使用流式 SHA256 计算，优化内存使用
  - 添加路径常量表，统一路径定义
  - 添加 SherpaService 接口一致性说明
  - 更新 DO NOT 表格，增加关键禁止事项
- 2025-12-22: Story created by SM Agent (Bob) - YOLO 模式

### File List

**实际创建/修改文件:**

| 文件 | 操作 | 说明 |
|------|------|------|
| `voice_capsule/pubspec.yaml` | 修改 | 添加 dio ^5.4.0, archive ^3.6.0, crypto ^3.0.3 依赖 |
| `voice_capsule/lib/services/model_manager.dart` | 新增 | 模型管理器服务 (309 行) |
| `voice_capsule/test/model_manager_test.dart` | 新增 | 单元测试 (7 个测试用例) |

---
*References: docs/architecture.md#4.4, docs/prd.md#FR2, _bmad-output/epics.md#Story-2.4, Story 2-3 (SherpaService 接口)*
