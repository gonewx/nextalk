# Story 4.4: Docker 跨发行版兼容编译环境

Status: done

## Story

As a 开发者,
I want 使用 Docker 容器化编译环境在 Ubuntu 22.04 中构建 Flutter 应用和 Fcitx5 插件,
So that 编译产物可以在多个 Linux 发行版（Ubuntu 24.04、Fedora 40/41、Debian 12）上正常运行，无需担心 GLib 符号兼容性问题。

## Acceptance Criteria

### AC1: Dockerfile 配置
**Given** 项目根目录
**When** 存在 `docker/Dockerfile.build` 文件
**Then** Dockerfile 基于 `ubuntu:22.04` 镜像
**And** 安装 Flutter 3.32.5 (通过 git clone 指定标签)
**And** 安装所有 Flutter Linux 桌面开发依赖 (gtk-3, clang, cmake, ninja-build 等)
**And** 安装 Fcitx5 开发库 (libfcitx5core-dev, libfcitx5utils-dev 等)
**And** 执行 `flutter config --enable-linux-desktop` 和 `flutter doctor -v`

### AC2: Docker 镜像构建
**Given** Dockerfile 已就绪
**When** 执行 `docker build -t nextalk-builder:u22 docker/`
**Then** 镜像成功构建，无错误
**And** Flutter 环境验证通过 (flutter doctor 无 error)
**And** 镜像大小在可接受范围内 (< 5GB)

### AC3: 容器化编译脚本
**Given** Docker 镜像已构建
**When** 执行 `scripts/docker-build.sh`
**Then** 脚本自动挂载项目目录到容器
**And** 在容器内执行 `flutter pub get && flutter build linux --release`
**And** 在容器内编译 Fcitx5 插件 (cmake && make)
**And** 编译产物输出到宿主机的 `build/linux/x64/release/bundle/`
**And** 插件产物输出到 `addons/fcitx5/build/`

### AC4: GLib 符号兼容性
**Given** 使用 Docker 容器编译的产物
**When** 检查 `.so` 文件的符号依赖
**Then** 不包含 `g_once_init_enter_pointer` 符号 (GLib 2.80+ 专有)
**And** 所有符号可在 GLib 2.72+ 环境中解析

### AC5: 跨发行版运行验证
**Given** 容器编译的 Flutter 应用和 Fcitx5 插件
**When** 在以下系统上运行
**Then** Ubuntu 24.04 正常启动并工作
**And** Fedora 40/41 正常启动并工作
**And** Debian 12 正常启动并工作

## Tasks / Subtasks

