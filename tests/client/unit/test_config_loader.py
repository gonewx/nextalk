"""
配置加载器单元测试

对nextalk_client.config.loader模块中的配置加载功能进行测试。
测试使用mock模拟文件系统和configparser行为。
"""

import os
import pytest
from unittest import mock
from configparser import ConfigParser
from pathlib import Path

# 导入被测试的模块
from nextalk_client.config.loader import (
    load_config,
    ensure_config_directory,
    create_default_user_config,
    get_client_config,
    get_server_config
)


@pytest.fixture
def mock_configparser():
    """提供一个模拟的ConfigParser对象"""
    with mock.patch('configparser.ConfigParser', autospec=True) as mock_config:
        # 创建一个真实的ConfigParser实例作为返回值
        config_instance = ConfigParser()
        mock_config.return_value = config_instance
        yield mock_config


@pytest.fixture
def mock_file_system():
    """模拟文件系统操作，包括os.path和文件读取"""
    with mock.patch('os.path.exists') as mock_exists, \
         mock.patch('os.path.expanduser', return_value='/mock/home/.config/nextalk/config.ini') as mock_expanduser, \
         mock.patch('os.makedirs') as mock_makedirs:
        yield {
            'exists': mock_exists,
            'expanduser': mock_expanduser,
            'makedirs': mock_makedirs
        }


@pytest.fixture
def mock_package_config_path():
    """模拟包配置路径"""
    with mock.patch('pathlib.Path.parents', new_callable=mock.PropertyMock) as mock_parents, \
         mock.patch('pathlib.Path.__truediv__') as mock_truediv:
        # 设置Path().parents[3]返回的路径
        mock_parents.return_value = [None, None, None, '/mock/package']
        # 设置Path() / "config" / "default_config.ini"的结果
        mock_truediv.return_value = Path('/mock/package/config/default_config.ini')
        yield


@pytest.fixture
def mock_shutil():
    """模拟shutil.copy2操作"""
    with mock.patch('shutil.copy2') as mock_copy:
        yield mock_copy


def test_load_config_user_config_exists(mock_configparser, mock_file_system, mock_package_config_path):
    """测试当用户配置文件存在时加载配置"""
    # 设置模拟文件存在
    mock_file_system['exists'].return_value = True
    
    # 设置ConfigParser.read()返回文件列表，表示读取成功
    mock_config_instance = mock_configparser.return_value
    mock_config_instance.read.return_value = ['/mock/home/.config/nextalk/config.ini']
    
    # 添加测试配置
    mock_config_instance.add_section('Client')
    mock_config_instance.set('Client', 'hotkey', 'ctrl+alt+space')  # 自定义值
    mock_config_instance.set('Client', 'server_url', 'ws://127.0.0.1:8080/ws/stream')  # 自定义值
    
    mock_config_instance.add_section('Server')
    mock_config_instance.set('Server', 'default_model', 'tiny.en')  # 自定义值
    
    # 调用被测试的函数
    config = load_config()
    
    # 验证结果
    assert config['Client']['hotkey'] == 'ctrl+alt+space'
    assert config['Client']['server_url'] == 'ws://127.0.0.1:8080/ws/stream'
    assert config['Server']['default_model'] == 'tiny.en'
    
    # 确认默认值填充了缺失的键
    assert 'language' in config['Client']
    assert 'vad_sensitivity' in config['Server']
    assert 'device' in config['Server']
    assert 'compute_type' in config['Server']


def test_load_config_only_default_config(mock_configparser, mock_file_system, mock_package_config_path):
    """测试当用户配置不存在但默认配置存在时加载配置"""
    # 设置模拟用户配置不存在，但默认配置存在
    mock_file_system['exists'].side_effect = lambda path: '/mock/package/config/default_config.ini' in path
    
    # 设置默认配置读取成功
    mock_config_instance = mock_configparser.return_value
    mock_config_instance.read.return_value = ['/mock/package/config/default_config.ini']
    
    # 模拟默认配置内容
    default_config = ConfigParser()
    default_config.add_section('Client')
    default_config.set('Client', 'hotkey', 'ctrl+shift+space')
    default_config.set('Client', 'server_url', 'ws://127.0.0.1:8000/ws/stream')
    
    default_config.add_section('Server')
    default_config.set('Server', 'default_model', 'small.en-int8')
    default_config.set('Server', 'vad_sensitivity', '2')
    
    # 模拟default_config的读取结果
    with mock.patch('configparser.ConfigParser', return_value=default_config) as mock_default_config:
        with mock.patch.object(mock_config_instance, 'has_section', return_value=False):
            # 调用被测试的函数
            config = load_config()
    
    # 验证结果
    assert 'Client' in config
    assert 'Server' in config
    
    # 内置默认值应该被使用
    assert 'hotkey' in config['Client']
    assert 'default_model' in config['Server']


def test_load_config_no_config_files(mock_configparser, mock_file_system, mock_package_config_path):
    """测试当所有配置文件都不存在时使用内置默认值"""
    # 设置模拟所有文件都不存在
    mock_file_system['exists'].return_value = False
    
    # ConfigParser.read()返回空列表表示没有文件被读取
    mock_config_instance = mock_configparser.return_value
    mock_config_instance.read.return_value = []
    
    # 调用被测试的函数
    config = load_config()
    
    # 验证结果：应使用内置默认值
    assert config['Client']['hotkey'] == 'ctrl+shift+space'
    assert config['Client']['server_url'] == 'ws://127.0.0.1:8000/ws/stream'
    assert config['Client']['language'] == 'en'
    
    assert config['Server']['default_model'] == 'small.en-int8'
    assert config['Server']['vad_sensitivity'] == '2'
    assert config['Server']['device'] == 'cuda'
    assert config['Server']['compute_type'] == 'int8'


def test_ensure_config_directory(mock_file_system):
    """测试确保配置目录存在的功能"""
    # 调用被测试的函数
    result = ensure_config_directory()
    
    # 验证结果
    assert result is True
    mock_file_system['makedirs'].assert_called_once_with('/mock/home/.config/nextalk', exist_ok=True)


def test_create_default_user_config_already_exists(mock_file_system):
    """测试当用户配置已存在时的行为"""
    # 设置模拟用户配置已存在
    mock_file_system['exists'].return_value = True
    
    # 调用被测试的函数
    result = create_default_user_config()
    
    # 验证结果
    assert result is True


def test_create_default_user_config_from_package(mock_file_system, mock_shutil, mock_package_config_path):
    """测试从包配置文件创建用户配置文件"""
    # 设置模拟用户配置不存在，但包配置存在
    mock_file_system['exists'].side_effect = lambda path: '/mock/package/config/default_config.ini' in path
    
    # 调用被测试的函数
    result = create_default_user_config()
    
    # 验证结果
    assert result is True
    mock_shutil.assert_called_once_with(
        Path('/mock/package/config/default_config.ini'),
        '/mock/home/.config/nextalk/config.ini'
    )


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
    
    with mock.patch('nextalk_client.config.loader.load_config', return_value={}) as mock_load:
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('configparser.ConfigParser.read', return_value=[custom_path]):
                # 调用被测试的函数
                config = load_config(config_path=custom_path)
                
                # 验证load_config被调用时使用了自定义路径
                mock_load.assert_called_once() 