#!/usr/bin/env python3
"""
IME诊断和测试工具 - 为开发和用户提供IME功能调试工具

提供IME状态诊断和兼容性检查，帮助排查IME相关问题。
"""

import sys
import os
import time
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from nextalk.output.ime_manager import IMEManager
    from nextalk.output.ime_base import IMEStatus, IMEInfo, CompositionState
    from nextalk.output.ime_exceptions import (
        IMEException, IMEErrorCode, get_user_friendly_message,
        get_ime_error_statistics
    )
    from nextalk.config.models import IMEConfig
    from nextalk.utils.system import get_system_info, check_system_requirements
    from nextalk.utils.logger import setup_logging
    NEXTALK_AVAILABLE = True
except ImportError as e:
    NEXTALK_AVAILABLE = False
    print(f"警告: 无法导入NexTalk模块: {e}")
    print("某些功能可能不可用")


class IMEDiagnosticTool:
    """IME诊断工具."""
    
    def __init__(self, verbose: bool = False):
        """
        初始化诊断工具.
        
        Args:
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.results = {}
        self.logger = self._setup_logger()
        self.ime_manager: Optional[IMEManager] = None
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        return logging.getLogger(__name__)
    
    async def run_full_diagnosis(self) -> Dict[str, Any]:
        """运行完整的IME诊断."""
        print("=== NexTalk IME 诊断工具 ===")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 系统信息检查
        print("📋 检查系统信息...")
        system_info = self._check_system_info()
        
        # IME可用性检查
        print("\n🔧 检查IME可用性...")
        ime_availability = await self._check_ime_availability()
        
        # IME功能测试
        print("\n⚡ 测试IME功能...")
        ime_functionality = await self._test_ime_functionality()
        
        # 权限检查
        print("\n🔐 检查权限设置...")
        permissions = await self._check_permissions()
        
        # 兼容性检查
        print("\n🔄 检查应用兼容性...")
        compatibility = await self._check_app_compatibility()
        
        # 汇总结果
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'system_info': system_info,
            'ime_availability': ime_availability,
            'ime_functionality': ime_functionality,
            'permissions': permissions,
            'app_compatibility': compatibility
        }
        
        print("\n📊 生成诊断报告...")
        self._generate_report()
        
        return self.results
    
    def _check_system_info(self) -> Dict[str, Any]:
        """检查系统信息."""
        try:
            if NEXTALK_AVAILABLE:
                system_info = get_system_info()
                requirements_ok = check_system_requirements()
            else:
                system_info = {
                    'platform_system': sys.platform,
                    'python_version': sys.version
                }
                requirements_ok = False
            
            print(f"  ✓ 操作系统: {system_info.get('platform_system', 'Unknown')}")
            print(f"  ✓ Python版本: {system_info.get('python_version', sys.version.split()[0])}")
            print(f"  {'✓' if requirements_ok else '✗'} 系统要求: {'满足' if requirements_ok else '不满足'}")
            
            return {
                'system_info': system_info,
                'requirements_met': requirements_ok,
                'supported_platform': sys.platform in ['win32', 'darwin', 'linux']
            }
        except Exception as e:
            print(f"  ✗ 系统检查失败: {e}")
            return {'error': str(e)}
    
    async def _check_ime_availability(self) -> Dict[str, Any]:
        """检查IME可用性."""
        if not NEXTALK_AVAILABLE:
            print("  ✗ NexTalk模块不可用")
            return {'available': False, 'error': 'NexTalk modules not available'}
        
        try:
            # 创建IME管理器
            ime_config = IMEConfig(
                enabled=True,
                debug_mode=True,
                auto_detect_ime=True
            )
            self.ime_manager = IMEManager(ime_config)
            
            # 尝试初始化
            success = await self.ime_manager.initialize()
            
            if success:
                print("  ✓ IME管理器初始化成功")
                
                # 检测当前IME
                ime_info = await self.ime_manager.detect_active_ime()
                if ime_info:
                    print(f"  ✓ 检测到IME: {ime_info.name}")
                    print(f"    - 框架: {ime_info.framework.value}")
                    print(f"    - 语言: {ime_info.language}")
                    print(f"    - 状态: {'活跃' if ime_info.is_active else '非活跃'}")
                else:
                    print("  ⚠ 未检测到活跃的IME")
                
                return {
                    'available': True,
                    'initialized': success,
                    'current_ime': ime_info.__dict__ if ime_info else None
                }
            else:
                print("  ✗ IME管理器初始化失败")
                return {
                    'available': False,
                    'initialized': False,
                    'error': 'IME manager initialization failed'
                }
                
        except Exception as e:
            print(f"  ✗ IME检查失败: {e}")
            return {'available': False, 'error': str(e)}
    
    async def _test_ime_functionality(self) -> Dict[str, Any]:
        """测试IME功能."""
        if not self.ime_manager or not self.ime_manager.is_initialized:
            print("  ✗ IME管理器未初始化，跳过功能测试")
            return {'skipped': True, 'reason': 'IME manager not initialized'}
        
        results = {}
        test_texts = [
            "Hello World",
            "你好世界",
            "こんにちは",
            "Hello 世界 Test",
            "123456"
        ]
        
        try:
            # 测试IME状态获取
            status = await self.ime_manager.get_ime_status()
            if status:
                print(f"  ✓ IME状态获取成功")
                print(f"    - 当前IME: {status.current_ime}")
                print(f"    - 输入语言: {status.input_language}")
                print(f"    - 焦点应用: {status.focus_app}")
                results['status_check'] = True
            else:
                print("  ✗ IME状态获取失败")
                results['status_check'] = False
            
            # 测试文本注入
            print("  🔤 测试文本注入...")
            injection_results = []
            
            for i, text in enumerate(test_texts):
                print(f"    测试 {i+1}/{len(test_texts)}: '{text}'", end=" ")
                
                try:
                    result = await self.ime_manager.inject_text(text)
                    if result.success:
                        print("✓")
                        injection_results.append({
                            'text': text,
                            'success': True,
                            'time': result.injection_time,
                            'method': result.ime_used
                        })
                    else:
                        print(f"✗ ({result.error})")
                        injection_results.append({
                            'text': text,
                            'success': False,
                            'error': result.error
                        })
                except Exception as e:
                    print(f"✗ (异常: {e})")
                    injection_results.append({
                        'text': text,
                        'success': False,
                        'error': str(e)
                    })
            
            success_count = sum(1 for r in injection_results if r['success'])
            print(f"  📈 注入成功率: {success_count}/{len(test_texts)} ({success_count/len(test_texts)*100:.1f}%)")
            
            results['injection_tests'] = injection_results
            results['success_rate'] = success_count / len(test_texts)
            
        except Exception as e:
            print(f"  ✗ 功能测试失败: {e}")
            results['error'] = str(e)
        
        return results
    
    async def _check_permissions(self) -> Dict[str, Any]:
        """检查权限设置."""
        results = {}
        
        if sys.platform == "darwin":
            print("  🍎 macOS权限检查:")
            # 检查辅助功能权限
            try:
                import subprocess
                result = subprocess.run([
                    'osascript', '-e', 
                    'tell application "System Events" to get name of first process'
                ], capture_output=True, timeout=2)
                
                if result.returncode == 0:
                    print("    ✓ 辅助功能权限已授予")
                    results['accessibility'] = True
                else:
                    print("    ✗ 辅助功能权限未授予")
                    results['accessibility'] = False
            except Exception as e:
                print(f"    ⚠ 无法检查辅助功能权限: {e}")
                results['accessibility'] = None
                
        elif sys.platform == "win32":
            print("  🪟 Windows权限检查:")
            try:
                from nextalk.utils.system import is_admin
                is_admin_user = is_admin()
                print(f"    {'✓' if is_admin_user else '⚠'} 管理员权限: {'已获得' if is_admin_user else '未获得'}")
                results['admin'] = is_admin_user
            except Exception as e:
                print(f"    ⚠ 无法检查管理员权限: {e}")
                results['admin'] = None
                
        elif sys.platform.startswith("linux"):
            print("  🐧 Linux权限检查:")
            # 检查X11权限
            try:
                import subprocess
                result = subprocess.run(['xdotool', 'search', '--name', '.*'], 
                                     capture_output=True, timeout=2)
                if result.returncode == 0:
                    print("    ✓ X11访问权限正常")
                    results['x11'] = True
                else:
                    print("    ✗ X11访问权限异常")
                    results['x11'] = False
            except FileNotFoundError:
                print("    ⚠ xdotool未安装")
                results['x11'] = None
            except Exception as e:
                print(f"    ⚠ X11权限检查失败: {e}")
                results['x11'] = None
        
        return results
    
    async def _check_app_compatibility(self) -> Dict[str, Any]:
        """检查应用兼容性."""
        print("  📱 应用兼容性检查:")
        
        # 获取当前焦点应用信息
        focus_info = await self._get_current_focus_info()
        if focus_info:
            print(f"    当前应用: {focus_info.get('app_name', 'Unknown')}")
            print(f"    窗口标题: {focus_info.get('window_title', 'Unknown')}")
            
            # 检查是否为已知兼容的应用
            compatible_apps = [
                'notepad', 'notepad++', 'code', 'vim', 'gedit',
                'terminal', 'cmd', 'powershell', 'bash',
                'chrome', 'firefox', 'safari', 'edge'
            ]
            
            app_name = focus_info.get('app_name', '').lower()
            is_compatible = any(compatible_app in app_name for compatible_app in compatible_apps)
            
            print(f"    兼容性: {'可能兼容' if is_compatible else '未知'}")
            
            return {
                'current_focus': focus_info,
                'likely_compatible': is_compatible,
                'known_compatible_apps': compatible_apps
            }
        else:
            print("    ⚠ 无法获取当前应用信息")
            return {'current_focus': None}
    
    async def _get_current_focus_info(self) -> Optional[Dict[str, Any]]:
        """获取当前焦点信息."""
        if self.ime_manager and hasattr(self.ime_manager, '_get_platform_adapter'):
            try:
                adapter = self.ime_manager._get_platform_adapter()
                if adapter and hasattr(adapter, '_get_focus_info'):
                    return await adapter._get_focus_info()
            except Exception as e:
                self.logger.debug(f"获取焦点信息失败: {e}")
        
        return None
    
    def _generate_report(self) -> None:
        """生成诊断报告."""
        print("\n" + "="*50)
        print("📋 诊断报告")
        print("="*50)
        
        # 系统状态
        sys_info = self.results.get('system_info', {})
        print(f"\n🖥️  系统状态:")
        print(f"   平台: {sys_info.get('system_info', {}).get('platform_system', 'Unknown')}")
        print(f"   要求满足: {'是' if sys_info.get('requirements_met') else '否'}")
        
        # IME状态
        ime_avail = self.results.get('ime_availability', {})
        print(f"\n🔧 IME状态:")
        print(f"   可用性: {'是' if ime_avail.get('available') else '否'}")
        if ime_avail.get('current_ime'):
            ime = ime_avail['current_ime']
            print(f"   当前IME: {ime.get('name', 'Unknown')}")
        
        # 功能测试
        ime_func = self.results.get('ime_functionality', {})
        if 'success_rate' in ime_func:
            rate = ime_func['success_rate'] * 100
            print(f"\n⚡ 功能测试:")
            print(f"   成功率: {rate:.1f}%")
            
            if rate < 50:
                print("   ⚠️  成功率较低，可能存在问题")
            elif rate < 80:
                print("   ⚠️  成功率一般，建议检查配置")
            else:
                print("   ✅ 成功率良好")
        
        # 权限状态
        perms = self.results.get('permissions', {})
        print(f"\n🔐 权限状态:")
        for perm_type, status in perms.items():
            if status is True:
                print(f"   ✅ {perm_type}: 正常")
            elif status is False:
                print(f"   ❌ {perm_type}: 异常")
            else:
                print(f"   ⚠️  {perm_type}: 无法检查")
        
        # 建议
        print(f"\n💡 建议:")
        self._generate_recommendations()
        
        # 保存报告
        self._save_report()
    
    def _generate_recommendations(self) -> None:
        """生成建议."""
        recommendations = []
        
        # 基于系统信息的建议
        sys_info = self.results.get('system_info', {})
        if not sys_info.get('requirements_met'):
            recommendations.append("检查并满足系统要求")
        
        # 基于IME可用性的建议
        ime_avail = self.results.get('ime_availability', {})
        if not ime_avail.get('available'):
            recommendations.append("检查IME系统是否正确安装和配置")
        
        # 基于功能测试的建议
        ime_func = self.results.get('ime_functionality', {})
        if ime_func.get('success_rate', 1.0) < 0.8:
            recommendations.append("检查目标应用的兼容性")
            recommendations.append("尝试使用不同的输入法")
        
        # 基于权限的建议
        perms = self.results.get('permissions', {})
        if sys.platform == "darwin" and perms.get('accessibility') is False:
            recommendations.append("在系统偏好设置中授予辅助功能权限")
        elif sys.platform == "win32" and perms.get('admin') is False:
            recommendations.append("考虑以管理员身份运行程序")
        elif sys.platform.startswith("linux") and perms.get('x11') is False:
            recommendations.append("检查X11配置和权限")
        
        if not recommendations:
            recommendations.append("系统状态良好，无特殊建议")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    
    def _save_report(self) -> None:
        """保存报告到文件."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ime_diagnostic_report_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"\n📄 报告已保存到: {filename}")
        except Exception as e:
            print(f"\n⚠️  无法保存报告: {e}")
    
    async def run_quick_test(self, text: str = "测试文本") -> bool:
        """运行快速IME测试."""
        print(f"🚀 快速IME测试: '{text}'")
        
        if not NEXTALK_AVAILABLE:
            print("❌ NexTalk模块不可用")
            return False
        
        try:
            # 初始化IME管理器
            ime_config = IMEConfig(enabled=True, auto_detect_ime=True)
            ime_manager = IMEManager(ime_config)
            
            if not await ime_manager.initialize():
                print("❌ IME初始化失败")
                return False
            
            print("✅ IME初始化成功")
            
            # 测试文本注入
            print("⏳ 正在注入文本...")
            result = await ime_manager.inject_text(text)
            
            if result.success:
                print(f"✅ 注入成功! 用时: {result.injection_time:.3f}s")
                print(f"   使用方法: {result.ime_used}")
                return True
            else:
                print(f"❌ 注入失败: {result.error}")
                return False
                
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            return False
        finally:
            if 'ime_manager' in locals():
                await ime_manager.cleanup()
    
    async def cleanup(self) -> None:
        """清理资源."""
        if self.ime_manager:
            await self.ime_manager.cleanup()


async def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="NexTalk IME诊断和测试工具")
    parser.add_argument(
        '--mode', 
        choices=['full', 'quick'], 
        default='full',
        help="运行模式: full=完整诊断, quick=快速测试"
    )
    parser.add_argument(
        '--text', 
        default="测试IME注入功能",
        help="测试文本 (仅用于快速测试模式)"
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true',
        help="显示详细信息"
    )
    
    args = parser.parse_args()
    
    tool = IMEDiagnosticTool(verbose=args.verbose)
    
    try:
        if args.mode == 'quick':
            success = await tool.run_quick_test(args.text)
            sys.exit(0 if success else 1)
        else:
            await tool.run_full_diagnosis()
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        sys.exit(1)
    finally:
        await tool.cleanup()


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 运行工具
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  程序已终止")
        sys.exit(1)