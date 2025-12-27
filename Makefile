# Nextalk - 项目级 Makefile
# 离线语音输入应用 (Flutter + Fcitx5)

.PHONY: all build build-flutter build-addon test test-flutter clean clean-flutter clean-addon install install-addon install-addon-system uninstall-addon uninstall-addon-system run dev help sync-version docker-build docker-build-flutter docker-build-addon docker-rebuild docker-build-image docker-clean

# 默认目标
all: build

# ============================================================
# 构建目标
# ============================================================

# 构建所有组件
build: build-flutter build-addon

# 同步版本号 (从 version.yaml 到 pubspec.yaml)
sync-version:
	@APP_VER=$$(grep -E "^app_version:" version.yaml | sed 's/app_version:[[:space:]]*"\?\([0-9.]*\)"\?/\1/'); \
	APP_BUILD=$$(grep -E "^app_build:" version.yaml | sed 's/app_build:[[:space:]]*\([0-9]*\)/\1/'); \
	if [ -n "$$APP_VER" ] && [ -n "$$APP_BUILD" ]; then \
		sed -i "s/^version:.*/version: $$APP_VER+$$APP_BUILD/" voice_capsule/pubspec.yaml; \
		echo "📌 版本同步: $$APP_VER+$$APP_BUILD"; \
	fi

# 构建 Flutter 客户端 (Release)
build-flutter: sync-version
	@echo "🔨 构建 Flutter 客户端..."
	cd voice_capsule && flutter build linux --release

# 构建 Flutter 客户端 (Debug)
build-flutter-debug: sync-version
	@echo "🔨 构建 Flutter 客户端 (Debug)..."
	cd voice_capsule && flutter build linux --debug

# 构建 Fcitx5 插件
build-addon:
	@echo "🔨 构建 Fcitx5 插件..."
	mkdir -p addons/fcitx5/build
	cd addons/fcitx5/build && cmake .. && make -j$$(nproc)

# ============================================================
# 测试目标
# ============================================================

# 运行所有测试
test: test-flutter

# Flutter 单元测试
test-flutter:
	@echo "🧪 运行 Flutter 测试..."
	cd voice_capsule && flutter test

# Flutter 代码分析
analyze:
	@echo "🔍 运行 Flutter 代码分析..."
	cd voice_capsule && flutter analyze

# ============================================================
# 安装/卸载目标
# ============================================================

# 安装 Fcitx5 插件 (用户级，不需要 sudo)
install-addon: build-addon
	@echo "📦 安装 Fcitx5 插件..."
	./scripts/install_addon.sh

# 安装 Fcitx5 插件 (系统级，需要 sudo)
install-addon-system: build-addon
	@echo "📦 安装 Fcitx5 插件 (系统级)..."
	sudo ./scripts/install_addon.sh --system

# 卸载 Fcitx5 插件 (用户级)
uninstall-addon:
	@echo "🗑️ 卸载 Fcitx5 插件 (用户级)..."
	rm -f ~/.local/lib/fcitx5/libnextalk.so
	rm -f ~/.local/share/fcitx5/addon/nextalk.conf
	@echo "✅ Fcitx5 插件已卸载"

# 卸载 Fcitx5 插件 (系统级，需要 sudo)
uninstall-addon-system:
	@echo "🗑️ 卸载 Fcitx5 插件 (系统级)..."
	sudo rm -f $$(pkg-config --variable=libdir Fcitx5Core)/fcitx5/libnextalk.so
	sudo rm -f $$(pkg-config --variable=pkgdatadir fcitx5)/addon/nextalk.conf
	@echo "✅ Fcitx5 插件已卸载"

# ============================================================
# 运行目标
# ============================================================

# 运行 Flutter 应用 (开发模式)
run:
	@echo "🚀 运行 Flutter 应用..."
	cd voice_capsule && flutter run -d linux

# 开发模式 (热重载)
dev:
	@echo "🔥 开发模式运行..."
	cd voice_capsule && flutter run -d linux

# 运行构建产物
run-release: build-flutter
	@echo "🚀 运行 Release 版本..."
	./voice_capsule/build/linux/x64/release/bundle/nextalk

# ============================================================
# 清理目标
# ============================================================

# 清理所有构建产物
clean: clean-flutter clean-addon
	@echo "✅ 清理完成"

# 清理 Flutter 构建
clean-flutter:
	@echo "🧹 清理 Flutter 构建..."
	cd voice_capsule && flutter clean

# 清理 Fcitx5 插件构建
clean-addon:
	@echo "🧹 清理 Fcitx5 插件构建..."
	rm -rf addons/fcitx5/build

# ============================================================
# 打包目标
# ============================================================

# 构建发布包
package: build
	@echo "📦 构建发布包..."
	./scripts/build-pkg.sh

