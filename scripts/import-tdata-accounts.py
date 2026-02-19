#!/usr/bin/env python3
"""
Import accounts from tdata directory into TGsys database.
"""

import os
import json
import asyncio
import asyncpg
import shutil
from pathlib import Path

async def import_tdata_accounts():
    """Import accounts from tdata directory into database."""
    
    # Database connection
    db_url = "postgresql://user:password@postgres:5432/mydb"
    
    # Tdata directory
    tdata_dir = Path("/app/sessions/tdata")
    
    if not tdata_dir.exists():
        print("❌ Tdata directory not found at /app/sessions/tdata")
        return
    
    print(f"🔍 Scanning tdata directory: {tdata_dir}")
    
    # Find all account directories
    account_dirs = [d for d in tdata_dir.iterdir() if d.is_dir()]
    
    if not account_dirs:
        print("❌ No account directories found in tdata")
        return
    
    print(f"📁 Found {len(account_dirs)} account directories")
    
    # Connect to database
    conn = await asyncpg.connect(db_url)
    
    try:
        imported_count = 0
        
        for account_dir in account_dirs:
            account_name = account_dir.name
            
            # Look for session file
            session_files = list(account_dir.glob("*.session"))
            if not session_files:
                print(f"⚠️  No session file found for {account_name}")
                continue
                
            session_file = session_files[0]
            
            # Copy session file to standard sessions directory
            target_session = Path(f"/app/sessions/{account_name}.session")
            shutil.copy2(session_file, target_session)
            print(f"📄 Copied session: {session_file} → {target_session}")
            
            # Look for account data files
            json_files = list(account_dir.glob("*.json"))
            account_data = {}
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        account_data.update(data)
                except Exception as e:
                    print(f"⚠️  Error reading {json_file}: {e}")
            
            # Extract account info
            api_id = account_data.get('id')
            api_hash = account_data.get('hash')
            phone = account_data.get('phone')
            
            if not api_id or not api_hash:
                print(f"⚠️  Missing id or hash for {account_name}")
                continue
            
            # Check if account already exists
            existing = await conn.fetchval(
                "SELECT id FROM telegram_accounts WHERE api_id = $1",
                api_id
            )
            
            if existing:
                print(f"⏭  Account {api_id} already exists, updating...")
                # Update existing account
                await conn.execute(
                    """
                    UPDATE telegram_accounts 
                    SET is_active = true, session_status = 'authorized'
                    WHERE api_id = $1
                    """,
                    api_id
                )
                print(f"✅ Updated account {api_id}: {phone}")
            else:
                # Insert new account
                try:
                    await conn.execute(
                        """
                        INSERT INTO telegram_accounts 
                        (api_id, api_hash, phone_number, is_active, 
                         health_score, session_status, comments_count)
                        VALUES ($1, $2, $3, true, 85, 'authorized', 0)
                        """,
                        api_id, api_hash, phone
                    )
                    
                    print(f"✅ Imported account {api_id}: {phone}")
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to import {api_id}: {e}")
        
        print(f"🎉 Successfully processed {len(account_dirs)} accounts ({imported_count} new, {len(account_dirs)-imported_count} updated)")
        
        # Update available accounts count
        await conn.execute(
            "UPDATE telegram_accounts SET is_active = true WHERE session_status = 'authorized'"
        )
        
        print("✅ Updated account availability")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(import_tdata_accounts())
