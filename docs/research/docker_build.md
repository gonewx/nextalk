# Docker 跨发行版兼容编译方案

> ⚠️ **重要更新 (2025-12-27)**: 原方案使用 Ubuntu 20.04 存在问题，已修正为 Ubuntu 22.04。

## 问题背景

在 Ubuntu 24.04 / Fedora 40+ 等新发行版上运行时，出现如下错误：

```
undefined symbol: g_once_init_enter_pointer
```

**原因**: `g_once_init_enter_pointer` 是 **GLib 2.80** 引入的新符号。Ubuntu 24.04 自带 GLib 2.80，在该环境编译的二进制会依赖此符号，导致无法在旧版 GLib 系统上运行。

## 解决方案

在 Docker 中使用 **Ubuntu 22.04** 配合 Flutter 3.32.5 进行编译。

### 为什么是 Ubuntu 22.04 而非 20.04？

| 对比项 | Ubuntu 20.04 | Ubuntu 22.04 |
|--------|-------------|-------------|
| **GLib 版本** | 2.64.6 | 2.72.4 |
| **Fcitx5 版本** | 0.0~git (2020年开发版，API 不兼容!) | **5.0.14** (稳定版) ✅ |
| **官方支持** | 标准支持已结束 | 到 2027-04 ✅ |

**关键问题**: Ubuntu 20.04 的 Fcitx5 是早期开发快照，API 与当前项目代码不兼容。

## 实现流程

### 1. 编写 Dockerfile

创建 `docker/Dockerfile.build`:

```dockerfile
# 使用 Ubuntu 22.04 - 平衡 Fcitx5 API 兼容性和 GLib 版本
FROM ubuntu:22.04

# 镜像元数据
LABEL org.opencontainers.image.title="nextalk-builder"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.description="Nextalk 跨发行版编译环境"

# 禁用安装过程中的交互提示
ENV DEBIAN_FRONTEND=noninteractive

# 安装 Flutter 编译和 Fcitx5 插件所需的系统依赖
RUN apt-get update && apt-get install -y \
    # 基础工具
    curl git unzip xz-utils zip ca-certificates \
    # C++ 编译工具链
    build-essential clang cmake ninja-build pkg-config \
    # Flutter Linux 桌面依赖
    libgtk-3-dev liblzma-dev libstdc++-12-dev \
    # System Tray 依赖
    libayatana-appindicator3-dev \
    # Fcitx5 开发库 (5.0.14 稳定版)
    libfcitx5core-dev libfcitx5utils-dev libfcitx5config-dev \
    # PortAudio 开发库 (音频采集)
    libportaudio2 portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Flutter 3.32.5 (直接克隆指定标签)
RUN git clone https://github.com/flutter/flutter.git -b 3.32.5 --depth 1 /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
ENV PUB_CACHE="/opt/flutter/.pub-cache"

# 预缓存 Flutter 依赖并验证环境
RUN flutter precache --linux && \
    flutter config --enable-linux-desktop && \
    flutter doctor -v

# 设置工作目录
WORKDIR /app
```

### 2. 构建镜像

```bash
docker build -t nextalk-builder:u22 docker/
```

如需代理：

```bash
docker build --build-arg http_proxy=http://127.0.0.1:2080 \
             --build-arg https_proxy=http://127.0.0.1:2080 \
             -t nextalk-builder:u22 docker/
```

### 3. 执行编译

```bash
docker run --rm -v $(pwd):/app -w /app nextalk-builder:u22 /bin/bash -c "
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
```

## 技术原理

### GLib 版本对照表

| 发行版 | GLib 版本 | g_once_init_enter_pointer |
|--------|----------|---------------------------|
| Ubuntu 22.04 | 2.72.4 | ❌ 无此符号 |
| Ubuntu 24.04 | **2.80.0** | ✅ 有此符号 |
| Fedora 40/41 | **2.80.x** | ✅ 有此符号 |
| Debian 12 | 2.74.6 | ❌ 无此符号 |

### 兼容性说明

在 Ubuntu 22.04 (GLib 2.72) 编译出的二进制文件：
- ✅ 在 Ubuntu 22.04+ 上可以运行
- ✅ 在 Ubuntu 24.04 上可以运行 (GLib 2.80 向下兼容)
- ✅ 在 Fedora 40/41 上可以运行
- ✅ 在 Debian 12 上可以运行

### 验证符号

```bash
# 检查是否包含问题符号
nm -D build/linux/x64/release/bundle/lib/*.so | grep g_once_init_enter_pointer
# 应该无输出，表示不依赖此符号
```

## 注意事项

1. **Fcitx5 插件目录差异**:
   - Fedora: `/usr/lib64/fcitx5/`
   - Ubuntu/Debian: `/usr/lib/x86_64-linux-gnu/fcitx5/`

2. **第三方依赖**: 如果插件依赖其他 C++ 库，需在 Dockerfile 中一并安装。

## 参考资料

- [GLib g_once_init_enter_pointer 文档](https://docs.gtk.org/glib/type_func.Once.init_enter_pointer.html) - GLib 2.80 引入
- [Ubuntu Jammy fcitx5 包](https://packages.ubuntu.com/jammy/fcitx5) - Fcitx5 5.0.14
- [Ubuntu Focal glib2.0](https://launchpad.net/ubuntu/focal/+source/glib2.0) - GLib 版本确认