# ============================================================
# Docker 跨发行版编译 (推荐用于发布)
# ============================================================

# Docker 编译所有组件 (跨发行版兼容)
docker-build:
	@echo "🐳 Docker 容器内编译..."
	./scripts/docker-build.sh

# Docker 只编译 Flutter
docker-build-flutter:
	@echo "🐳 Docker 编译 Flutter..."
	./scripts/docker-build.sh --flutter-only

# Docker 只编译插件
docker-build-addon:
	@echo "🐳 Docker 编译 Fcitx5 插件..."
	./scripts/docker-build.sh --plugin-only

# Docker 重新完整编译 (清理缓存后编译)
docker-rebuild:
	@echo "🐳 Docker 重新完整编译..."
	./scripts/docker-build.sh --clean

# 构建/重建 Docker 镜像
docker-build-image:
	@echo "🐳 构建 Docker 镜像..."
	./scripts/docker-build.sh --rebuild-image

# 清理 Docker 编译产物的权限问题
docker-clean:
	@echo "🧹 清理 Docker 编译产物..."
	@if [ -d "voice_capsule/.dart_tool" ]; then \
		sudo rm -rf voice_capsule/.dart_tool 2>/dev/null || rm -rf voice_capsule/.dart_tool; \
	fi
	@if [ -d "voice_capsule/build" ]; then \
		sudo rm -rf voice_capsule/build 2>/dev/null || rm -rf voice_capsule/build; \
	fi
	@if [ -d "voice_capsule/linux/flutter/ephemeral" ]; then \
		sudo rm -rf voice_capsule/linux/flutter/ephemeral 2>/dev/null || rm -rf voice_capsule/linux/flutter/ephemeral; \
	fi
	@if [ -d "addons/fcitx5/build" ]; then \
		sudo rm -rf addons/fcitx5/build 2>/dev/null || rm -rf addons/fcitx5/build; \
	fi
	@echo "✅ Docker 编译产物已清理"

# ============================================================
# 依赖管理
# ============================================================

# 获取 Flutter 依赖
deps:
	@echo "📥 获取 Flutter 依赖..."
	cd voice_capsule && flutter pub get

# 更新 Flutter 依赖
deps-upgrade:
	@echo "📥 更新 Flutter 依赖..."
	cd voice_capsule && flutter pub upgrade

# ============================================================
# 帮助信息
# ============================================================

help:
	@echo "Nextalk Makefile 使用说明"
	@echo "========================="
	@echo ""
	@echo "构建命令:"
	@echo "  make build              - 构建所有组件"
	@echo "  make build-flutter      - 构建 Flutter 客户端 (Release)"
	@echo "  make build-flutter-debug- 构建 Flutter 客户端 (Debug)"
	@echo "  make build-addon        - 构建 Fcitx5 插件"
	@echo ""
	@echo "Docker 编译 (跨发行版兼容，推荐用于发布):"
	@echo "  make docker-build       - Docker 增量编译"
	@echo "  make docker-rebuild     - Docker 重新完整编译"
	@echo "  make docker-build-flutter - Docker 只编译 Flutter"
	@echo "  make docker-build-addon - Docker 只编译插件"
	@echo "  make docker-build-image - 构建/重建 Docker 镜像"
	@echo "  make docker-clean       - 清理 Docker 编译产物"
	@echo ""
	@echo "测试命令:"
	@echo "  make test               - 运行所有测试"
	@echo "  make test-flutter       - 运行 Flutter 测试"
	@echo "  make analyze            - 运行 Flutter 代码分析"
	@echo ""
	@echo "安装命令:"
	@echo "  make install-addon        - 安装 Fcitx5 插件 (用户级)"
	@echo "  make install-addon-system - 安装 Fcitx5 插件 (系统级，需 sudo)"
	@echo "  make uninstall-addon      - 卸载 Fcitx5 插件 (用户级)"
	@echo "  make uninstall-addon-system - 卸载 Fcitx5 插件 (系统级，需 sudo)"
	@echo ""
	@echo "运行命令:"
	@echo "  make run                - 开发模式运行"
	@echo "  make dev                - 开发模式运行 (同 run)"
	@echo "  make run-release        - 运行 Release 版本"
	@echo ""
	@echo "清理命令:"
	@echo "  make clean              - 清理所有构建产物"
	@echo "  make clean-flutter      - 清理 Flutter 构建"
	@echo "  make clean-addon        - 清理插件构建"
	@echo ""
	@echo "其他命令:"
	@echo "  make deps               - 获取 Flutter 依赖"
	@echo "  make deps-upgrade       - 更新 Flutter 依赖"
	@echo "  make package            - 构建发布包"
	@echo "  make help               - 显示此帮助信息"
