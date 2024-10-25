#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch, call
import json
import subprocess
from datetime import datetime
import logging
from keychain_bitwarden_sync import KeychainBitwardenSync, KeychainItem, BitwardenItem

@pytest.fixture
def mock_logger():
    logger = logging.getLogger('test-logger')
    logger.setLevel(logging.DEBUG)
    return logger

@pytest.fixture
def sync_app(mock_logger):
    app = KeychainBitwardenSync()
    app.logger = mock_logger
    return app

@pytest.fixture
def sample_keychain_items():
    return [
        KeychainItem(
            account='user1@example.com',
            service='example.com',
            password='password123'
        ),
        KeychainItem(
            account='user2@test.com',
            service='test.com',
            password='password456'
        )
    ]

@pytest.fixture
def sample_bitwarden_items():
    return [
        BitwardenItem(
            id='item1',
            name='example.com - user1@example.com',
            login={
                'username': 'user1@example.com',
                'password': 'password123'
            }
        )
    ]

class TestKeychainItemRetrieval:
    @patch('subprocess.run')
    @patch('keyring.get_password')
    def test_get_keychain_items_success(self, mock_get_password, mock_run, sync_app):
        # Mock the security command output
        mock_run.return_value = Mock(
            returncode=0,
            stdout='''
keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    0x00000007 <blob>="example.com"  (service)
    0x00000008 <blob>="user1@example.com"  (account)
            
keychain: "/Users/test/Library/Keychains/login.keychain-db"
class: "genp"
attributes:
    0x00000007 <blob>="test.com"  (service)
    0x00000008 <blob>="user2@test.com"  (account)
'''
        )
        
        # Mock password retrieval
        mock_get_password.side_effect = ['password123', 'password456']
        
        items = sync_app._get_keychain_items()
        
        assert len(items) == 2
        assert items[0].service == 'example.com'
        assert items[0].account == 'user1@example.com'
        assert items[1].service == 'test.com'
        assert items[1].account == 'user2@test.com'

    @patch('subprocess.run')
    def test_get_keychain_items_failure(self, mock_run, sync_app):
        mock_run.return_value = Mock(returncode=1, stderr='Access denied')
        
        items = sync_app._get_keychain_items()
        assert len(items) == 0

class TestBitwardenAuthentication:
    @patch('subprocess.run')
    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_bitwarden_success(self, mock_input, mock_getpass, mock_run, sync_app):
        mock_input.return_value = 'test@example.com'
        mock_getpass.return_value = 'masterpass'
        mock_run.return_value = Mock(
            returncode=0,
            stdout=b'mock-session-token'
        )
        
        result = sync_app._login_bitwarden()
        
        assert result is True
        assert sync_app.bw_session == 'mock-session-token'
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_login_bitwarden_failure(self, mock_input, mock_getpass, mock_run, sync_app):
        mock_input.return_value = 'test@example.com'
        mock_getpass.return_value = 'wrongpass'
        mock_run.return_value = Mock(returncode=1)
        
        result = sync_app._login_bitwarden()
        
        assert result is False
        assert sync_app.bw_session is None

class TestBitwardenOperations:
    @patch('subprocess.run')
    def test_get_bitwarden_items_success(self, mock_run, sync_app, sample_bitwarden_items):
        sync_app.bw_session = 'mock-session'
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([{
                'id': 'item1',
                'name': 'example.com - user1@example.com',
                'login': {
                    'username': 'user1@example.com',
                    'password': 'password123'
                }
            }])
        )
        
        items = sync_app._get_bitwarden_items()
        
        assert len(items) == 1
        assert items[0].id == 'item1'
        assert items[0].name == 'example.com - user1@example.com'

    @patch('subprocess.run')
    def test_get_bitwarden_items_no_session(self, mock_run, sync_app):
        sync_app.bw_session = None
        items = sync_app._get_bitwarden_items()
        assert len(items) == 0
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_create_bitwarden_item_success(self, mock_run, sync_app):
        sync_app.bw_session = 'mock-session'
        keychain_item = KeychainItem(
            account='new@example.com',
            service='example.com',
            password='newpass123'
        )
        
        mock_run.return_value = Mock(returncode=0)
        
        result = sync_app._create_bitwarden_item(keychain_item)
        
        assert result is True
        mock_run.assert_called_once()
        
        # Verify the item data format
        call_args = mock_run.call_args[1]['input']
        item_data = json.loads(call_args.decode())
        assert item_data['name'] == 'example.com - new@example.com'
        assert item_data['login']['username'] == 'new@example.com'
        assert item_data['login']['password'] == 'newpass123'

