# Story 1.1: Fcitx5 插件集成

Status: done

## Story

As a 开发者,
I want 将现有的 Fcitx5 C++ 插件代码正确集成到 Monorepo 结构中,
So that 项目有一个统一的代码库结构，便于后续开发和维护。

## Acceptance Criteria

1. **AC1: 环境预检**
   - **Given** 开发机器准备开始此 Story
   - **When** 执行环境检查
   - **Then** Fcitx5 版本 >= 5.0.0 已安装 (`fcitx5 --version`)
   - **And** fcitx5-dev 开发包已安装 (`pkg-config --modversion fcitx5`)
   - **And** CMake 和 build-essential 已安装

2. **AC2: 源码迁移**
   - **Given** 现有的 Fcitx5 插件源码位于 `/mnt/disk0/project/newx/nextalk/nextalk_fcitx5/addons`
   - **When** 执行代码迁移
   - **Then** 插件源码复制到当前项目的 `/addons/fcitx5/` 目录下
   - **And** 目录结构保持完整 (CMakeLists.txt, src/nextalk.cpp, src/nextalk.h, src/nextalk.conf.in)

3. **AC3: CMake 配置正确**
   - **Given** 插件源码已迁移
   - **When** 执行 CMake 配置
   - **Then** CMakeLists.txt 正确配置，可独立编译插件
   - **And** 找到 Fcitx5Core 和 Fcitx5Utils 依赖

4. **AC4: ydotool 回退逻辑移除**
   - **Given** 原有代码包含 ydotool 回退逻辑 (nextalk.cpp:197-207)
   - **When** 代码清理完成
   - **Then** 移除所有 ydotool 相关代码
   - **And** 当无输入上下文时，仅记录警告日志，不执行外部命令

5. **AC5: 编译成功**
   - **Given** 代码已迁移且 ydotool 逻辑已移除
   - **When** 执行编译 (使用 `-Wall -Wextra` 警告标志)
   - **Then** 插件能成功编译生成 `libnextalk.so` 文件
   - **And** 无编译警告或错误
   - **And** 编译输出无 undefined reference 错误

6. **AC6: 插件功能验证**
   - **Given** 编译成功且 libnextalk.so 已生成
   - **When** 将插件安装到 Fcitx5 目录并重启 Fcitx5
   - **Then** `fcitx5-diagnose` 输出包含 "nextalk" 插件
   - **And** 插件状态显示为已加载 (无错误)

## Tasks / Subtasks

> **并行提示**: Task 1-2 (目录创建+文件迁移) 可顺序执行，Task 3 (ydotool移除) 可与 Task 4 (CMake验证) 并行

