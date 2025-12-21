# Story 1.4: Flutter 项目初始化

Status: done

## Prerequisites

> **本 Story 无前置依赖**，可独立开始。
>
> ⚠️ **重要**: 本 Story 是以下 Story 的**阻塞前置条件**:
> - Story 1-3 (Dart Socket Client) - 需要 `voice_capsule/lib/services/` 目录
> - Story 2-1 (原生库链接配置) - 需要 `linux/CMakeLists.txt` RPATH 配置
> - Story 2-2/2-3 (FFI 绑定) - 需要 `lib/ffi/` 目录
>
> 请在完成本 Story 后再开始上述 Story 的开发。

## Story

As a 开发者,
I want 创建 Flutter Linux 项目的基础结构,
So that 有一个可扩展的代码基础用于后续功能开发。

## Acceptance Criteria

1. **AC1: Flutter 项目创建**
   - **Given** Monorepo 根目录 `/mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2`
   - **When** 初始化 Flutter 项目
   - **Then** `/voice_capsule/` 目录包含完整的 Flutter Linux 项目
   - **And** 使用 `flutter create voice_capsule --platforms=linux` 创建
   - **And** 项目可成功执行 `flutter doctor` 无阻塞错误

2. **AC2: pubspec.yaml 配置**
   - **Given** Flutter 项目已创建
   - **When** 配置 pubspec.yaml
   - **Then** `name: voice_capsule` (项目名)
   - **And** `description` 包含 Nextalk 描述
   - **And** `environment.sdk` 设置为 Flutter 3.x+ 兼容版本

3. **AC3: CMakeLists.txt RPATH 配置**
   - **Given** Flutter 项目已创建
   - **When** 修改 `linux/CMakeLists.txt`
   - **Then** 设置 `CMAKE_INSTALL_RPATH` 为 `$ORIGIN/lib`
   - **And** 预留 libsherpa-onnx-c-api.so 复制配置 (注释形式)
   - **And** 配置 RPATH 使程序能从可执行文件旁的 lib/ 目录加载动态库

4. **AC4: 目录结构符合架构**
   - **Given** Flutter 项目已创建
   - **When** 创建业务目录结构
   - **Then** 存在 `lib/ffi/` 目录 (用于 FFI 绑定)
   - **And** 存在 `lib/services/` 目录 (用于业务逻辑)
   - **And** 存在 `lib/ui/` 目录 (用于 Widget 组件)
   - **And** main.dart 保留基础结构，可被后续 Story 扩展

5. **AC5: 构建验证**
   - **Given** 项目结构配置完成
   - **When** 执行 `flutter build linux`
   - **Then** 构建成功，无错误
   - **And** 生成可执行文件位于 `build/linux/x64/release/bundle/`
   - **And** RPATH 配置正确 (可通过 `readelf -d` 验证)

## Tasks / Subtasks

> **执行顺序**: Task 0 → Task 1 → Task 2 → Task 3 → Task 4 → Task 5

- [x] **Task 0: 环境预检** (Prerequisites)
  - [x] 0.1 验证 Flutter 版本: `flutter --version`
    - **期望输出**: `Flutter 3.x.x • channel stable` (版本 >= 3.0.0, < 4.0.0)
  - [x] 0.2 验证 Linux 桌面开发支持: `flutter doctor`
    - **期望输出**: `[✓] Linux toolchain - develop for Linux desktop`
    - 若显示 `[✗]` 或 `[!]`，需先安装依赖
  - [x] 0.3 若缺失依赖，执行:
    ```bash
    sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev libstdc++-12-dev
    ```
  - **失败处理**: 若 Flutter 未安装或版本不在 3.0.0-4.0.0 范围内，参考 https://docs.flutter.dev/get-started/install/linux

