#!/usr/bin/env python3
"""Convert all tdata directories to Telethon session files using OpenTele library.
This script finds all tdata directories and converts them to .session files
that can be used by Telethon-based services.
"""

import os
import sys
import shutil
import asyncio
import sqlite3
from pathlib import Path
from typing import List, Optional
import json

try:
    from opentele.td import TDesktop
    from opentele.tl import TelegramClient
    from opentele.api import API, UseCurrentSession
except ImportError:
    print("❌ OpenTele not installed. Please install it with: pip install opentele")
    sys.exit(1)

class TDataConverter:
    """Convert tdata directories to Telethon session files using OpenTele."""
    
    def __init__(self, base_dir: str = "/Users/admin/Desktop/TGsys/sessions"):
        self.base_dir = Path(base_dir)
        self.tdata_dir = self.base_dir / "tdata"
        self.sessions_dir = self.base_dir
        
    def find_tdata_directories(self) -> List[Path]:
        """Find all directories containing tdata folders."""
        tdata_accounts = []
        
        if not self.tdata_dir.exists():
            print(f"❌ Tdata directory not found: {self.tdata_dir}")
            return tdata_accounts
            
        for item in self.tdata_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                tdata_path = item / "tdata"
                if tdata_path.exists() and tdata_path.is_dir():
                    # Check if tdata contains necessary files
                    if self._is_valid_tdata(tdata_path):
                        tdata_accounts.append(item)
                        
        return tdata_accounts
    
    def _is_valid_tdata(self, tdata_path: Path) -> bool:
        """Check if tdata directory contains valid Telegram data."""
        required_files = ["key_datas"]
        optional_files = ["D877F783D5D3EF8C", "D877F783D5D3EF8Cs"]
        
        has_required = any((tdata_path / f).exists() for f in required_files)
        has_optional = any((tdata_path / f).exists() for f in optional_files)
        
        return has_required or has_optional
    
    async def convert_single_account(self, account_dir: Path) -> bool:
        """Convert a single tdata directory to session file using OpenTele."""
        account_name = account_dir.name
        tdata_path = account_dir / "tdata"
        session_file = self.sessions_dir / f"{account_name}.session"
        
        print(f"🔄 Converting {account_name}...")
        
        try:
            # Load TDesktop client from tdata folder
            print(f"📁 Loading TDesktop from: {tdata_path}")
            tdesk = TDesktop(str(tdata_path))
            
            # Check if we have loaded any accounts
            if not tdesk.isLoaded():
                print(f"❌ No accounts found in {account_name}")
                return False
            
            print(f"✅ TDesktop loaded for {account_name}")
            
            # Convert TDesktop to Telethon using the current session
            client = await tdesk.ToTelethon(
                session=str(session_file.with_suffix('')),
                flag=UseCurrentSession
            )
            
            # Connect and verify the session
            await client.connect()
            
            # Get user info for verification
            me = await client.get_me()
            print(f"✅ Successfully converted {account_name} to session")
            print(f"👤 User: {me.first_name} {me.last_name or ''} (@{me.username or 'N/A'})")
            
            # Save account info to JSON for reference
            account_info = {
                "account_name": account_name,
                "user_id": me.id,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "username": me.username,
                "phone": me.phone,
                "session_file": str(session_file),
                "tdata_path": str(tdata_path)
            }
            
            info_file = self.sessions_dir / f"{account_name}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(account_info, f, indent=2, ensure_ascii=False)
            
            await client.disconnect()
            return True
            
        except Exception as e:
            print(f"❌ Error converting {account_name}: {e}")
            return False
    
    async def convert_all_accounts(self) -> None:
        """Convert all tdata directories to session files."""
        print("🔍 Scanning for tdata directories...")
        
        tdata_accounts = self.find_tdata_directories()
        
        if not tdata_accounts:
            print("❌ No valid tdata directories found")
            return
        
        print(f"📁 Found {len(tdata_accounts)} tdata directories to convert")
        
        successful_conversions = 0
        failed_conversions = 0
        
        for account_dir in tdata_accounts:
            if await self.convert_single_account(account_dir):
                successful_conversions += 1
            else:
                failed_conversions += 1
        
        print(f"\n🎉 Conversion complete!")
        print(f"✅ Successful: {successful_conversions}")
        print(f"❌ Failed: {failed_conversions}")
        
        if successful_conversions > 0:
            print(f"\n📄 Session files created in: {self.sessions_dir}")
            print("💡 You can now use these session files with Telethon-based services")
            print("📋 Account info saved to *_info.json files")

async def main():
    """Main conversion function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert tdata directories to Telethon session files using OpenTele")
    parser.add_argument("--base-dir", type=str, default="/Users/admin/Desktop/TGsys/sessions", 
                       help="Base directory containing tdata folder")
    
    args = parser.parse_args()
    
    converter = TDataConverter(args.base_dir)
    await converter.convert_all_accounts()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