- [x] **Task 0: 环境预检** (AC: #1) ~5min
  - [x] 0.1 验证 Fcitx5 >= 5.0.0: `fcitx5 --version`
  - [x] 0.2 验证开发包: `pkg-config --modversion fcitx5`
  - [x] 0.3 若缺失依赖，执行: `sudo apt install fcitx5 fcitx5-dev cmake build-essential`
  - **失败处理**: 若 Fcitx5 版本低于 5.0.0，需先升级系统或添加 PPA

- [x] **Task 1: 创建目标目录结构** (AC: #2) ~2min
  - [x] 1.1 创建 `/addons/fcitx5/src/` 目录: `mkdir -p addons/fcitx5/src`
  - [x] 1.2 验证目录结构符合架构文档

- [x] **Task 2: 迁移源码文件** (AC: #2) ~3min
  - [x] 2.1 复制 CMakeLists.txt: `cp <source>/CMakeLists.txt addons/fcitx5/`
  - [x] 2.2 复制 src/*.cpp, src/*.h, src/*.conf.in: `cp <source>/src/* addons/fcitx5/src/`

- [x] **Task 3: 移除 ydotool 回退逻辑** (AC: #4) ~10min
  - [x] 3.1 定位代码块: `grep -n "ydotool" addons/fcitx5/src/nextalk.cpp`
  - [x] 3.2 删除第 197-207 行 ydotool 相关代码
  - [x] 3.3 替换为简单警告日志 (见下方代码)
  - **验证**: `grep -c "ydotool" addons/fcitx5/src/nextalk.cpp` 应返回 0

- [x] **Task 4: 验证 CMake 配置** (AC: #3) ~5min
  - [x] 4.1 检查 `find_package(Fcitx5Core REQUIRED)`
  - [x] 4.2 检查 `find_package(Fcitx5Utils REQUIRED)`
  - [x] 4.3 确认 `set(CMAKE_CXX_STANDARD 17)`
  - [x] 4.4 确认安装路径使用 `FCITX_INSTALL_ADDONDIR`

- [x] **Task 5: 编译验证** (AC: #5) ~5min
  - [x] 5.1 创建 build 目录: `cd addons/fcitx5 && mkdir -p build && cd build`
  - [x] 5.2 执行 cmake: `cmake .. -DCMAKE_CXX_FLAGS="-Wall -Wextra"`
  - [x] 5.3 执行编译: `make -j$(nproc)`
  - [x] 5.4 验证产物: `ls -la nextalk.so`
  - **失败处理**: 查看 `build/CMakeFiles/CMakeError.log`

- [x] **Task 6: 功能验证** (AC: #6) ~5min
  - [x] 6.1 安装插件: `sudo cp nextalk.so /usr/lib/x86_64-linux-gnu/fcitx5/`
  - [x] 6.2 复制配置: `sudo cp nextalk.conf /usr/share/fcitx5/addon/`
  - [x] 6.3 重启 Fcitx5: `fcitx5 -r`
  - [x] 6.4 验证加载: Fcitx5 logs show "Loaded addon nextalk"
  - **预期输出**: 显示 nextalk 插件已加载，无错误

## Dev Notes

### 预检命令 (复制粘贴即用)

```bash
# 环境预检 - 所有命令应成功返回
fcitx5 --version                        # 期望: >= 5.0.0
pkg-config --modversion fcitx5          # 期望: >= 5.0.0
cmake --version                         # 期望: >= 3.16
```

### 源文件位置

| 文件 | 源路径 | 行数 |
|------|--------|------|
| CMakeLists.txt | `<source>/CMakeLists.txt` | 46 |
| nextalk.cpp | `<source>/src/nextalk.cpp` | 218 |
| nextalk.h | `<source>/src/nextalk.h` | 62 |
| nextalk.conf.in | `<source>/src/nextalk.conf.in` | 9 |

> `<source>` = `/mnt/disk0/project/newx/nextalk/nextalk_fcitx5/addons/fcitx5/`

### ydotool 移除

**定位**: `nextalk.cpp` 第 197-207 行，`commitText` 函数内

**删除整个 else 分支** (包含 ydotool fallback)，**替换为**:
```cpp
NEXTALK_WARN() << "No active input context available, text not committed: " << text;
return;
```

### 目标目录结构

```
addons/fcitx5/
├── CMakeLists.txt
└── src/
    ├── nextalk.cpp
    ├── nextalk.h
    └── nextalk.conf.in
```

### 关键架构约束

| 约束 | 要求 | 来源 |
|------|------|------|
| C++ 标准 | C++17 | docs/architecture.md |
| 依赖 | Fcitx5Core >= 5.0.0, Fcitx5Utils | docs/architecture.md#4.1 |
| Socket 路径 | `$XDG_RUNTIME_DIR/nextalk-fcitx5.sock` | docs/architecture.md#4.1 |
| 安全 | Socket 权限 0600 ✅ 已实现 | docs/architecture.md#6 |

### IPC 协议 (参考)

| Offset | Type | Size | Description |
|--------|------|------|-------------|
| 0 | uint32_le | 4 | Payload length |
| 4 | bytes | N | UTF-8 text |

### 编译命令 (完整流程)

```bash
cd addons/fcitx5
mkdir -p build && cd build
cmake .. -DCMAKE_CXX_FLAGS="-Wall -Wextra"
make -j$(nproc)
# 验证
ls -la nextalk.so
```

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| CMake 找不到 Fcitx5Core | `sudo apt install fcitx5-dev` |
| undefined reference 错误 | 检查 CMakeLists.txt 的 target_link_libraries |
| 编译警告 | 修复代码或添加 `-Wno-<warning>` (不推荐) |
| 插件未加载 | 检查 .conf 文件是否正确安装，重启 Fcitx5 |

**CMake 错误日志位置**: `build/CMakeFiles/CMakeError.log`

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- Environment check: Fcitx5 5.1.7, CMake 3.28.3, build-essential installed
- CMake configuration: Successfully found Fcitx5Core and Fcitx5Utils
- Build output: nextalk.so (95712 bytes) compiled with -Wall -Wextra, no warnings
- Plugin load logs: `Loaded addon nextalk`, socket at `/run/user/1000/nextalk-fcitx5.sock`

### Completion Notes List

1. **Environment Verified**: Fcitx5 5.1.7, fcitx5-dev 5.1.7, CMake 3.28.3 - all meet requirements
2. **Source Migration**: Copied CMakeLists.txt, nextalk.cpp, nextalk.h, nextalk.conf.in from original project
3. **ydotool Removal**: Removed fallback code (lines 197-207), replaced with warning log
4. **CMake Fix**: Added `set_target_properties(nextalk PROPERTIES PREFIX "")` to output `nextalk.so` instead of `libnextalk.so` (Fcitx5 requirement)
5. **Build Success**: Clean compilation with -Wall -Wextra, no warnings or errors
6. **Plugin Verified**: Installed to system paths, Fcitx5 loads addon successfully, socket listening

### Senior Developer Review (AI)

**Reviewer:** Dev Agent (Code Review Mode)  
**Date:** 2025-12-21  
**Outcome:** ✅ Approved (after fixes)

**Issues Found & Fixed:**
| Severity | Issue | Resolution |
|----------|-------|------------|
| CRITICAL | Story 文档 `libnextalk.so` 应为 `nextalk.so` | ✅ 已修正 |
| MEDIUM | Socket 缺少 chmod 0600 权限设置 | ✅ 已添加到 `socketListenerLoop()` |
| MEDIUM | 缺少 `.gitignore` 文件 | ✅ 已创建 |
| MEDIUM | Git 仓库未初始化 | ✅ 已初始化 |
| MEDIUM | `recv()` 缺少 EINTR 处理 | ✅ 已添加重试循环 |
| LOW | 魔法数字 `1024*1024` | ✅ 改为 `MAX_MESSAGE_SIZE` 常量 |

**Code Quality:** 重新编译成功，无警告

### Change Log

- 2025-12-21: Code Review - Fixed socket permissions, EINTR handling, added .gitignore, init git repo
- 2025-12-21: Initial implementation - Migrated Fcitx5 plugin, removed ydotool fallback, verified build and load

### File List

**Created/Modified Files:**
- `addons/fcitx5/CMakeLists.txt` (modified: added PREFIX property)
- `addons/fcitx5/src/nextalk.cpp` (modified: removed ydotool, added chmod 0600, EINTR handling, MAX_MESSAGE_SIZE)
- `addons/fcitx5/src/nextalk.h` (copied from source)
- `addons/fcitx5/src/nextalk.conf.in` (copied from source)
- `addons/fcitx5/build/nextalk.so` (generated)
- `addons/fcitx5/build/nextalk.conf` (generated)
- `.gitignore` (created: build artifacts, IDE files, Flutter exclusions)

---
*References: docs/architecture.md#2.2, docs/architecture.md#4.1, docs/prd.md#2.1 (FR4), _bmad-output/epics.md#Story-1.1*
