#!/bin/bash
# Nextalk 发布脚本
# 用法: ./scripts/release.sh [patch|minor|major] [提交信息]
# 示例: ./scripts/release.sh patch "修复冷启动问题"

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION_FILE="$PROJECT_ROOT/version.yaml"

# 读取当前版本
get_current_version() {
    grep -E '^app_version:' "$VERSION_FILE" | sed 's/app_version:[[:space:]]*"\?\([0-9.]*\)"\?/\1/'
}

# 计算新版本
bump_version() {
    local version=$1
    local type=$2

    IFS='.' read -r major minor patch <<< "$version"

    case $type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch|*)
            patch=$((patch + 1))
            ;;
    esac

    echo "$major.$minor.$patch"
}

# 更新 version.yaml
update_version_file() {
    local new_version=$1
    sed -i "s/^app_version:.*/app_version: \"$new_version\"/" "$VERSION_FILE"
}

# 主流程
main() {
    cd "$PROJECT_ROOT"

    # 参数解析
    BUMP_TYPE="${1:-patch}"
    COMMIT_MSG="$2"

    # 验证参数
    if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
        echo -e "${RED}错误: 版本类型必须是 patch, minor 或 major${NC}"
        echo "用法: $0 [patch|minor|major] [提交信息]"
        exit 1
    fi

    # 检查工作区是否干净
    if [[ -n $(git status --porcelain) ]]; then
        echo -e "${YELLOW}警告: 工作区有未提交的更改${NC}"
        git status --short
        echo ""
        read -p "是否继续? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # 获取版本信息
    CURRENT_VERSION=$(get_current_version)
    NEW_VERSION=$(bump_version "$CURRENT_VERSION" "$BUMP_TYPE")

    echo -e "${GREEN}=== Nextalk 发布 ===${NC}"
    echo "当前版本: v$CURRENT_VERSION"
    echo "新版本:   v$NEW_VERSION"
    echo "类型:     $BUMP_TYPE"
    echo ""

    # 确认发布
    read -p "确认发布 v$NEW_VERSION? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消"
        exit 0
    fi

    # 1. 更新版本文件
    echo -e "\n${YELLOW}[1/4] 更新版本号...${NC}"
    update_version_file "$NEW_VERSION"

    # 2. 提交更改
    echo -e "${YELLOW}[2/4] 提交更改...${NC}"
    git add -A

    if [[ -n "$COMMIT_MSG" ]]; then
        git commit -m "chore: 版本升级至 v$NEW_VERSION

- $COMMIT_MSG"
    else
        git commit -m "chore: 版本升级至 v$NEW_VERSION"
    fi

    # 3. 推送代码
    echo -e "${YELLOW}[3/4] 推送代码...${NC}"
    git push origin main

    # 4. 创建并推送 tag
    echo -e "${YELLOW}[4/4] 创建 tag 并触发 CI...${NC}"
    git tag "v$NEW_VERSION"
    git push origin "v$NEW_VERSION"

    echo -e "\n${GREEN}✅ 发布成功!${NC}"
    echo "版本: v$NEW_VERSION"
    echo "查看 CI: https://github.com/gonewx/nextalk/actions"
}

main "$@"
