#!/bin/bash
# Story 2-1 验证脚本
set -e
cd "$(dirname "$0")/.."

echo "=== [1/6] 检查 libs/ 目录 ==="
test -f libs/libsherpa-onnx-c-api.so && echo "[✓] libsherpa-onnx-c-api.so" || { echo "[✗] 缺少 libsherpa-onnx-c-api.so"; exit 1; }
test -f libs/libonnxruntime.so && echo "[✓] libonnxruntime.so" || { echo "[✗] 缺少 libonnxruntime.so"; exit 1; }

echo "=== [2/6] 验证库依赖 ==="
if ldd libs/libsherpa-onnx-c-api.so | grep -q "not found"; then
  echo "[✗] libsherpa-onnx-c-api.so 有未满足的依赖"
  ldd libs/libsherpa-onnx-c-api.so | grep "not found"
  exit 1
fi
echo "[✓] 库依赖满足"

echo "=== [3/6] 检查系统 PortAudio ==="
dpkg -l libportaudio2 > /dev/null 2>&1 && echo "[✓] libportaudio2 已安装" || { echo "[✗] 请安装: sudo apt install libportaudio2"; exit 1; }

echo "=== [4/6] 执行 Flutter 构建 ==="
cd voice_capsule
flutter clean > /dev/null 2>&1
flutter build linux --release

echo "=== [5/6] 验证构建产物 ==="
BUNDLE="build/linux/x64/release/bundle"
test -f "$BUNDLE/voice_capsule" && echo "[✓] 可执行文件存在"
test -f "$BUNDLE/lib/libsherpa-onnx-c-api.so" && echo "[✓] libsherpa-onnx-c-api.so 已复制" || { echo "[✗] 库未复制到 bundle"; exit 1; }
test -f "$BUNDLE/lib/libonnxruntime.so" && echo "[✓] libonnxruntime.so 已复制" || { echo "[✗] 库未复制到 bundle"; exit 1; }

echo "=== [6/6] 验证 RPATH ==="
RPATH=$(readelf -d "$BUNDLE/voice_capsule" 2>/dev/null | grep -E "RUNPATH|RPATH" | grep -o '\$ORIGIN/lib' || true)
if [ -n "$RPATH" ]; then
  echo "[✓] RPATH 配置正确: \$ORIGIN/lib"
else
  echo "[✗] RPATH 配置错误"
  exit 1
fi

echo ""
echo "=== ✅ Story 2-1 验证通过 ==="
