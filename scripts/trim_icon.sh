#!/bin/bash
# 去除图片周围留白的脚本
# 使用 ImageMagick 的 trim 功能

set -e

# 默认值
INPUT_FILE=""
OUTPUT_FILE=""
FUZZ="1%"  # 颜色容差，允许轻微的颜色差异

usage() {
    echo "用法: $0 -i <输入文件> [-o <输出文件>] [-f <容差>]"
    echo ""
    echo "选项:"
    echo "  -i  输入图片文件路径 (必需)"
    echo "  -o  输出图片文件路径 (默认: 覆盖原文件)"
    echo "  -f  颜色容差百分比 (默认: 1%)"
    echo ""
    echo "示例:"
    echo "  $0 -i icon.png                    # 直接修改原文件"
    echo "  $0 -i icon.png -o icon_trimmed.png # 保存到新文件"
    echo "  $0 -i icon.png -f 5%              # 使用5%的颜色容差"
    exit 1
}

# 解析参数
while getopts "i:o:f:h" opt; do
    case $opt in
        i) INPUT_FILE="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        f) FUZZ="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# 检查必需参数
if [ -z "$INPUT_FILE" ]; then
    echo "错误: 必须指定输入文件"
    usage
fi

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 文件不存在: $INPUT_FILE"
    exit 1
fi

# 检查 ImageMagick 是否安装
if ! command -v convert &> /dev/null; then
    echo "错误: 需要安装 ImageMagick"
    echo "Ubuntu/Debian: sudo apt install imagemagick"
    echo "Fedora: sudo dnf install ImageMagick"
    echo "Arch: sudo pacman -S imagemagick"
    exit 1
fi

# 如果没有指定输出文件，则覆盖原文件
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="$INPUT_FILE"
fi

# 获取处理前的尺寸
BEFORE_SIZE=$(identify -format "%wx%h" "$INPUT_FILE")

# 执行裁剪
echo "正在处理: $INPUT_FILE"
echo "颜色容差: $FUZZ"

convert "$INPUT_FILE" -fuzz "$FUZZ" -trim +repage "$OUTPUT_FILE"

# 调整图片尺寸为 128x128
# convert "$INPUT_FILE" -resize 128x128 "$OUTPUT_FILE"

# 获取处理后的尺寸
AFTER_SIZE=$(identify -format "%wx%h" "$OUTPUT_FILE")

echo "处理完成!"
echo "  处理前尺寸: $BEFORE_SIZE"
echo "  处理后尺寸: $AFTER_SIZE"
echo "  输出文件: $OUTPUT_FILE"
