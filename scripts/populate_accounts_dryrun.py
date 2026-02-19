#!/usr/bin/env python3
"""
Dry-run version of populate_accounts.py to show what would be inserted.
"""

import os
import csv
import json
from pathlib import Path
from typing import Dict, List

class DatabasePopulatorDryRun:
    """Show what would be populated in telegram_accounts table."""
    
    def __init__(self, base_dir: str = "/Users/admin/Desktop/TGsys"):
        self.base_dir = Path(base_dir)
        self.sessions_dir = self.base_dir / "sessions"
        self.data_dir = self.base_dir / "data"
        self.proxy_csv = self.data_dir / "proxies.csv"
        
    def load_account_info(self) -> List[Dict]:
        """Load account info from JSON files."""
        accounts = []
        
        for info_file in self.sessions_dir.glob("*_info.json"):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    account_data = json.load(f)
                    accounts.append(account_data)
                    print(f"📋 Loaded account info: {account_data['account_name']}")
            except Exception as e:
                print(f"❌ Error loading {info_file}: {e}")
                
        return accounts
    
    def load_proxies(self) -> Dict[str, Dict]:
        """Load proxy data from CSV file."""
        proxies = {}
        
        if not self.proxy_csv.exists():
            print(f"❌ Proxy CSV not found: {self.proxy_csv}")
            return proxies
            
        try:
            with open(self.proxy_csv, 'r', encoding='utf-8') as f:
                content = f.read().strip().split('\n')
                if not content:
                    return proxies
                    
                headers = [h.strip().replace('\ufeff', '') for h in content[0].split(';')]
                print(f"📋 CSV Headers: {headers}")
                
                for line in content[1:]:
                    if line.strip():
                        values = [v.strip() for v in line.split(';')]
                        if len(values) >= len(headers):
                            row_data = dict(zip(headers, values))
                            
                            proxy_id = row_data['id']
                            proxies[proxy_id] = {
                                'id': proxy_id,
                                'ip': row_data['ip'],
                                'port_http': row_data['port_http'],
                                'port_socks5': row_data['port_socks5'],
                                'username': row_data['username'],
                                'password': row_data['password'],
                                'country': row_data['country']
                            }
                            print(f"🌐 Loaded proxy: {proxy_id} ({row_data['ip']})")
                    
        except Exception as e:
            print(f"❌ Error loading proxy CSV: {e}")
            
        return proxies
    
    def assign_proxies_to_accounts(self, accounts: List[Dict], proxies: Dict[str, Dict]) -> List[Dict]:
        """Assign proxies to accounts (round-robin)."""
        if not proxies:
            print("⚠️  No proxies available, accounts will be created without proxies")
            return accounts
            
        proxy_list = list(proxies.values())
        print(f"🔄 Assigning {len(proxy_list)} proxies to {len(accounts)} accounts")
        
        for i, account in enumerate(accounts):
            proxy = proxy_list[i % len(proxy_list)]
            account['proxy_id'] = proxy['id']
            account['proxy_type'] = 'socks5'  # Using SOCKS5 by default
            account['proxy_host'] = proxy['ip']
            account['proxy_port'] = proxy['port_socks5']
            account['proxy_username'] = proxy['username']
            account['proxy_password'] = proxy['password']
            
            print(f"✅ Assigned proxy {proxy['id']} ({proxy['ip']}) to {account['account_name']}")
            
        return accounts
    
    def show_sql_statements(self, accounts: List[Dict]) -> None:
        """Show SQL statements that would be executed."""
        print(f"\n📋 SQL Statements that would be executed:")
        print("=" * 80)
        
        for account in accounts:
            sql = f"""
INSERT INTO telegram_accounts 
(account_name, user_id, first_name, last_name, username, phone_number,
 session_file, is_active, health_score, session_status, comments_count,
 proxy_id, proxy_type, proxy_host, proxy_port, proxy_username, proxy_password)
VALUES (
    '{account['account_name']}',
    {account.get('user_id', 'NULL')},
    '{account.get('first_name', '')}',
    '{account.get('last_name', '')}',
    '{account.get('username', '')}',
    '{account.get('phone', '')}',
    '{account.get('session_file', '')}',
    true,
    100,
    'authorized',
    0,
    {account.get('proxy_id', 'NULL')},
    '{account.get('proxy_type', '')}',
    '{account.get('proxy_host', '')}',
    {account.get('proxy_port', 'NULL')},
    '{account.get('proxy_username', '')}',
    '{account.get('proxy_password', '')}'
);"""
            print(sql)
            print("-" * 40)
    
    def run_dry_run(self) -> None:
        """Run dry-run simulation."""
        print("🔍 Loading account and proxy data...")
        
        # Load data
        accounts = self.load_account_info()
        proxies = self.load_proxies()
        
        if not accounts:
            print("❌ No account info files found")
            return
            
        # Assign proxies
        accounts = self.assign_proxies_to_accounts(accounts, proxies)
        
        print(f"\n🎉 Dry-run complete!")
        print(f"📊 Total accounts to process: {len(accounts)}")
        
        # Show summary
        print(f"\n📋 Account Summary:")
        for account in accounts:
            proxy_info = f"Proxy: {account.get('proxy_host', 'None')}:{account.get('proxy_port', 'N/A')}"
            print(f"   • {account['account_name']} - {account.get('first_name', 'N/A')} {account.get('last_name', '')} - {proxy_info}")
        
        # Show SQL statements
        self.show_sql_statements(accounts)

def main():
    """Main function."""
    populator = DatabasePopulatorDryRun("/Users/admin/Desktop/TGsys")
    populator.run_dry_run()

if __name__ == "__main__":
    main()
