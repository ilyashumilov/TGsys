#!/usr/bin/env python3
"""
Diagnostic script for Task Distribution Service
Run this to check configuration and connectivity
"""

import asyncio
import os
import sys
import logging
from config import AppConfig, KafkaConfig, PostgresConfig, setup_logging
from custom_clients.kafka_client import KafkaConfig as KafkaClientConfig, KafkaProducerClient, KafkaConsumerClient
from custom_clients.postgres_client import PostgresClient, PostgresConnection

async def test_postgres_connection():
    """Test PostgreSQL connection."""
    print("🔍 Testing PostgreSQL connection...")
    try:
        config = PostgresConfig.from_env()
        print(f"   Host: {config.host}")
        print(f"   Port: {config.port}")
        print(f"   Database: {config.db}")
        print(f"   User: {config.user}")
        
        client = PostgresClient(PostgresConnection(
            host=config.host,
            port=config.port,
            database=config.db,
            user=config.user,
            password=config.password,
        ))
        
        await client.connect()
        
        # Test query
        result = await client._pool.fetch("SELECT version()")
        print(f"   ✅ PostgreSQL connected: {result[0]['version']}")
        
        # Check if telegram_accounts table exists
        tables = await client._pool.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'telegram_accounts'
        """)
        
        if tables:
            print("   ✅ telegram_accounts table exists")
            
            # Check account count
            count = await client._pool.fetchval("SELECT COUNT(*) FROM telegram_accounts")
            print(f"   📊 Found {count} accounts in database")
            
            # Check available accounts
            available = await client.get_available_accounts_list(
                min_health_score=70, 
                cooldown_minutes=18  # 18 minutes default
            )
            print(f"   📊 {len(available)} accounts available for tasks")
            
        else:
            print("   ❌ telegram_accounts table not found")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        return False

async def test_kafka_connection():
    """Test Kafka connection."""
    print("\n🔍 Testing Kafka connection...")
    try:
        config = KafkaConfig.from_env()
        print(f"   Broker: {config.broker}")
        print(f"   Topic: {config.topic}")
        print(f"   Consumer Group: {config.consumer_group}")
        
        # Test consumer
        consumer_config = KafkaClientConfig(
            broker=config.broker,
            topic=config.topic,
            consumer_group=config.consumer_group,
            consumer_start_delay=1  # Short delay for testing
        )
        
        consumer = KafkaConsumerClient(consumer_config)
        await consumer.connect()
        print("   ✅ Kafka consumer connected")
        
        # Test producer
        producer_config = KafkaClientConfig(
            broker=config.broker,
            topic="comment-tasks",
            consumer_group=config.consumer_group
        )
        
        producer = KafkaProducerClient(producer_config)
        await producer.connect()
        print("   ✅ Kafka producer connected")
        
        await consumer.disconnect()
        await producer.disconnect()
        return True
        
    except Exception as e:
        print(f"   ❌ Kafka connection failed: {e}")
        return False

async def test_configuration():
    """Test configuration values."""
    print("\n🔍 Testing configuration...")
    
    try:
        app_config = AppConfig.from_env()
        kafka_config = KafkaConfig.from_env()
        postgres_config = PostgresConfig.from_env()
        
        print(f"   Log Level: {app_config.log_level}")
        print(f"   Min Health Score: {app_config.min_health_score}")
        print(f"   Cooldown Minutes: {app_config.cooldown_minutes}")
        print(f"   Max Retries: {app_config.max_retries}")
        print(f"   Retry Delay: {app_config.retry_delay}")
        
        # Check for missing environment variables
        required_vars = [
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 
            'POSTGRES_USER', 'POSTGRES_PASSWORD',
            'KAFKA_BROKER', 'KAFKA_TOPIC'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ❌ Missing environment variables: {missing_vars}")
            return False
        else:
            print("   ✅ All required environment variables set")
            return True
            
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        return False

async def main():
    """Run all diagnostic tests."""
    print("🚀 TGsys Task Distribution Service Diagnostic")
    print("=" * 50)
    
    setup_logging()
    
    # Test configuration
    config_ok = await test_configuration()
    
    # Test PostgreSQL
    postgres_ok = await test_postgres_connection()
    
    # Test Kafka
    kafka_ok = await test_kafka_connection()
    
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary:")
    print(f"   Configuration: {'✅ OK' if config_ok else '❌ FAILED'}")
    print(f"   PostgreSQL:    {'✅ OK' if postgres_ok else '❌ FAILED'}")
    print(f"   Kafka:         {'✅ OK' if kafka_ok else '❌ FAILED'}")
    
    if config_ok and postgres_ok and kafka_ok:
        print("\n🎉 All tests passed! The service should start correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