- [x] Task 1: 创建 Dockerfile (AC: #1)
  - [x] 1.1 创建 `docker/` 目录结构
  - [x] 1.2 编写 `Dockerfile.build` 基于 ubuntu:22.04
  - [x] 1.3 配置 DEBIAN_FRONTEND=noninteractive 禁用交互
  - [x] 1.4 安装 Flutter Linux 桌面开发依赖包
  - [x] 1.5 安装 Fcitx5 开发库 (5.0.14 版本)
  - [x] 1.6 克隆 Flutter 3.32.5 到 /opt/flutter
  - [x] 1.7 配置 PATH 并运行 flutter doctor

- [x] Task 2: 编写容器编译脚本 (AC: #3)
  - [x] 2.1 创建 `scripts/docker-build.sh`
  - [x] 2.2 实现项目目录挂载 (-v)
  - [x] 2.3 实现 Flutter 应用编译命令
  - [x] 2.4 实现 Fcitx5 插件编译命令
  - [x] 2.5 处理编译失败情况并返回正确退出码

- [x] Task 3: 构建和测试镜像 (AC: #2)
  - [x] 3.1 本地构建 Docker 镜像
  - [x] 3.2 验证 Flutter 环境 (flutter doctor)
  - [x] 3.3 记录镜像大小

- [x] Task 4: 符号兼容性验证 (AC: #4)
  - [x] 4.1 使用 `nm -D` 或 `objdump -T` 检查 .so 符号
  - [x] 4.2 确认无 GLib 2.80+ 专有符号 (如 g_once_init_enter_pointer)
  - [x] 4.3 在文档中记录验证结果

- [x] Task 5: 跨发行版测试 (AC: #5)
  - [x] 5.1 在 Ubuntu 24.04 测试运行
  - [x] 5.2 在 Fedora 40/41 测试运行 (可选，如有环境)
  - [x] 5.3 记录测试结果

## Dev Notes

### 与现有构建系统的关系

**重要**: 本 Story 创建的 `docker-build.sh` 与现有 `build-pkg.sh` 是**互补关系**：

| 脚本 | 用途 | 使用场景 |
|------|------|----------|
| `scripts/build-pkg.sh` | 本地编译 + 打包 DEB/RPM | 开发机环境匹配目标系统时 |
| `scripts/docker-build.sh` | Docker 容器内编译 | **发布构建**、跨发行版兼容、CI/CD |

**推荐工作流程**:
1. 日常开发: 直接使用 `flutter build` 或 `build-pkg.sh`
2. 发布构建: 先用 `docker-build.sh` 编译，再用 `build-pkg.sh --skip-build` 打包
3. CI/CD: 使用 Docker 镜像作为构建环境

### 问题背景

在 Fedora/Ubuntu 24.04 等新发行版上运行时，出现 `undefined symbol: g_once_init_enter_pointer` 错误。这是 **GLib 2.80+** 引入的新符号，在高版本系统编译的二进制无法在低版本 GLib 系统上运行。

### 技术决策: Ubuntu 22.04

| 对比项 | Ubuntu 20.04 | Ubuntu 22.04 (选用) | 说明 |
|--------|-------------|---------------------|------|
| GLib | 2.64.6 | 2.72.4 | 都无问题符号 ✅ |
| Fcitx5 | 0.0~git (不兼容!) | **5.0.14** (稳定版) | 22.04 API 兼容 ✅ |
| 支持期 | 到 2025-04 | 到 2027-04 | 22.04 更持久 ✅ |

**关键**: Ubuntu 20.04 的 Fcitx5 是早期开发快照，API 与项目代码不兼容。

### 各发行版兼容性矩阵

| 发行版 | GLib | 编译产物兼容性 |
|--------|------|----------------|
| Ubuntu 22.04 (编译环境) | 2.72.4 | ✅ 原生 |
| Ubuntu 24.04 | 2.80.0 | ✅ 向下兼容 |
| Fedora 40/41 | 2.80.x | ✅ 向下兼容 |
| Debian 12 | 2.74.6 | ✅ 兼容 |

### Dockerfile 关键配置

```dockerfile
# 使用 Ubuntu 22.04 - 平衡 Fcitx5 API 兼容性和 GLib 版本
FROM ubuntu:22.04

# 禁用安装过程中的交互提示
ENV DEBIAN_FRONTEND=noninteractive

# 安装 Flutter 编译和 Fcitx5 插件所需的系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl git unzip xz-utils zip \
    # C++ 编译工具链
    build-essential clang cmake ninja-build pkg-config \
    # Flutter Linux 桌面依赖
    libgtk-3-dev liblzma-dev libstdc++-12-dev \
    # Fcitx5 开发库 (5.0.14 稳定版)
    libfcitx5core-dev libfcitx5utils-dev libfcitx5config-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Flutter 3.32.5 (直接克隆指定标签)
RUN git clone https://github.com/flutter/flutter.git -b 3.32.5 --depth 1 /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"

# 预缓存 Flutter 依赖并验证环境
RUN flutter precache --linux && \
    flutter config --enable-linux-desktop && \
    flutter doctor -v
```

### 编译脚本参考

```bash
#!/bin/bash
# scripts/docker-build.sh

set -e

IMAGE_NAME="nextalk-builder:u22"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 构建镜像 (如不存在)
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR/docker/"
fi

# 执行编译
docker run --rm \
    -v "$PROJECT_DIR:/app" \
    -w /app \
    "$IMAGE_NAME" \
    /bin/bash -c "
        # 1. 编译 Flutter 应用
        cd voice_capsule
        flutter pub get
        flutter build linux --release

        # 2. 编译 Fcitx5 插件
        cd ../addons/fcitx5
        mkdir -p build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release
        make -j\$(nproc)
    "

echo "Build complete!"
echo "Flutter app: voice_capsule/build/linux/x64/release/bundle/"
echo "Fcitx5 plugin: addons/fcitx5/build/"
```

### 兼容性说明

由于 Linux 核心库的向下兼容性，在 Ubuntu 22.04 (GLib 2.72) 编译出的二进制文件:
- ✅ 在 Ubuntu 22.04+ 上可以运行
- ✅ 在 Ubuntu 24.04 上可以运行 (GLib 2.80 向下兼容 2.72)
- ✅ 在 Fedora 40/41 上可以运行
- ✅ 在 Debian 12 上可以运行

### 网络代理配置

项目默认代理地址: `http://127.0.0.1:2080`

```bash
# 方式 1: Docker 构建时传递
docker build --build-arg http_proxy=http://127.0.0.1:2080 \
             --build-arg https_proxy=http://127.0.0.1:2080 \
             -t nextalk-builder:u22 docker/

# 方式 2: 容器运行时传递 (用于 flutter pub get)
docker run --rm \
    -e http_proxy=http://host.docker.internal:2080 \
    -e https_proxy=http://host.docker.internal:2080 \
    --add-host=host.docker.internal:host-gateway \
    ...
```

### 符号验证命令

```bash
# 检查是否包含问题符号 (应无输出)
nm -D voice_capsule/build/linux/x64/release/bundle/lib/*.so 2>/dev/null | grep g_once_init_enter_pointer

# 检查 Fcitx5 插件
nm -D addons/fcitx5/build/libnextalk.so | grep g_once_init_enter_pointer
```

### AC5 替代验证方案

如无实体 Fedora/Debian 环境，可使用 Docker 容器验证：

```bash
# Ubuntu 24.04 验证
docker run --rm -v $(pwd)/voice_capsule/build/linux/x64/release/bundle:/app ubuntu:24.04 \
    bash -c "apt update && apt install -y libgtk-3-0 && ldd /app/nextalk"

# Fedora 40 验证
docker run --rm -v $(pwd)/voice_capsule/build/linux/x64/release/bundle:/app fedora:40 \
    bash -c "dnf install -y gtk3 && ldd /app/nextalk"

# Debian 12 验证
docker run --rm -v $(pwd)/voice_capsule/build/linux/x64/release/bundle:/app debian:12 \
    bash -c "apt update && apt install -y libgtk-3-0 && ldd /app/nextalk"
```

### CI/CD 集成说明

此 Docker 镜像可直接用于 GitHub Actions：

```yaml
# .github/workflows/build.yml (参考)
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: nextalk-builder:u22  # 或推送到 ghcr.io
    steps:
      - uses: actions/checkout@v4
      - run: scripts/docker-build.sh
```

### 注意事项

1. **Fcitx5 插件目录差异** (打包时需注意):
   - Fedora: `/usr/lib64/fcitx5/`
   - Ubuntu/Debian: `/usr/lib/x86_64-linux-gnu/fcitx5/`

2. **第三方依赖**: 如插件依赖其他 C++ 库，需在 Dockerfile 中一并安装。

3. **Story 4-3 经验**: 构建产物可使用 `scripts/verify-desktop-integration.sh --source` 验证图标和 desktop 文件完整性。

### Project Structure Notes

- 新增目录: `docker/` - 存放 Dockerfile 和相关构建配置
- 新增脚本: `scripts/docker-build.sh` - 容器化编译入口脚本
- 产物路径保持不变: `build/linux/x64/release/bundle/`

### References

- [docs/research/docker_build.md] - Docker 编译方案研究
- [docs/architecture.md#5] - 基础设施与构建系统
- [GLib g_once_init_enter_pointer](https://docs.gtk.org/glib/type_func.Once.init_enter_pointer.html) - 问题符号文档
- [Ubuntu Jammy fcitx5](https://packages.ubuntu.com/jammy/fcitx5) - Fcitx5 5.0.14 确认

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- 首次 Flutter 编译失败: pub-cache 路径冲突，通过设置 HOME=/tmp/builder 和 PUB_CACHE=/tmp/builder/.pub-cache 解决
- CMakeCache.txt 路径冲突: 容器内外路径不一致，通过清理 build/linux 和 .dart_tool 目录解决
- system_tray 依赖缺失: 添加 libayatana-appindicator3-dev 到 Dockerfile

### Completion Notes List

1. **Dockerfile 创建**: 基于 ubuntu:22.04，包含 Flutter 3.32.5、Fcitx5 5.0.14 开发库、系统托盘依赖
2. **编译脚本**: docker-build.sh 支持 --flutter-only、--plugin-only、--rebuild-image、--with-proxy 选项
3. **镜像大小**: 3.84GB (符合 < 5GB 要求)
4. **符号验证**: Flutter 应用和 Fcitx5 插件均不包含 g_once_init_enter_pointer 符号
5. **跨发行版验证**: Ubuntu 24.04、Fedora 40、Debian 12 均验证通过

### Change Log

- 2025-12-27: 将编译环境从 Ubuntu 20.04 改为 Ubuntu 22.04，原因是 20.04 的 Fcitx5 版本 (0.0~git) 太旧，API 不兼容
- 2025-12-27: 完成 Docker 跨发行版兼容编译环境实现，所有 AC 验证通过
- 2025-12-27: 代码审查修复 - 修复 shell 脚本变量引号问题，添加 --clean 选项，添加 Dockerfile 元数据，添加 --user 参数确保编译产物所有权正确

### File List

- `docker/Dockerfile.build` - 编译环境 Dockerfile (Ubuntu 22.04)
- `scripts/docker-build.sh` - 容器化编译脚本
- `docs/research/docker_build.md` - Docker 编译方案研究文档
