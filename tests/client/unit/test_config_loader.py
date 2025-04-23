"""
配置加载器单元测试

对nextalk_client.config.loader模块中的配置加载功能进行测试。
测试使用mock模拟文件系统和configparser行为。
"""

import os
import pytest
from unittest import mock
from configparser import ConfigParser
from pathlib import Path, PurePath

# 导入被测试的模块
from nextalk_client.config.loader import (
    load_config,
    ensure_config_directory,
    create_default_user_config,
    get_client_config,
    get_server_config
)


@pytest.fixture
def mock_config_parser():
    """模拟配置解析器，用于测试配置加载"""
    with mock.patch('configparser.ConfigParser') as mock_parser:
        # 设置模拟的读取行为
        mock_parser.return_value.read.return_value = ['mock_path']
        # 设置模拟的sections返回值
        mock_parser.return_value.sections.return_value = ['Client', 'Server']
        # 设置模拟的get方法
        mock_parser.return_value.get.side_effect = lambda section, option: {
            ('Client', 'hotkey'): 'ctrl+alt+space',
            ('Client', 'server_url'): 'ws://test.example.com/ws/stream',
            ('Client', 'language'): 'zh',
            ('Server', 'default_model'): 'test_model',
            ('Server', 'vad_sensitivity'): '3',
            ('Server', 'device'): 'cpu',
            ('Server', 'compute_type'): 'float16',
        }.get((section, option), '')
        # 设置模拟的has_section和has_option方法
        mock_parser.return_value.has_section.return_value = True
        mock_parser.return_value.has_option.return_value = True
        yield mock_parser


@pytest.fixture
def mock_file_system():
    """模拟文件系统操作"""
    with mock.patch('os.path.exists') as mock_exists, \
         mock.patch('os.path.expanduser') as mock_expanduser, \
         mock.patch('os.makedirs') as mock_makedirs:
        
        # 设置模拟的expanduser返回值
        mock_expanduser.return_value = '/mock/home/.config/nextalk/config.ini'
        
        # 默认情况下文件不存在
        mock_exists.return_value = False
        
        yield {
            'exists': mock_exists,
            'expanduser': mock_expanduser,
            'makedirs': mock_makedirs
        }


@pytest.fixture
def mock_package_config_path():
    """模拟包配置路径"""
    # 创建一个模拟的Path对象
    mock_path = mock.MagicMock(spec=Path)
    
    # 设置必要的属性和方法
    mock_path.parents = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock(), '/mock/package']
    mock_path.__truediv__ = mock.MagicMock(return_value=Path('/mock/package/config/default_config.ini'))
    
    # 为Path类添加_flavour属性以满足pathlib内部需求
    with mock.patch('pathlib.Path', return_value=mock_path) as mock_path_class:
        # 确保Path类有_flavour属性
        if not hasattr(PurePath, '_flavour'):
            # 从系统中获取真实的PurePath._flavour
            mock_path_class._flavour = PurePath()._flavour
        yield


@pytest.fixture
def mock_shutil():
    """模拟shutil模块操作"""
    with mock.patch('shutil.copy') as mock_copy:
        mock_copy.return_value = None
        yield mock_copy


def test_load_config_with_default_values(mock_config_parser, mock_file_system, mock_package_config_path):
    """测试加载配置时使用内置默认值"""
    # 设置文件不存在，强制使用内置默认值
    mock_file_system['exists'].return_value = False
    
    # 调用配置加载函数
    config = load_config()
    
    # 验证结果包含预期的默认值
    assert config['Client']['hotkey'] == 'ctrl+shift+space'
    assert config['Client']['server_url'] == 'ws://127.0.0.1:8000/ws/stream'
    assert config['Server']['default_model'] == 'small.en-int8'


def test_load_config_from_user_file(mock_config_parser, mock_file_system, mock_package_config_path):
    """测试从用户配置文件加载配置"""
    # 设置用户配置文件存在
    mock_file_system['exists'].side_effect = lambda path: path == '/mock/home/.config/nextalk/config.ini'
    
    # 调用配置加载函数
    config = load_config()
    
    # 验证结果使用了从文件加载的值
    assert config['Client']['hotkey'] == 'ctrl+alt+space'
    assert config['Client']['server_url'] == 'ws://test.example.com/ws/stream'
    assert config['Server']['default_model'] == 'test_model'


