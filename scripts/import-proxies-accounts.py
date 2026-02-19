#!/usr/bin/env python3
"""
Import accounts from proxies.csv into TGsys database.
Sets up 1 account for channel parser and n accounts for comment workers.
"""

import csv
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Configuration
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "tgsys")

# Channel parser account (first account will be used for monitoring)
CHANNEL_PARSER_API_ID = 33093187  # Your existing channel parser account
CHANNEL_PARSER_API_HASH = "your_api_hash_here"  # Replace with actual hash

async def create_database_connection():
    """Create database connection."""
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    try:
        conn = await asyncpg.connect(db_url)
        print(f"✅ Connected to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

async def setup_channel_parser_account(conn):
    """Setup the channel parser account if not exists."""
    print("\n🔧 Setting up channel parser account...")
    
    # Check if channel parser account exists
    existing = await conn.fetchval(
        "SELECT id FROM telegram_accounts WHERE api_id = $1",
        CHANNEL_PARSER_API_ID
    )
    
    if existing:
        print(f"⏭ Channel parser account {CHANNEL_PARSER_API_ID} already exists")
        await conn.execute(
            """
            UPDATE telegram_accounts 
            SET is_active = true, session_status = 'authorized', health_score = 100
            WHERE api_id = $1
            """,
            CHANNEL_PARSER_API_ID
        )
        print(f"✅ Updated channel parser account")
    else:
        # Insert channel parser account
        await conn.execute(
            """
            INSERT INTO telegram_accounts 
            (api_id, api_hash, phone_number, is_active, 
             health_score, session_status, comments_count)
            VALUES ($1, $2, $3, true, 100, 'authorized', 0)
            """,
            CHANNEL_PARSER_API_ID, CHANNEL_PARSER_API_HASH, "channel_parser"
        )
        print(f"✅ Created channel parser account {CHANNEL_PARSER_API_ID}")

async def import_proxy_accounts(conn, proxies_csv_path):
    """Import accounts from proxies.csv file."""
    print(f"\n📥 Importing accounts from {proxies_csv_path}...")
    
    if not Path(proxies_csv_path).exists():
        print(f"❌ File not found: {proxies_csv_path}")
        return 0
    
    imported_count = 0
    updated_count = 0
    
    with open(proxies_csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        
        for row in reader:
            try:
                proxy_id = row['id']
                proxy_ip = row['ip']
                port_socks5 = row['port_socks5']
                username = row['username']
                password = row['password']
                country = row.get('country', 'unknown')
                
                # Generate account details based on proxy
                api_id = int(proxy_id) + 100000000  # Ensure unique API IDs
                api_hash = f"generated_hash_{proxy_id}"  # Replace with actual API hashes
                phone_number = f"+1{proxy_id:010d}"  # Generate phone number
                
                # Check if account already exists
                existing = await conn.fetchval(
                    "SELECT id FROM telegram_accounts WHERE api_id = $1",
                    api_id
                )
                
                if existing:
                    # Update existing account with new proxy info
                    await conn.execute(
                        """
                        UPDATE telegram_accounts 
                        SET proxy_type = 'socks5',
                            proxy_host = $2,
                            proxy_port = $3,
                            proxy_username = $4,
                            proxy_password = $5,
                            is_active = true,
                            health_score = 85,
                            session_status = 'authorized'
                        WHERE api_id = $1
                        """,
                        api_id, proxy_ip, int(port_socks5), username, password
                    )
                    updated_count += 1
                    print(f"🔄 Updated account {api_id} with proxy {proxy_ip}:{port_socks5}")
                else:
                    # Insert new account
                    await conn.execute(
                        """
                        INSERT INTO telegram_accounts 
                        (api_id, api_hash, phone_number, is_active,
                         health_score, session_status, comments_count,
                         proxy_type, proxy_host, proxy_port, proxy_username, proxy_password)
                        VALUES ($1, $2, $3, true, 85, 'authorized', 0,
                                'socks5', $4, $5, $6, $7)
                        """,
                        api_id, api_hash, phone_number,
                        proxy_ip, int(port_socks5), username, password
                    )
                    imported_count += 1
                    print(f"✅ Imported account {api_id} with proxy {proxy_ip}:{port_socks5} ({country})")
                
            except Exception as e:
                print(f"❌ Error processing proxy {proxy_id}: {e}")
                continue
    
    print(f"\n📊 Import Summary:")
    print(f"   ├─ New accounts: {imported_count}")
    print(f"   ├─ Updated accounts: {updated_count}")
    print(f"   └─ Total processed: {imported_count + updated_count}")
    
    return imported_count + updated_count

async def create_session_template(conn):
    """Create session template file path info."""
    print("\n📄 Session file setup:")
    print("   ├─ Channel parser: /app/sessions/33093187_session.session")
    print("   ├─ Template file: /app/sessions/33093187_session.session")
    print("   └─ Workers will use this template to create account-specific sessions")

async def show_account_summary(conn):
    """Show summary of all accounts in database."""
    print("\n📋 Account Summary:")
    
    # Channel parser account
    channel_parser = await conn.fetchrow(
        "SELECT * FROM telegram_accounts WHERE api_id = $1",
        CHANNEL_PARSER_API_ID
    )
    
    if channel_parser:
        print(f"🔍 Channel Parser Account:")
        print(f"   ├─ ID: {channel_parser['id']}")
        print(f"   ├─ API ID: {channel_parser['api_id']}")
        print(f"   ├─ Status: {channel_parser['session_status']}")
        print(f"   ├─ Health: {channel_parser['health_score']}")
        print(f"   └─ Active: {channel_parser['is_active']}")
    
    # Comment worker accounts
    worker_accounts = await conn.fetch(
        """
        SELECT id, api_id, proxy_host, proxy_port, health_score, 
               session_status, comments_count
        FROM telegram_accounts 
        WHERE api_id != $1 AND is_active = true
        ORDER BY id
        """,
        CHANNEL_PARSER_API_ID
    )
    
    print(f"\n👥 Comment Worker Accounts ({len(worker_accounts)} total):")
    
    for i, account in enumerate(worker_accounts[:5], 1):  # Show first 5
        print(f"   ├─ Account {account['id']}: API {account['api_id']} "
              f"→ {account['proxy_host']}:{account['proxy_port']} "
              f"(Health: {account['health_score']}, Comments: {account['comments_count']})")
    
    if len(worker_accounts) > 5:
        print(f"   └─ ... and {len(worker_accounts) - 5} more accounts")

async def main():
    """Main import function."""
    print("🚀 TGsys Account Importer")
    print("=" * 50)
    
    # Check if API hash is set
    if CHANNEL_PARSER_API_HASH == "your_api_hash_here":
        print("⚠️  WARNING: Please update CHANNEL_PARSER_API_HASH in the script")
        print("   This should be your actual Telegram API hash for the channel parser")
    
    # Path to proxies.csv
    proxies_csv = "/Users/admin/Downloads/proxies.csv"
    
    if not Path(proxies_csv).exists():
        print(f"❌ Proxies file not found: {proxies_csv}")
        print("   Please update the proxies_csv path in the script")
        sys.exit(1)
    
    # Connect to database
    conn = await create_database_connection()
    
    try:
        # Setup channel parser account
        await setup_channel_parser_account(conn)
        
        # Import proxy accounts for comment workers
        worker_count = await import_proxy_accounts(conn, proxies_csv)
        
        # Session file info
        await create_session_template(conn)
        
        # Show summary
        await show_account_summary(conn)
        
        print(f"\n🎉 Setup Complete!")
        print(f"   ├─ 1 Channel Parser Account")
        print(f"   ├─ {worker_count} Comment Worker Accounts")
        print(f"   └─ Ready to start services")
        
        print(f"\n📝 Next Steps:")
        print(f"   1. Update CHANNEL_PARSER_API_HASH with real API hash")
        print(f"   2. Replace generated API hashes with real ones")
        print(f"   3. Ensure session file exists at /app/sessions/33093187_session.session")
        print(f"   4. Start services: docker-compose up -d")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