- [x] **Task 1: 创建 Flutter 项目** (AC: #1)
  - [x] 1.1 进入项目根目录: `cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2`
  - [x] 1.2 创建 Flutter 项目: `flutter create voice_capsule --platforms=linux`
  - [x] 1.3 验证创建成功: `test -f voice_capsule/lib/main.dart && echo "OK"`
  - [x] 1.4 进入项目目录验证: `cd voice_capsule && flutter doctor`
  - **验证**: `flutter analyze` 无错误
  - **注意**: Flutter 会自动生成 `analysis_options.yaml`，保留默认配置即可

- [x] **Task 2: 配置 pubspec.yaml** (AC: #2)
  - [x] 2.1 修改项目名称和描述 (见 Dev Notes - pubspec.yaml 配置)
  - [x] 2.2 确认 SDK 约束: `sdk: ">=3.0.0 <4.0.0"`
  - [x] 2.3 确认 Flutter 约束: `flutter: ">=3.0.0"`
  - [x] 2.4 保留 Flutter 默认生成的 dev_dependencies (flutter_test, flutter_lints)
  - **验证**: `flutter pub get` 成功

- [x] **Task 3: 配置 CMakeLists.txt RPATH** (AC: #3)
  - [x] 3.1 打开 `voice_capsule/linux/CMakeLists.txt`
  - [x] 3.2 定位插入点: 在文件中搜索 `set(APPLICATION_ID`，在该行**下方**添加 RPATH 配置
    - 默认 Flutter 生成的该行约在第 5-10 行附近
  - [x] 3.3 添加 RPATH 配置和预留的库复制注释 (见 Dev Notes)
  - [x] 3.4 修改 APPLICATION_ID 为 `com.nextalk.voice_capsule`
  - **验证**: `cd voice_capsule && flutter build linux` 无 CMake 错误

- [x] **Task 4: 创建业务目录结构** (AC: #4)
  - [x] 4.1 创建目录并添加 .gitkeep:
    ```bash
    mkdir -p voice_capsule/lib/{ffi,services,ui}
    touch voice_capsule/lib/{ffi,services,ui}/.gitkeep
    ```
  - **验证**: `ls voice_capsule/lib/` 显示 ffi/, services/, ui/ 目录

- [x] **Task 5: 构建验证** (AC: #5)
  - [x] 5.1 执行完整验证脚本 (见 Dev Notes - 一键验证脚本)
  - **期望结果**: 所有检查通过，Flutter Demo 窗口正常显示

## Dev Notes

### 项目关系概览

```
本 Story (1-4)
    │
    ├──► Story 1-3 (Dart Socket Client) - 需要 lib/services/
    ├──► Story 2-1 (原生库链接) - 需要 CMakeLists.txt RPATH
    ├──► Story 2-2 (PortAudio FFI) - 需要 lib/ffi/
    └──► Story 2-3 (Sherpa FFI) - 需要 lib/ffi/

已完成的 Story (无直接依赖):
    • Story 1-1 (Fcitx5 插件集成) ✓
    • Story 1-2 (插件安装脚本) ✓
```

### pubspec.yaml 配置

修改 `voice_capsule/pubspec.yaml`:

```yaml
name: voice_capsule
description: "Nextalk Voice Capsule - Linux 高性能离线语音输入应用的 Flutter 前端"
publish_to: 'none' # 私有项目，不发布到 pub.dev
version: 0.1.0+1

environment:
  sdk: ">=3.0.0 <4.0.0"
  flutter: ">=3.0.0"

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2

# 保留 Flutter 默认生成的 dev_dependencies，无需修改
dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0

flutter:
  uses-material-design: true
```

> **注意**: `flutter_lints` 版本应与 Flutter 版本匹配。Flutter 3.x 默认生成 `^5.0.0`，保留默认值即可。

### CMakeLists.txt RPATH 配置

在 `voice_capsule/linux/CMakeLists.txt` 中，找到 `set(APPLICATION_ID ...)` 行（约第 5-10 行），在其**下方**添加:

```cmake
# 修改 APPLICATION_ID
set(APPLICATION_ID "com.nextalk.voice_capsule")

# ============================================
# Nextalk: RPATH 配置 (用于运行时动态库查找)
# ============================================
set(CMAKE_INSTALL_RPATH "$ORIGIN/lib")
set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)

# ============================================
# Nextalk: 原生库复制配置 (Story 2-1 实现)
# ============================================
# TODO: Story 2-1 将添加以下配置:
# set(LIBS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../libs")
# install(FILES "${LIBS_DIR}/libsherpa-onnx-c-api.so"
#         DESTINATION "${CMAKE_INSTALL_PREFIX}/lib"
#         COMPONENT Runtime)
```

### 目标目录结构

```
voice_capsule/
├── pubspec.yaml              # 项目配置 (修改)
├── analysis_options.yaml     # Lint 配置 (保留默认)
├── linux/
│   └── CMakeLists.txt        # 构建配置 (修改 RPATH)
├── lib/
│   ├── main.dart             # 入口 (保留默认)
│   ├── ffi/                  # FFI 绑定层 (新建)
│   │   └── .gitkeep
│   ├── services/             # 业务逻辑 (新建)
│   │   └── .gitkeep
│   └── ui/                   # Widget 组件 (新建)
│       └── .gitkeep
└── test/
    └── widget_test.dart      # 默认测试 (保留)
```

### 一键验证脚本

将以下脚本保存或直接执行:

```bash
#!/bin/bash
set -e
cd /mnt/disk0/project/newx/nextalk/nextalk_fcitx5_v2/voice_capsule

echo "=== Step 1: 获取依赖 ==="
flutter pub get

echo "=== Step 2: 静态分析 ==="
flutter analyze
# 期望: No issues found!

echo "=== Step 3: Release 构建 ==="
flutter build linux --release

echo "=== Step 4: 验证产物 ==="
BUNDLE="build/linux/x64/release/bundle"
test -f "$BUNDLE/voice_capsule" && echo "[✓] 可执行文件存在"
test -d "$BUNDLE/lib" && echo "[✓] lib/ 目录存在"

echo "=== Step 5: 验证 RPATH ==="
RPATH_OUTPUT=$(readelf -d "$BUNDLE/voice_capsule" 2>/dev/null | grep -E "RUNPATH|RPATH" || true)
if echo "$RPATH_OUTPUT" | grep -q '\$ORIGIN/lib'; then
  echo "[✓] RPATH 配置正确: \$ORIGIN/lib"
else
  echo "[✗] RPATH 配置错误或缺失"
  echo "    实际输出: $RPATH_OUTPUT"
  exit 1
fi

echo "=== Step 6: 测试运行 (手动关闭窗口) ==="
echo "启动 Flutter Demo..."
"$BUNDLE/voice_capsule" &
APP_PID=$!
sleep 3
if kill -0 $APP_PID 2>/dev/null; then
  echo "[✓] 应用启动成功 (PID: $APP_PID)"
  echo "请手动关闭窗口，或运行: kill $APP_PID"
else
  echo "[✗] 应用启动失败"
  exit 1
fi

echo ""
echo "=== 所有验证通过 ✓ ==="
```

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| `flutter create` 失败 | 安装 Flutter 并配置 PATH |
| `[✗] Linux toolchain` | `sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev libstdc++-12-dev` |
| CMake Error | 确认 CMake >= 3.16: `cmake --version` |
| RPATH 未设置 | 检查 `CMAKE_BUILD_WITH_INSTALL_RPATH TRUE` 是否添加 |

### IDE 配置建议 (可选)

推荐使用 VS Code + Flutter 插件:
1. 安装 "Flutter" 和 "Dart" 扩展
2. 打开 `voice_capsule/` 目录作为工作区
3. 使用 `F5` 或 Run > Start Debugging 启动调试

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

无异常

### Completion Notes List

- ✅ Flutter 3.32.5 环境验证通过，Linux toolchain 正常
- ✅ 使用 `flutter create voice_capsule --platforms=linux` 成功创建项目
- ✅ pubspec.yaml 配置: name=voice_capsule, sdk>=3.0.0<4.0.0, flutter>=3.0.0
- ✅ CMakeLists.txt RPATH 配置: `$ORIGIN/lib`, APPLICATION_ID=com.nextalk.voice_capsule
- ✅ 业务目录结构创建: lib/ffi/, lib/services/, lib/ui/ (含 .gitkeep)
- ✅ flutter build linux --release 构建成功
- ✅ RPATH 验证: readelf 确认 RUNPATH=$ORIGIN/lib
- ✅ 所有 Acceptance Criteria 满足

### Change Log

- 2025-12-22: Code Review (Amelia) - 修复 3 个 MEDIUM 问题:
  - M1: main.dart 标题改为 "Nextalk Voice Capsule"
  - M2: CMakeLists.txt 注释风格统一
  - M3: voice_capsule/ 加入 Git 暂存区
- 2025-12-22: Story 实现完成 (Dev Agent - Amelia)
- 2025-12-22: Story Review (Bob) - 应用全部改进建议 (C1-C2, E1-E5, O1-O3, L1-L4)
- 2025-12-22: Story created by SM Agent (Bob) - 完整上下文分析

### File List

**新增文件:**
- voice_capsule/ (整个 Flutter 项目目录)
- voice_capsule/pubspec.yaml (修改)
- voice_capsule/linux/CMakeLists.txt (修改)
- voice_capsule/lib/ffi/.gitkeep (新增)
- voice_capsule/lib/services/.gitkeep (新增)
- voice_capsule/lib/ui/.gitkeep (新增)

---
*References: docs/architecture.md#2.2, docs/architecture.md#5.2, _bmad-output/epics.md#Story-1.4*
