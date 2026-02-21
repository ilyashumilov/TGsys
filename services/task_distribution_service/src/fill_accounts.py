#!/usr/bin/env python3
"""
Script to populate telegram_accounts database from session files and assign proxies.
"""

import csv
import os
import glob
import re
from dataclasses import dataclass
from typing import List, Optional

from config import PostgresConfig
from custom_clients.postgres_client import PostgresClient, PostgresConnection


@dataclass
class Proxy:
    id: str
    ip: str
    port_http: str
    port_socks5: str
    username: str
    password: str
    internal_ip: str
    country: str


def load_proxies(csv_path: str) -> List[Proxy]:
    """Load proxies from CSV file."""
    proxies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 8:
                proxies.append(Proxy(
                    id=row[0],
                    ip=row[1],
                    port_http=row[2],
                    port_socks5=row[3],
                    username=row[4],
                    password=row[5],
                    internal_ip=row[6],
                    country=row[7]
                ))
    return proxies


def extract_phone_from_session(session_path: str) -> Optional[str]:
    """Extract phone number from session filename."""
    basename = os.path.basename(session_path)
    if basename.endswith('.session'):
        phone = basename[:-8]  # Remove .session
        # Validate phone format (basic check)
        if re.match(r'^\+?\d{10,15}$', phone):
            return phone
    return None


async def fill_accounts(session_dir: str, proxies_csv: str):
    """Fill accounts database from sessions and assign proxies."""

    # Load proxies
    if not os.path.exists(proxies_csv):
        print(f"❌ Proxies CSV not found: {proxies_csv}")
        return

    proxies = load_proxies(proxies_csv)
    if not proxies:
        print("❌ No proxies loaded from CSV")
        return

    print(f"📋 Loaded {len(proxies)} proxies")

    # Find session files
    if not os.path.exists(session_dir):
        print(f"❌ Session directory not found: {session_dir}")
        return

    session_pattern = os.path.join(session_dir, "*.session")
    session_files = glob.glob(session_pattern)

    if not session_files:
        print(f"❌ No session files found in {session_dir}")
        return

    print(f"📁 Found {len(session_files)} session files")

    # Connect to database
    pg_config = PostgresConfig.from_env()
    db = PostgresClient(PostgresConnection(
        host=pg_config.host,
        port=pg_config.port,
        database=pg_config.db,
        user=pg_config.user,
        password=pg_config.password,
    ))

    await db.connect()

    try:
        inserted_count = 0
        proxy_index = 0

        for session_file in session_files:
            phone = extract_phone_from_session(session_file)
            if not phone:
                print(f"⚠️  Could not extract phone from {session_file}")
                continue

            # Check if account already exists
            existing = await db.fetch_one(
                "SELECT id FROM telegram_accounts WHERE phone_number = %s",
                (phone,)
            )

            if existing:
                print(f"⏭️  Account {phone} already exists, skipping")
                continue

            # Assign proxy (cycle through available proxies)
            proxy = proxies[proxy_index % len(proxies)]
            proxy_index += 1

            # Insert account
            account_data = {
                'account_name': f"account_{phone.replace('+', '')}",
                'phone_number': phone,
                'session_file': os.path.basename(session_file),
                'is_active': True,
                'health_score': 100,
                'session_status': 'authorized',
                'proxy_type': 'socks5',
                'proxy_host': proxy.ip,
                'proxy_port': int(proxy.port_socks5),
                'proxy_username': proxy.username,
                'proxy_password': proxy.password,
            }

            try:
                await db.insert("telegram_accounts", account_data)
                print(f"✅ Inserted account {phone} with proxy {proxy.ip}:{proxy.port_socks5}")
                inserted_count += 1
            except Exception as e:
                print(f"❌ Failed to insert account {phone}: {e}")

        print(f"\n🎉 Completed! Inserted {inserted_count} accounts")

    finally:
        await db.close()


async def main():
    """Main function."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python fill_accounts.py <session_dir> <proxies_csv>")
        print("Example: python fill_accounts.py /path/to/sessions /path/to/proxies.csv")
        sys.exit(1)

    session_dir = sys.argv[1]
    proxies_csv = sys.argv[2]

    print("🚀 Starting account database population...")
    await fill_accounts(session_dir, proxies_csv)
    print("✅ Done!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
