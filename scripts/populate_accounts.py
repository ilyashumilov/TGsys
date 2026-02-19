#!/usr/bin/env python3
"""
Populate telegram_accounts table with converted sessions and assign proxies.
This script reads the converted session info and proxy CSV to populate the database.
"""

import os
import csv
import asyncio
import asyncpg
from pathlib import Path
from typing import Dict, List, Optional

class DatabasePopulator:
    """Populate telegram_accounts table with session data and proxies."""
    
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
                import json
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
            account['proxy_id'] = int(proxy['id'])
            account['proxy_type'] = 'socks5'  # Using SOCKS5 by default
            account['proxy_host'] = proxy['ip']
            account['proxy_port'] = int(proxy['port_socks5'])
            account['proxy_username'] = proxy['username']
            account['proxy_password'] = proxy['password']
            
            print(f"✅ Assigned proxy {proxy['id']} ({proxy['ip']}) to {account['account_name']}")
            
        return accounts
    
    async def populate_database(self, db_url: str = "postgresql://user:password@postgres:5432/mydb") -> None:
        """Populate the telegram_accounts table."""
        print("🔍 Loading account and proxy data...")
        
        # Load data
        accounts = self.load_account_info()
        proxies = self.load_proxies()
        
        if not accounts:
            print("❌ No account info files found")
            return
            
        # Assign proxies
        accounts = self.assign_proxies_to_accounts(accounts, proxies)
        
        # Connect to database
        try:
            conn = await asyncpg.connect(db_url)
            print("🔗 Connected to database")
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            print("💡 Make sure PostgreSQL is running and the database exists")
            return
        
        try:
            inserted_count = 0
            updated_count = 0
            
            for account in accounts:
                # Check if account already exists
                existing = await conn.fetchval(
                    "SELECT id FROM telegram_accounts WHERE account_name = $1",
                    account['account_name']
                )
                
                if existing:
                    # Update existing account
                    await conn.execute(
                        """
                        UPDATE telegram_accounts 
                        SET user_id = $2, first_name = $3, last_name = $4, username = $5,
                            phone_number = $6, session_file = $7, session_status = 'authorized',
                            proxy_id = $8, proxy_type = $9, proxy_host = $10, proxy_port = $11,
                            proxy_username = $12, proxy_password = $13
                        WHERE account_name = $1
                        """,
                        account['account_name'],
                        account.get('user_id'),
                        account.get('first_name'),
                        account.get('last_name'),
                        account.get('username'),
                        account.get('phone'),
                        account.get('session_file'),
                        account.get('proxy_id'),
                        account.get('proxy_type'),
                        account.get('proxy_host'),
                        account.get('proxy_port'),
                        account.get('proxy_username'),
                        account.get('proxy_password')
                    )
                    print(f"🔄 Updated account: {account['account_name']}")
                    updated_count += 1
                else:
                    # Insert new account
                    await conn.execute(
                        """
                        INSERT INTO telegram_accounts 
                        (account_name, user_id, first_name, last_name, username, phone_number,
                         session_file, is_active, health_score, session_status, comments_count,
                         proxy_id, proxy_type, proxy_host, proxy_port, proxy_username, proxy_password)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, true, 100, 'authorized', 0,
                                $8, $9, $10, $11, $12, $13)
                        """,
                        account['account_name'],
                        account.get('user_id'),
                        account.get('first_name'),
                        account.get('last_name'),
                        account.get('username'),
                        account.get('phone'),
                        account.get('session_file'),
                        account.get('proxy_id'),
                        account.get('proxy_type'),
                        account.get('proxy_host'),
                        account.get('proxy_port'),
                        account.get('proxy_username'),
                        account.get('proxy_password')
                    )
                    print(f"✅ Inserted account: {account['account_name']}")
                    inserted_count += 1
            
            print(f"\n🎉 Database population complete!")
            print(f"✅ Inserted: {inserted_count}")
            print(f"🔄 Updated: {updated_count}")
            print(f"📊 Total accounts processed: {len(accounts)}")
            
            # Show summary
            print(f"\n📋 Account Summary:")
            for account in accounts:
                proxy_info = f"Proxy: {account.get('proxy_host', 'None')}:{account.get('proxy_port', 'N/A')}"
                print(f"   • {account['account_name']} - {account.get('first_name', 'N/A')} {account.get('last_name', '')} - {proxy_info}")
                
        except Exception as e:
            print(f"❌ Database error: {e}")
        finally:
            await conn.close()

async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate telegram_accounts table with sessions and proxies")
    parser.add_argument("--db-url", type=str, default="postgresql://user:password@postgres:5432/mydb",
                       help="PostgreSQL database URL")
    parser.add_argument("--base-dir", type=str, default="/Users/admin/Desktop/TGsys",
                       help="Base directory containing sessions and data folders")
    
    args = parser.parse_args()
    
    populator = DatabasePopulator(args.base_dir)
    await populator.populate_database(args.db_url)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