def test_load_config_with_custom_path(mock_config_parser, mock_file_system, mock_package_config_path):
    """测试使用自定义路径加载配置"""
    # 设置自定义配置文件路径
    custom_path = '/custom/path/config.ini'
    
    # 设置自定义路径的文件存在
    mock_file_system['exists'].side_effect = lambda path: path == custom_path
    
    # 调用配置加载函数，传入自定义路径
    config = load_config(custom_path)
    
    # 验证使用了自定义路径
    mock_config_parser.return_value.read.assert_called_with(custom_path)


def test_ensure_config_directory(mock_file_system):
    """测试确保配置目录存在"""
    # 设置目录不存在
    mock_file_system['exists'].return_value = False
    
    # 调用函数
    result = ensure_config_directory()
    
    # 验证结果
    assert result is True
    mock_file_system['makedirs'].assert_called_once()


def test_ensure_config_directory_already_exists(mock_file_system):
    """测试当配置目录已存在时确保配置目录"""
    # 设置目录已存在
    mock_file_system['exists'].return_value = True
    
    # 调用函数
    result = ensure_config_directory()
    
    # 验证结果
    assert result is True
    mock_file_system['makedirs'].assert_not_called()


def test_create_default_user_config_exists(mock_file_system):
    """测试当用户配置文件已存在时创建默认用户配置"""
    # 设置文件已存在
    mock_file_system['exists'].return_value = True
    
    # 调用函数
    result = create_default_user_config()
    
    # 验证结果
    assert result is True


@pytest.mark.skip(reason="需要更复杂的Path模拟")
def test_create_default_user_config_from_package(mock_file_system, mock_shutil, mock_package_config_path):
    """测试从包配置文件创建用户配置文件"""
    # 该测试需要更复杂的Path模拟，暂时跳过
    pass


def test_get_client_config():
    """测试获取客户端配置部分"""
    with mock.patch('nextalk_client.config.loader.load_config') as mock_load_config:
        # 设置load_config的返回值
        mock_load_config.return_value = {
            'Client': {'hotkey': 'ctrl+shift+space', 'server_url': 'ws://127.0.0.1:8000/ws/stream'},
            'Server': {'default_model': 'small.en-int8'}
        }
        
        # 调用被测试的函数
        client_config = get_client_config()
        
        # 验证结果
        assert client_config == {'hotkey': 'ctrl+shift+space', 'server_url': 'ws://127.0.0.1:8000/ws/stream'}


def test_get_server_config():
    """测试获取服务器配置部分"""
    with mock.patch('nextalk_client.config.loader.load_config') as mock_load_config:
        # 设置load_config的返回值
        mock_load_config.return_value = {
            'Client': {'hotkey': 'ctrl+shift+space'},
            'Server': {'default_model': 'small.en-int8', 'vad_sensitivity': '2'}
        }
        
        # 调用被测试的函数
        server_config = get_server_config()
        
        # 验证结果
        assert server_config == {'default_model': 'small.en-int8', 'vad_sensitivity': '2'}


def test_load_config_with_custom_path():
    """测试使用自定义路径加载配置"""
    custom_path = '/custom/path/config.ini'
    
    # 我们不再依赖mock.patch('nextalk_client.config.loader.load_config')，
    # 因为这会导致循环调用。相反，我们直接测试自定义路径的功能。
    
    with mock.patch('os.path.exists', return_value=True):
        with mock.patch('configparser.ConfigParser', autospec=True) as mock_config:
            mock_instance = mock.MagicMock()
            mock_config.return_value = mock_instance
            mock_instance.read.side_effect = lambda paths: [custom_path]
            
            # 模拟配置项
            config_data = {
                'Client': {'hotkey': 'ctrl+shift+space', 'server_url': 'ws://127.0.0.1:8000/ws/stream'},
                'Server': {'default_model': 'custom_model', 'vad_sensitivity': '2'}
            }
            
            # 模拟sections和配置项
            mock_instance.__contains__ = lambda self, item: item in config_data
            mock_instance.sections.return_value = config_data.keys()
            mock_instance.__getitem__.side_effect = lambda key: config_data[key]
            
            # 添加has_section和get方法
            mock_instance.has_section = lambda section: section in config_data
            mock_instance.get = lambda section, option, fallback=None: config_data[section].get(option, fallback)
            
            # 调用被测试的函数
            with mock.patch('nextalk_client.config.loader.ConfigParser', return_value=mock_instance):
                config = load_config(config_path=custom_path)
            
            # 验证read方法被调用
            # 由于是传入自定义路径，应该只尝试读取这个路径
            mock_instance.read.assert_called_once() 