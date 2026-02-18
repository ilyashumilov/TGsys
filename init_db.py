#!/usr/bin/env python3
"""
Database initialization script for Telegram channels table.
Run this script to create the table and add sample channels.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'channel_parser_service', 'src'))

from postgres.client import PostgresClient, PostgresConnection
from config import PostgresConfig


def create_table_and_sample_data():
    """Create the telegram_channels table and insert sample data."""
    
    # Create table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS telegram_channels (
      id BIGSERIAL PRIMARY KEY,
      identifier TEXT NOT NULL UNIQUE,
      tg_channel_id BIGINT,
      last_message_id BIGINT NOT NULL DEFAULT 0,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    
    # Sample channels (you can modify these)
    sample_channels = [
        '@durov',
        '@telegram',
        'https://t.me/durov',
    ]
    
    try:
        # Load config
        pg_config = PostgresConfig.from_env()
        print(f"Connecting to PostgreSQL: {pg_config.host}:{pg_config.port}/{pg_config.db}")
        
        # Initialize database
        db = PostgresClient(
            PostgresConnection(
                host=pg_config.host,
                port=pg_config.port,
                db=pg_config.db,
                user=pg_config.user,
                password=pg_config.password,
            )
        )
        
        # Create table
        print("Creating telegram_channels table...")
        db.execute(create_table_sql)
        print("✅ Table created successfully")
        
        # Insert sample channels
        for channel in sample_channels:
            try:
                db.execute(
                    "INSERT INTO telegram_channels (identifier) VALUES (%s) ON CONFLICT (identifier) DO NOTHING",
                    (channel,)
                )
                print(f"✅ Added channel: {channel}")
            except Exception as e:
                print(f"⚠️  Channel {channel} already exists or error: {e}")
        
        # Verify table exists
        result = db.fetch_one("""
            SELECT COUNT(*) as count 
            FROM telegram_channels 
            WHERE is_active = TRUE
        """)
        
        print(f"\n📊 Database initialized successfully!")
        print(f"📈 Active channels to track: {result['count']}")
        
        # Show all channels
        channels = db.fetch_all("SELECT * FROM telegram_channels ORDER BY id")
        if channels:
            print("\n📋 Current channels:")
            for ch in channels:
                print(f"  ID: {ch['id']}, Identifier: {ch['identifier']}, Active: {ch['is_active']}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_table_and_sample_data()
