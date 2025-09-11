#!/usr/bin/env python
"""
NexTalk 构建脚本
使用 PyInstaller 创建独立的可执行文件
"""

import os
import sys
import shutil
import platform
import subprocess
from pathlib import Path
import argparse
import json

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent.resolve()
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
SPEC_DIR = ROOT_DIR / "specs"

# 平台特定配置
PLATFORM = platform.system().lower()
ARCH = platform.machine().lower()

def check_requirements():
    """检查构建依赖"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} 已安装")
    except ImportError:
        print("✗ PyInstaller 未安装")
        print("  请运行: pip install pyinstaller")
        return False
    
    # 检查其他必要的依赖
    required_modules = [
        "websockets",
        "PyYAML",
        "pynput",
        "pyautogui",
        "pyperclip",
        "sounddevice",
        "numpy",
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"✗ 缺少依赖: {', '.join(missing)}")
        print(f"  请运行: pip install {' '.join(missing)}")
        return False
    
    print("✓ 所有依赖已安装")
    return True

def clean_build():
    """清理之前的构建文件"""
    print("清理旧的构建文件...")
    
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"  已删除: {BUILD_DIR}")
    
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print(f"  已删除: {DIST_DIR}")
    
    # 清理 .spec 文件
    for spec_file in ROOT_DIR.glob("*.spec"):
        spec_file.unlink()
        print(f"  已删除: {spec_file}")

def create_spec_file(mode="onefile", gui=False):
    """创建 PyInstaller spec 文件"""
    print("创建 spec 文件...")
    
    # 确保 specs 目录存在
    SPEC_DIR.mkdir(exist_ok=True)
    
    # 主入口文件
    entry_point = ROOT_DIR / "nextalk" / "main.py"
    
    # 收集数据文件
    datas = [
        (str(ROOT_DIR / "config" / "nextalk.yaml"), "config"),
        (str(ROOT_DIR / "ssl_key"), "ssl_key"),
    ]
    
    # 收集隐式导入
    hidden_imports = [
        "websockets",
        "yaml",
        "pynput.keyboard",
        "pynput.mouse",
        "pyautogui",
        "pyperclip",
        "sounddevice",
        "numpy",
    ]
    
    # 如果包含 GUI，添加 PyQt6
    if gui:
        hidden_imports.extend([
            "PyQt6",
            "PyQt6.QtCore",
            "PyQt6.QtGui",
            "PyQt6.QtWidgets",
        ])
    
    # 平台特定的配置
    if PLATFORM == "windows":
        icon_path = ROOT_DIR / "nextalk" / "ui" / "assets" / "nextalk.ico"
        console = not gui
    elif PLATFORM == "darwin":  # macOS
        icon_path = ROOT_DIR / "nextalk" / "ui" / "assets" / "nextalk.icns"
        console = False
    else:  # Linux
        icon_path = ROOT_DIR / "nextalk" / "ui" / "assets" / "nextalk.png"
        console = not gui
    
    # 生成 spec 内容
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['{entry_point}'],
    pathex=['{ROOT_DIR}'],
    binaries=[],
    datas={datas},
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

"""

    if mode == "onefile":
        spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='nextalk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon_path if icon_path.exists() else ""}',
)
"""
    else:  # onedir
        spec_content += f"""
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='nextalk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{icon_path if icon_path.exists() else ""}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='nextalk',
)
"""

    # 如果是 macOS，添加 app bundle 配置
    if PLATFORM == "darwin" and gui:
        spec_content += f"""
app = BUNDLE(
    {'exe' if mode == 'onefile' else 'coll'},
    name='NexTalk.app',
    icon='{icon_path if icon_path.exists() else ""}',
    bundle_identifier='dev.nextalk.app',
    version='0.1.0',
    info_plist={{
        'NSHighResolutionCapable': 'True',
        'NSRequiresAquaSystemAppearance': 'False',
        'LSUIElement': '1',  # 隐藏 Dock 图标，只显示托盘图标
    }},
)
"""

    spec_file = SPEC_DIR / f"nextalk_{PLATFORM}_{mode}.spec"
    spec_file.write_text(spec_content.strip())
    print(f"  已创建: {spec_file}")
    
    return spec_file

def build_executable(spec_file, clean=True):
    """使用 PyInstaller 构建可执行文件"""
    print(f"构建可执行文件...")
    print(f"  使用 spec: {spec_file}")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean" if clean else "",
        str(spec_file)
    ]
    
    # 移除空字符串参数
    cmd = [arg for arg in cmd if arg]
    
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 构建成功")
            
            # 显示输出文件位置
            if (DIST_DIR / "nextalk").exists():
                print(f"  输出目录: {DIST_DIR / 'nextalk'}")
            elif (DIST_DIR / "nextalk.exe").exists():
                print(f"  输出文件: {DIST_DIR / 'nextalk.exe'}")
            elif (DIST_DIR / "nextalk").exists():
                print(f"  输出文件: {DIST_DIR / 'nextalk'}")
            
            return True
        else:
            print("✗ 构建失败")
            print(f"  错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 构建过程出错: {e}")
        return False

def create_installer_config():
    """创建安装器配置文件"""
    print("创建安装器配置...")
    
    installer_config = {
        "name": "NexTalk",
        "version": "0.1.0",
        "description": "个人轻量级实时语音识别与输入系统",
        "author": "NexTalk Team",
        "url": "https://nextalk.dev",
        "license": "MIT",
        "platform": PLATFORM,
        "arch": ARCH,
        "install_dir": {
            "windows": "C:\\Program Files\\NexTalk",
            "darwin": "/Applications/NexTalk.app",
            "linux": "/opt/nextalk"
        }.get(PLATFORM, "/opt/nextalk"),
        "shortcuts": {
            "desktop": True,
            "start_menu": True,
        },
        "auto_start": False,
        "file_associations": [],
    }
    
    config_file = DIST_DIR / "installer.json"
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(installer_config, f, indent=2, ensure_ascii=False)
    
    print(f"  已创建: {config_file}")
    return config_file

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NexTalk 构建脚本")
    parser.add_argument(
        "--mode",
        choices=["onefile", "onedir"],
        default="onefile",
        help="打包模式：单文件或目录"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="包含 GUI 支持（PyQt6）"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理之前的构建文件"
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="创建安装器配置"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="跳过依赖检查"
    )
    
    args = parser.parse_args()
    
    print(f"NexTalk 构建脚本")
    print(f"平台: {PLATFORM} ({ARCH})")
    print(f"模式: {args.mode}")
    print(f"GUI: {'是' if args.gui else '否'}")
    print("-" * 50)
    
    # 检查依赖
    if not args.skip_check:
        if not check_requirements():
            print("\n请安装缺少的依赖后重试")
            return 1
    
    # 清理旧文件
    if args.clean:
        clean_build()
    
    # 创建 spec 文件
    spec_file = create_spec_file(mode=args.mode, gui=args.gui)
    
    # 构建可执行文件
    if not build_executable(spec_file, clean=args.clean):
        return 1
    
    # 创建安装器配置
    if args.installer:
        create_installer_config()
    
    print("\n构建完成！")
    print(f"输出目录: {DIST_DIR}")
    
    # 显示后续步骤
    print("\n后续步骤:")
    print("1. 测试生成的可执行文件")
    print("2. 使用 scripts/package.py 创建安装包")
    print("3. 分发给用户")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())