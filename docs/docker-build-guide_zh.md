# Docker 跨发行版编译指南

简体中文 | [English](docker-build-guide.md)

本文档介绍如何使用 Docker 容器化编译环境构建 Nextalk，确保编译产物可在多个 Linux 发行版上运行。

## 为什么使用 Docker 编译

在高版本系统（如 Ubuntu 24.04、Fedora 40+）上编译的二进制文件可能依赖新版 GLib 符号（如 `g_once_init_enter_pointer`），导致无法在旧版系统上运行。

Docker 编译环境基于 Ubuntu 22.04，产物兼容以下系统：

| 发行版 | 兼容性 |
|--------|--------|
| Ubuntu 22.04+ | ✅ |
| Ubuntu 24.04 | ✅ |
| Fedora 40/41 | ✅ |
| Debian 12 | ✅ |

## 前置条件

- Docker 已安装并运行
- 约 4GB 磁盘空间（用于 Docker 镜像）

验证 Docker 是否可用：

```bash
docker info
```

## 快速开始

### 编译全部组件

```bash
./scripts/docker-build.sh
```

首次运行会自动构建 Docker 镜像，后续运行直接使用缓存镜像。

### 编译产物路径

| 组件 | 路径 |
|------|------|
| Flutter 应用 | `voice_capsule/build/linux/x64/release/bundle/` |
| Fcitx5 插件 | `addons/fcitx5/build/` |

## 命令选项

```bash
./scripts/docker-build.sh [选项]
```

| 选项 | 说明 |
|------|------|
| `--flutter-only` | 只编译 Flutter 应用 |
| `--plugin-only` | 只编译 Fcitx5 插件 |
| `--clean` | 清理缓存后全量编译 |
| `--rebuild-image` | 强制重建 Docker 镜像 |
| `--with-proxy` | 使用代理（`http://host.docker.internal:2080`） |
| `-h, --help` | 显示帮助信息 |

## 常用场景

### 日常开发（增量编译）

```bash
./scripts/docker-build.sh
```

默认增量编译，速度较快。

### 发布构建（全量编译）

```bash
./scripts/docker-build.sh --clean
```

清理所有缓存后重新编译，确保产物干净。

### 只编译 Flutter 应用

```bash
./scripts/docker-build.sh --flutter-only
```

### 只编译 Fcitx5 插件

```bash
./scripts/docker-build.sh --plugin-only
```

### 网络环境需要代理

```bash
./scripts/docker-build.sh --with-proxy
```

代理地址：`http://host.docker.internal:2080`

### 更新编译环境

当 Dockerfile 有变更时，重建镜像：

```bash
./scripts/docker-build.sh --rebuild-image
```

## 与本地编译的关系

| 脚本 | 用途 | 使用场景 |
|------|------|----------|
| `scripts/docker-build.sh` | Docker 容器内编译 | **发布构建**、跨发行版兼容、CI/CD |
| `scripts/build-pkg.sh` | 本地编译 + 打包 DEB/RPM | 开发机环境匹配目标系统时 |

**推荐工作流程：**

1. 日常开发：直接使用 `flutter build` 或本地编译
2. 发布构建：先用 `docker-build.sh` 编译，再用 `build-pkg.sh --skip-build` 打包

## 验证编译产物

检查产物是否包含问题符号（应无输出）：

```bash
# Flutter 应用
nm -D voice_capsule/build/linux/x64/release/bundle/lib/*.so 2>/dev/null | grep g_once_init_enter_pointer

# Fcitx5 插件
nm -D addons/fcitx5/build/libnextalk.so | grep g_once_init_enter_pointer
```

## 故障排除

### Docker daemon 未运行

```
错误: Docker daemon 未运行
```

**解决：** 启动 Docker 服务

```bash
sudo systemctl start docker
```

### 镜像构建失败（网络问题）

**解决：** 使用代理

```bash
./scripts/docker-build.sh --rebuild-image --with-proxy
```

### 编译产物权限问题

脚本使用 `--user $(id -u):$(id -g)` 运行容器，编译产物所有权应与当前用户一致。如仍有问题：

```bash
sudo chown -R $(id -u):$(id -g) voice_capsule/build addons/fcitx5/build
```

### 缓存导致编译问题

**解决：** 使用清理模式

```bash
./scripts/docker-build.sh --clean
```

## 技术细节

### Docker 镜像信息

- **镜像名称：** `nextalk-builder:u22`
- **基础镜像：** Ubuntu 22.04
- **Flutter 版本：** 3.32.5
- **Fcitx5 开发库：** 5.0.14
- **镜像大小：** 约 3.8GB

### 编译环境包含

- Flutter Linux 桌面开发工具链
- C++ 编译工具（clang, cmake, ninja-build）
- Fcitx5 开发库
- PortAudio 开发库（libportaudio2, portaudio19-dev）
- System Tray 依赖（libayatana-appindicator3）

### 打包的运行时库

编译产物 `bundle/lib/` 包含以下库，无需目标系统安装：

| 库 | 用途 |
|----|------|
| libsherpa-onnx-c-api.so | 语音识别引擎 |
| libonnxruntime.so | ONNX 推理运行时 |
| libportaudio.so.2 | 音频采集 |

---

**相关文档：**

- [docs/research/docker_build.md](research/docker_build.md) - Docker 编译方案研究
