#!/usr/bin/env python3

import subprocess
import json
import argparse
import sys
from typing import Dict, List, Optional
import keyring
import getpass
from dataclasses import dataclass
import logging
from datetime import datetime

@dataclass
class KeychainItem:
    account: str
    service: str
    password: str
    
@dataclass
class BitwardenItem:
    id: str
    name: str
    login: Dict
    
class KeychainBitwardenSync:
    def __init__(self):
        self.logger = self._setup_logging()
        self.bw_session: Optional[str] = None
        
    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger('keychain-bw-sync')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _get_keychain_items(self) -> List[KeychainItem]:
        """Retrieve all password items from macOS Keychain."""
        try:
            # Using security command-line tool to list all generic passwords
            cmd = ['security', 'dump-keychain', '-d']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to retrieve keychain items: {result.stderr}")
                return []
                
            items = []
            current_item = {}
            
            for line in result.stdout.split('\n'):
                if 'keychain: ' in line:
                    if current_item:
                        items.append(KeychainItem(
                            account=current_item.get('acct', ''),
                            service=current_item.get('svce', ''),
                            password=self._get_keychain_password(
                                current_item.get('acct', ''),
                                current_item.get('svce', '')
                            )
                        ))
                    current_item = {}
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip('" ')
                    value = value.strip('" ')
                    current_item[key] = value
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error retrieving keychain items: {str(e)}")
            return []
    
    def _get_keychain_password(self, account: str, service: str) -> str:
        """Retrieve specific password from keychain."""
        try:
            return keyring.get_password(service, account) or ''
        except Exception as e:
            self.logger.error(f"Error retrieving password for {account}@{service}: {str(e)}")
            return ''
    
    def _login_bitwarden(self) -> bool:
        """Log in to Bitwarden CLI."""
        try:
            email = input("Bitwarden email: ")
            password = getpass.getpass("Bitwarden master password: ")
            
            # Login to Bitwarden
            login_cmd = ['bw', 'login', email, '--raw']
            result = subprocess.run(login_cmd, input=password.encode(), capture_output=True)
            
            if result.returncode != 0:
                self.logger.error("Failed to login to Bitwarden")
                return False
            
            self.bw_session = result.stdout.decode().strip()
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging into Bitwarden: {str(e)}")
            return False
    
    def _get_bitwarden_items(self) -> List[BitwardenItem]:
        """Retrieve all items from Bitwarden vault."""
        try:
            if not self.bw_session:
                return []
                
            cmd = ['bw', 'list', 'items', '--session', self.bw_session]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error("Failed to retrieve Bitwarden items")
                return []
                
            items = json.loads(result.stdout)
            return [BitwardenItem(
                id=item['id'],
                name=item['name'],
                login=item.get('login', {})
            ) for item in items]
            
        except Exception as e:
            self.logger.error(f"Error retrieving Bitwarden items: {str(e)}")
            return []
    
    def _create_bitwarden_item(self, keychain_item: KeychainItem) -> bool:
        """Create new item in Bitwarden vault."""
        try:
            if not self.bw_session:
                return False
                
            item_data = {
                'organizationId': None,
                'folderId': None,
                'type': 1,
                'name': f"{keychain_item.service} - {keychain_item.account}",
                'notes': f"Imported from macOS Keychain on {datetime.now().isoformat()}",
                'favorite': False,
                'login': {
                    'username': keychain_item.account,
                    'password': keychain_item.password,
                    'uris': [
                        {
                            'match': None,
                            'uri': f"https://{keychain_item.service}"
                        }
                    ]
                }
            }
            
            cmd = ['bw', 'create', 'item', '--session', self.bw_session]
            result = subprocess.run(cmd, input=json.dumps(item_data).encode(), capture_output=True)
            
            if result.returncode != 0:
                self.logger.error(f"Failed to create Bitwarden item for {keychain_item.account}@{keychain_item.service}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating Bitwarden item: {str(e)}")
            return False
    
    def sync(self, check_only: bool = True) -> None:
        """Main sync function."""
        if not self._login_bitwarden():
            return
            
        keychain_items = self._get_keychain_items()
        bitwarden_items = self._get_bitwarden_items()
        
        # Create lookup dictionary for Bitwarden items
        bw_lookup = {
            f"{item.login.get('username', '')}@{item.name.split(' - ')[0]}": item
            for item in bitwarden_items
        }
        
        for kc_item in keychain_items:
            key = f"{kc_item.account}@{kc_item.service}"
            
            if key not in bw_lookup:
                self.logger.info(f"New item found: {key}")
                if not check_only:
                    if self._create_bitwarden_item(kc_item):
                        self.logger.info(f"Successfully created Bitwarden item for {key}")
                    else:
                        self.logger.error(f"Failed to create Bitwarden item for {key}")
            else:
                self.logger.debug(f"Item already exists in Bitwarden: {key}")

def main():
    parser = argparse.ArgumentParser(description='Sync macOS Keychain passwords to Bitwarden')
    parser.add_argument('--write', action='store_true', help='Enable writing updates to Bitwarden')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    syncer = KeychainBitwardenSync()
    if args.verbose:
        syncer.logger.setLevel(logging.DEBUG)
    
    syncer.sync(check_only=not args.write)

if __name__ == '__main__':
    main()
    