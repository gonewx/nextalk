# Docker Cross-Distribution Build Guide

[简体中文](docker-build-guide_zh.md) | English

This document describes how to use Docker containerized build environment to build Nextalk, ensuring build artifacts run on multiple Linux distributions.

## Why Use Docker Build

Binaries compiled on newer systems (like Ubuntu 24.04, Fedora 40+) may depend on new GLib symbols (like `g_once_init_enter_pointer`), preventing them from running on older systems.

Docker build environment is based on Ubuntu 22.04, artifacts compatible with:

| Distribution | Compatibility |
|--------------|---------------|
| Ubuntu 22.04+ | ✅ |
| Ubuntu 24.04 | ✅ |
| Fedora 40/41 | ✅ |
| Debian 12 | ✅ |

## Prerequisites

- Docker installed and running
- About 4GB disk space (for Docker image)

Verify Docker is available:

```bash
docker info
```

## Quick Start

### Build All Components

```bash
./scripts/docker-build.sh
```

First run will automatically build Docker image, subsequent runs use cached image.

### Build Artifact Paths

| Component | Path |
|-----------|------|
| Flutter App | `voice_capsule/build/linux/x64/release/bundle/` |
| Fcitx5 Plugin | `addons/fcitx5/build/` |

## Command Options

```bash
./scripts/docker-build.sh [options]
```

| Option | Description |
|--------|-------------|
| `--flutter-only` | Build Flutter app only |
| `--plugin-only` | Build Fcitx5 plugin only |
| `--clean` | Clean cache before full build |
| `--rebuild-image` | Force rebuild Docker image |
| `--with-proxy` | Use proxy (`http://host.docker.internal:2080`) |
| `-h, --help` | Show help message |

## Common Scenarios

### Daily Development (Incremental Build)

```bash
./scripts/docker-build.sh
```

Default incremental build, faster.

### Release Build (Full Build)

```bash
./scripts/docker-build.sh --clean
```

Clean all cache before rebuilding, ensures clean artifacts.

### Flutter App Only

```bash
./scripts/docker-build.sh --flutter-only
```

### Fcitx5 Plugin Only

```bash
./scripts/docker-build.sh --plugin-only
```

### Network Requires Proxy

```bash
./scripts/docker-build.sh --with-proxy
```

Proxy address: `http://host.docker.internal:2080`

### Update Build Environment

When Dockerfile changes, rebuild image:

```bash
./scripts/docker-build.sh --rebuild-image
```

## Relationship with Local Build

| Script | Purpose | Use Case |
|--------|---------|----------|
| `scripts/docker-build.sh` | Build in Docker container | **Release builds**, cross-distro compatibility, CI/CD |
| `scripts/build-pkg.sh` | Local build + DEB/RPM packaging | When dev machine matches target system |

**Recommended Workflow:**

1. Daily development: Use `flutter build` directly or local build
2. Release build: First use `docker-build.sh` to compile, then use `build-pkg.sh --skip-build` to package

## Verify Build Artifacts

Check if artifacts contain problematic symbols (should have no output):

```bash
# Flutter app
nm -D voice_capsule/build/linux/x64/release/bundle/lib/*.so 2>/dev/null | grep g_once_init_enter_pointer

# Fcitx5 plugin
nm -D addons/fcitx5/build/libnextalk.so | grep g_once_init_enter_pointer
```

## Troubleshooting

### Docker daemon not running

```
Error: Docker daemon not running
```

**Solution:** Start Docker service

```bash
sudo systemctl start docker
```

### Image build failed (network issues)

**Solution:** Use proxy

```bash
./scripts/docker-build.sh --rebuild-image --with-proxy
```

### Build artifact permission issues

Script runs container with `--user $(id -u):$(id -g)`, artifact ownership should match current user. If issues persist:

```bash
sudo chown -R $(id -u):$(id -g) voice_capsule/build addons/fcitx5/build
```

### Cache causing build issues

**Solution:** Use clean mode

```bash
./scripts/docker-build.sh --clean
```

## Technical Details

### Docker Image Info

- **Image Name:** `nextalk-builder:u22`
- **Base Image:** Ubuntu 22.04
- **Flutter Version:** 3.32.5
- **Fcitx5 Dev Library:** 5.0.14
- **Image Size:** ~3.8GB

### Build Environment Includes

- Flutter Linux desktop development toolchain
- C++ compilation tools (clang, cmake, ninja-build)
- Fcitx5 development libraries
- PortAudio development libraries (libportaudio2, portaudio19-dev)
- System Tray dependencies (libayatana-appindicator3)

### Bundled Runtime Libraries

Build artifact `bundle/lib/` includes these libraries, no target system installation needed:

| Library | Purpose |
|---------|---------|
| libsherpa-onnx-c-api.so | Speech recognition engine |
| libonnxruntime.so | ONNX inference runtime |
| libportaudio.so.2 | Audio capture |

---

**Related Documents:**

- [docs/research/docker_build.md](research/docker_build.md) - Docker build solution research