class TestSyncOperation:
    @patch.object(KeychainBitwardenSync, '_login_bitwarden')
    @patch.object(KeychainBitwardenSync, '_get_keychain_items')
    @patch.object(KeychainBitwardenSync, '_get_bitwarden_items')
    @patch.object(KeychainBitwardenSync, '_create_bitwarden_item')
    def test_sync_check_only(
        self, mock_create, mock_get_bw, mock_get_kc, mock_login,
        sync_app, sample_keychain_items, sample_bitwarden_items
    ):
        mock_login.return_value = True
        mock_get_kc.return_value = sample_keychain_items
        mock_get_bw.return_value = sample_bitwarden_items
        
        sync_app.sync(check_only=True)
        
        mock_create.assert_not_called()

    @patch.object(KeychainBitwardenSync, '_login_bitwarden')
    @patch.object(KeychainBitwardenSync, '_get_keychain_items')
    @patch.object(KeychainBitwardenSync, '_get_bitwarden_items')
    @patch.object(KeychainBitwardenSync, '_create_bitwarden_item')
    def test_sync_with_write(
        self, mock_create, mock_get_bw, mock_get_kc, mock_login,
        sync_app, sample_keychain_items, sample_bitwarden_items
    ):
        mock_login.return_value = True
        mock_get_kc.return_value = sample_keychain_items
        mock_get_bw.return_value = sample_bitwarden_items
        mock_create.return_value = True
        
        sync_app.sync(check_only=False)
        
        # Should try to create the second keychain item only
        mock_create.assert_called_once()
        created_item = mock_create.call_args[0][0]
        assert created_item.account == 'user2@test.com'
        assert created_item.service == 'test.com'

    def test_sync_login_failure(self, sync_app):
        with patch.object(KeychainBitwardenSync, '_login_bitwarden') as mock_login:
            mock_login.return_value = False
            sync_app.sync()
            mock_login.assert_called_once()

class TestCommandLineInterface:
    def test_cli_default_options(self):
        with patch('sys.argv', ['keychain-bitwarden-sync.py']):
            with patch.object(KeychainBitwardenSync, 'sync') as mock_sync:
                from keychain_bitwarden_sync import main
                main()
                mock_sync.assert_called_once_with(check_only=True)

    def test_cli_write_option(self):
        with patch('sys.argv', ['keychain-bitwarden-sync.py', '--write']):
            with patch.object(KeychainBitwardenSync, 'sync') as mock_sync:
                from keychain_bitwarden_sync import main
                main()
                mock_sync.assert_called_once_with(check_only=False)

    def test_cli_verbose_option(self):
        with patch('sys.argv', ['keychain-bitwarden-sync.py', '--verbose']):
            with patch.object(KeychainBitwardenSync, 'sync') as mock_sync:
                from keychain_bitwarden_sync import main
                main()
                # Verify logger level was set to DEBUG
                assert logging.getLogger('keychain-bw-sync').level == logging.DEBUG

class TestErrorHandling:
    @patch('subprocess.run')
    def test_keychain_command_exception(self, mock_run, sync_app):
        mock_run.side_effect = subprocess.SubprocessError()
        items = sync_app._get_keychain_items()
        assert items == []

    @patch('subprocess.run')
    def test_bitwarden_command_exception(self, mock_run, sync_app):
        sync_app.bw_session = 'mock-session'
        mock_run.side_effect = subprocess.SubprocessError()
        items = sync_app._get_bitwarden_items()
        assert items == []

    @patch('keyring.get_password')
    def test_keychain_password_retrieval_error(self, mock_get_password, sync_app):
        mock_get_password.side_effect = Exception('Access denied')
        password = sync_app._get_keychain_password('test', 'test')
        assert password == ''
