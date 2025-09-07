# NexTalk Makefile
# 提供便捷的构建和打包命令

.PHONY: help install dev test build package clean release all

# 默认 Python 解释器
PYTHON := python3
PIP := $(PYTHON) -m pip
PLATFORM := $(shell $(PYTHON) -c "import platform; print(platform.system().lower())")
VERSION := 0.1.0

help:
	@echo "NexTalk 构建系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install       - 安装运行时依赖"
	@echo "  make dev          - 安装开发依赖"
	@echo "  make test         - 运行测试套件"
	@echo "  make build        - 构建可执行文件"
	@echo "  make package      - 创建分发包"
	@echo "  make clean        - 清理构建文件"
	@echo "  make release      - 完整发布流程"
	@echo "  make all          - 执行所有步骤"
	@echo ""
	@echo "高级选项:"
	@echo "  make build-gui    - 构建带 GUI 的版本"
	@echo "  make build-onedir - 构建目录版本"
	@echo "  make portable     - 创建便携版"
	@echo "  make installer    - 创建安装器"

install:
	@echo "安装运行时依赖..."
	$(PIP) install -r requirements.txt

dev: install
	@echo "安装开发依赖..."
	$(PIP) install -r requirements-build.txt
	$(PIP) install -e .[dev]

test:
	@echo "运行测试套件..."
	$(PYTHON) -m pytest tests/ -v --cov=nextalk --cov-report=html

test-quick:
	@echo "运行快速测试..."
	$(PYTHON) -m pytest tests/unit/ -v

test-integration:
	@echo "运行集成测试..."
	$(PYTHON) -m pytest tests/integration/ -v

lint:
	@echo "运行代码检查..."
	$(PYTHON) -m flake8 nextalk/
	$(PYTHON) -m mypy nextalk/
	$(PYTHON) -m black --check nextalk/

format:
	@echo "格式化代码..."
	$(PYTHON) -m black nextalk/

build:
	@echo "构建可执行文件 (单文件模式)..."
	$(PYTHON) scripts/build.py --mode onefile --clean

build-gui:
	@echo "构建带 GUI 的可执行文件..."
	$(PYTHON) scripts/build.py --mode onefile --gui --clean

build-onedir:
	@echo "构建目录版本..."
	$(PYTHON) scripts/build.py --mode onedir --clean

package: build
	@echo "创建分发包..."
	$(PYTHON) scripts/package.py --format all

portable: build
	@echo "创建便携版..."
	$(PYTHON) scripts/package.py --portable

installer: build
	@echo "创建安装器..."
	$(PYTHON) scripts/package.py --installer

release: clean test build package
	@echo "创建完整发布版..."
	$(PYTHON) scripts/package.py --all
	@echo "发布版本 $(VERSION) 创建完成！"

clean:
	@echo "清理构建文件..."
	rm -rf build/ dist/ releases/ temp_package/ *.spec
	rm -rf nextalk.egg-info/ .pytest_cache/ .coverage htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# 开发相关命令
run:
	@echo "运行开发版本..."
	$(PYTHON) -m nextalk

debug:
	@echo "调试模式运行..."
	$(PYTHON) -m nextalk --debug --verbose

# Docker 支持（可选）
docker-build:
	@echo "构建 Docker 镜像..."
	docker build -t nextalk:$(VERSION) .

docker-run:
	@echo "运行 Docker 容器..."
	docker run -it --rm \
		--device /dev/snd \
		-e PULSE_SERVER=unix:$${XDG_RUNTIME_DIR}/pulse/native \
		-v $${XDG_RUNTIME_DIR}/pulse/native:$${XDG_RUNTIME_DIR}/pulse/native \
		-v ~/.config/nextalk:/config \
		nextalk:$(VERSION)

# CI/CD 支持
ci-test:
	@echo "运行 CI 测试..."
	$(PYTHON) -m pytest tests/ --cov=nextalk --cov-report=xml

ci-build:
	@echo "CI 构建..."
	$(PYTHON) scripts/build.py --mode onefile --skip-check

# 文档生成（如需要）
docs:
	@echo "生成文档..."
	@echo "文档生成功能待实现"

# 版本管理
version:
	@echo "当前版本: $(VERSION)"
	@echo "平台: $(PLATFORM)"
	@$(PYTHON) --version

# 依赖检查
check-deps:
	@echo "检查依赖..."
	@$(PYTHON) -c "import websockets; print(f'✓ websockets {websockets.__version__}')" || echo "✗ websockets"
	@$(PYTHON) -c "import yaml; print('✓ PyYAML')" || echo "✗ PyYAML"
	@$(PYTHON) -c "import pynput; print(f'✓ pynput {pynput.__version__}')" || echo "✗ pynput"
	@$(PYTHON) -c "import pyautogui; print(f'✓ pyautogui {pyautogui.__version__}')" || echo "✗ pyautogui"
	@$(PYTHON) -c "import sounddevice; print(f'✓ sounddevice {sounddevice.__version__}')" || echo "✗ sounddevice"

# 安装 PyInstaller
install-pyinstaller:
	@echo "安装 PyInstaller..."
	$(PIP) install pyinstaller>=6.0.0

# 完整构建流程
all: clean install dev test build package
	@echo "完整构建完成！"

# 快速构建（跳过测试）
quick: clean install build
	@echo "快速构建完成！"

# 仅测试不构建
test-only: install dev test
	@echo "测试完成！"

.DEFAULT_GOAL := help