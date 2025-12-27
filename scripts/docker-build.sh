#!/bin/bash
# docker-build.sh - 使用 Docker 容器编译 Nextalk (跨发行版兼容)
# Version: 1.0.0
# Date: 2025-12-27
#
# 用途: 在 Ubuntu 22.04 容器中编译，产物可在多个发行版上运行
# 使用: ./scripts/docker-build.sh [--rebuild-image] [--flutter-only] [--plugin-only] [--clean]
#
# 产物路径:
#   - Flutter 应用: voice_capsule/build/linux/x64/release/bundle/
#   - Fcitx5 插件: addons/fcitx5/build/

set -e

# 配置
IMAGE_NAME="nextalk-builder:u22"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --rebuild-image   强制重建 Docker 镜像"
    echo "  --flutter-only    只编译 Flutter 应用"
    echo "  --plugin-only     只编译 Fcitx5 插件"
    echo "  --with-proxy      使用代理 (http://host.docker.internal:2080)"
    echo "  --clean           清理缓存后编译 (默认增量编译)"
    echo "  -h, --help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 增量编译全部"
    echo "  $0 --clean            # 清理后全量编译"
    echo "  $0 --flutter-only     # 只编译 Flutter 应用"
    echo "  $0 --rebuild-image    # 重建镜像后编译"
}

# 解析参数
REBUILD_IMAGE=false
FLUTTER_ONLY=false
PLUGIN_ONLY=false
WITH_PROXY=false
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild-image)
            REBUILD_IMAGE=true
            shift
            ;;
        --flutter-only)
            FLUTTER_ONLY=true
            shift
            ;;
        --plugin-only)
            PLUGIN_ONLY=true
            shift
            ;;
        --with-proxy)
            WITH_PROXY=true
            shift
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 检查 Docker 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装或不在 PATH 中${NC}"
    exit 1
fi

# 检查 Docker daemon 是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误: Docker daemon 未运行${NC}"
    exit 1
fi

# 构建镜像 (如不存在或强制重建)
build_image() {
    if $REBUILD_IMAGE || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
        echo -e "${YELLOW}正在构建 Docker 镜像 $IMAGE_NAME ...${NC}"

        # 使用数组存储构建参数，避免 word splitting 问题
        local build_args=()
        if $WITH_PROXY; then
            build_args+=(--build-arg "http_proxy=http://host.docker.internal:2080")
            build_args+=(--build-arg "https_proxy=http://host.docker.internal:2080")
        fi

        if docker build "${build_args[@]}" -t "$IMAGE_NAME" -f "$PROJECT_DIR/docker/Dockerfile.build" "$PROJECT_DIR/docker/"; then
            echo -e "${GREEN}Docker 镜像构建成功${NC}"
        else
            echo -e "${RED}Docker 镜像构建失败${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}使用已存在的 Docker 镜像 $IMAGE_NAME${NC}"
    fi
}

# 准备 Docker run 参数 (存储到全局数组 DOCKER_RUN_ARGS)
prepare_docker_args() {
    # 使用全局数组存储参数，避免 word splitting 问题
    DOCKER_RUN_ARGS=(
        --rm
        -v "$PROJECT_DIR:/app"
        -w /app
        # 使用当前用户 ID 运行，确保编译产物所有权正确
        --user "$(id -u):$(id -g)"
        -e "HOME=/tmp/builder"
        # 显式指定 pub-cache 路径，覆盖 HOME 默认值
        -e "PUB_CACHE=/opt/flutter/.pub-cache"
    )

    if $WITH_PROXY; then
        DOCKER_RUN_ARGS+=(
            -e "http_proxy=http://host.docker.internal:2080"
            -e "https_proxy=http://host.docker.internal:2080"
            --add-host=host.docker.internal:host-gateway
        )
    fi
}

# 编译 Flutter 应用
build_flutter() {
    echo -e "${YELLOW}正在编译 Flutter 应用...${NC}"

    prepare_docker_args

    # 根据 --clean 选项决定是否清理缓存
    local clean_cmd=""
    if $CLEAN_BUILD; then
        clean_cmd="rm -rf .dart_tool build/linux && "
        echo -e "${YELLOW}  (清理模式: 将删除 .dart_tool 和 build/linux)${NC}"
    fi

    if docker run "${DOCKER_RUN_ARGS[@]}" "$IMAGE_NAME" /bin/bash -c "
        mkdir -p /tmp/builder && \
        git config --global --add safe.directory /opt/flutter && \
        cd voice_capsule && \
        rm -rf .dart_tool && \
        ${clean_cmd}flutter pub get && \
        flutter build linux --release
    "; then
        echo -e "${GREEN}Flutter 应用编译成功${NC}"
        echo "  产物路径: voice_capsule/build/linux/x64/release/bundle/"
    else
        echo -e "${RED}Flutter 应用编译失败${NC}"
        exit 1
    fi
}

# 编译 Fcitx5 插件
build_plugin() {
    echo -e "${YELLOW}正在编译 Fcitx5 插件...${NC}"

    prepare_docker_args

    # 根据 --clean 选项决定是否清理 build 目录
    local clean_cmd=""
    if $CLEAN_BUILD; then
        clean_cmd="rm -rf build && "
        echo -e "${YELLOW}  (清理模式: 将删除 build 目录)${NC}"
    fi

    if docker run "${DOCKER_RUN_ARGS[@]}" "$IMAGE_NAME" /bin/bash -c "
        cd addons/fcitx5 && \
        ${clean_cmd}mkdir -p build && cd build && \
        cmake .. -DCMAKE_BUILD_TYPE=Release && \
        make -j\$(nproc)
    "; then
        echo -e "${GREEN}Fcitx5 插件编译成功${NC}"
        echo "  产物路径: addons/fcitx5/build/"
    else
        echo -e "${RED}Fcitx5 插件编译失败${NC}"
        exit 1
    fi
}

# 主流程
main() {
    echo "========================================"
    echo "  Nextalk Docker 跨发行版编译"
    echo "========================================"
    echo ""

    # 构建镜像
    build_image

    # 执行编译
    if $FLUTTER_ONLY; then
        build_flutter
    elif $PLUGIN_ONLY; then
        build_plugin
    else
        build_flutter
        build_plugin
    fi

    echo ""
    echo "========================================"
    echo -e "${GREEN}编译完成!${NC}"
    echo "========================================"

    if ! $PLUGIN_ONLY; then
        echo "Flutter 应用: voice_capsule/build/linux/x64/release/bundle/"
    fi
    if ! $FLUTTER_ONLY; then
        echo "Fcitx5 插件:  addons/fcitx5/build/"
    fi
}

main
