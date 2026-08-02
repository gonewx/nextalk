#!/bin/bash
# check-cmake-cache.sh - 检测并清理路径不匹配的 CMake 缓存
#
# 背景: CMakeCache.txt 会记录配置时的绝对路径。宿主机编译记录 /mnt/.../项目,
#       Docker 容器内项目挂载在 /app, 两者交替编译时 CMake 会直接报错退出:
#         "The current CMakeCache.txt directory ... is different than ..."
# 用途: 编译前检查缓存路径, 不匹配则删除 build 目录, 触发重新配置。
#
# 用法: ./scripts/check-cmake-cache.sh <build_dir> [build_dir...]

set -u

for build_dir in "$@"; do
    cache="$build_dir/CMakeCache.txt"
    [ -f "$cache" ] || continue

    cached_dir=$(sed -n 's/^CMAKE_CACHEFILE_DIR:INTERNAL=//p' "$cache" | head -1)
    actual_dir=$(cd "$build_dir" && pwd)

    if [ -n "$cached_dir" ] && [ "$cached_dir" != "$actual_dir" ]; then
        echo "🧹 CMake 缓存路径不匹配, 清理 $build_dir"
        echo "   缓存记录: $cached_dir"
        echo "   当前路径: $actual_dir"
        rm -rf "$build_dir"
    fi
done
