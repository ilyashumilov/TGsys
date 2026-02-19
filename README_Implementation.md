# TGsys Implementation Guide

## 🎯 Overview

This document provides a complete implementation of the TGsys Telegram automation system with the new architecture featuring:
- **Task Distribution Service** for intelligent account selection
- **Worker Orchestrator Service** for dynamic container management  
- **Comment Worker Service** for account-specific task execution
- **Simplified database schema** with comment counting

## 🏗️ Architecture Components

### Core Services

1. **Channel Parser Service** (existing)
   - Monitors Telegram channels for new posts
   - Publishes events to `telegram-last-post` topic

2. **Task Distribution Service** (new)
   - Consumes post events from Kafka
   - Selects best available account based on health and load balancing
   - Publishes tasks to `comment-tasks` topic

3. **Worker Orchestrator Service** (new)
   - Manages worker container lifecycle
   - Database-driven deployment
   - Session file management from template

4. **Comment Worker Service** (new)
   - Account-specific containers
   - Executes assigned comment tasks
   - Updates account statistics

### Database Schema

```sql
-- Simplified telegram_accounts table
CREATE TABLE telegram_accounts (
  id BIGSERIAL PRIMARY KEY,
  api_id BIGINT NOT NULL UNIQUE,
  api_hash TEXT NOT NULL,
  phone_number TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_comment_time TIMESTAMPTZ,
  comments_count INTEGER NOT NULL DEFAULT 0,
  health_score INTEGER NOT NULL DEFAULT 100,
  session_status TEXT NOT NULL DEFAULT 'unknown',
  proxy_type TEXT,
  proxy_host TEXT,
  proxy_port INTEGER,
  proxy_username TEXT,
  proxy_password TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose**
2. **Template Session File**: `sessions/33093187_session.session`
3. **Environment Variables**: Copy `.env.example` to `.env`

### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### Build and Start Services

```bash
# Build all services
docker-compose build

# Start core infrastructure
docker-compose up -d postgres zookeeper kafka

# Wait 30 seconds for services to be ready
sleep 30

# Start application services
docker-compose up -d channel_parser_service kafka_logger task_distribution_service worker_orchestrator_service
```

### Add Accounts to System

The Worker Orchestrator will automatically deploy workers for accounts in the database. Add accounts via SQL:

```sql
-- Add first account
INSERT INTO telegram_accounts (
  api_id, api_hash, phone_number,
  proxy_type, proxy_host, proxy_port,
  proxy_username, proxy_password,
  session_status
) VALUES (
  12345678, 'your_api_hash', '+1234567890',
  'socks5', 'proxy.example.com', 1080,
  'proxy_user', 'proxy_pass',
  'authorized'
);
```

## 📋 Service Details

### Task Distribution Service

**Purpose**: Intelligent task assignment to available accounts

**Features**:
- Selects accounts with lowest comment count (load balancing)
- Enforces 1-hour cooldown period
- Health score filtering (minimum 70)
- Automatic retry on failure

**Configuration**:
```yaml
MIN_HEALTH_SCORE: 70
COOLDOWN_HOURS: 1
MAX_RETRIES: 3
```

### Worker Orchestrator Service

**Purpose**: Dynamic worker container management

**Features**:
- Database-driven deployment
- Session file creation from template
- Container health monitoring
- Automatic cleanup of dead containers

**Container Management**:
- One container per account
- Account-specific environment variables
- Persistent session connections
- Automatic restart on failure

### Comment Worker Service

**Purpose**: Execute comment tasks for specific account

**Features**:
- Account-specific Kafka consumer
- Persistent Telegram session
- Proxy-bound connections
- Comment generation
- Health status reporting

**Environment Variables**:
```bash
ACCOUNT_ID=1
API_ID=12345678
API_HASH=your_api_hash
SESSION_FILE=/app/sessions/12345678_session.session
PROXY_TYPE=socks5
PROXY_HOST=proxy.example.com
PROXY_PORT=1080
```

## 🔄 Data Flow

```
1. Channel Parser → Kafka: New post detected
2. Task Distribution → Kafka: Consumes post event
3. Task Distribution → DB: Selects available account
4. Task Distribution → Kafka: Publishes comment task
5. Comment Worker → Kafka: Consumes assigned task
6. Comment Worker → Telegram: Posts comment via proxy
7. Comment Worker → DB: Updates account stats
```

## 📊 Monitoring & Health

### Account Health Scoring

- **Start**: 100 points
- **Success**: +1 point
- **Failure**: -5 points
- **Range**: 0-100 points
- **Minimum for tasks**: 70 points

### Load Balancing

Accounts selected tasks based:
1. **Availability** (not in cooldown, healthy)
2. **Comment Count** (lowest first)
3. **Health Score** (highest first)

### Container Health

Worker Orchestrator monitors:
- Container status (running/exited/dead)
- Health score updates
- Automatic restarts
- Dead container cleanup

## 🛠️ Management Operations

### Add New Account

```sql
INSERT INTO telegram_accounts (
  api_id, api_hash, phone_number,
  proxy_type, proxy_host, proxy_port,
  session_status
) VALUES (
  87654321, 'another_api_hash', '+0987654321',
  'socks5', 'proxy2.example.com', 1080,
  'unknown'
);
```

The orchestrator will automatically:
1. Create session file from template
2. Deploy worker container
3. Start monitoring health

### Remove Account

```sql
UPDATE telegram_accounts SET is_active = false WHERE id = 1;
```

The orchestrator will:
1. Stop worker container
2. Deactivate account in database
3. Clean up resources

### Check System Status

```bash
# View running containers
docker-compose ps

# Check service logs
docker-compose logs -f task_distribution_service
docker-compose logs -f worker_orchestrator_service

# Monitor specific worker
docker logs comment_worker_1
```

## 🔧 Troubleshooting

### Common Issues

**Worker containers not starting**:
- Check template session file exists
- Verify database connection
- Review orchestrator logs

**Tasks not being assigned**:
- Check account health scores
- Verify cooldown period
- Review task distributor logs

**Telegram connection failures**:
- Verify API credentials
- Check proxy configuration
- Review worker logs

### Debug Commands

```bash
# Check database
docker-compose exec postgres psql -U postgres -d tgsys -c "SELECT * FROM telegram_accounts;"

# Test Kafka topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# View worker deployment
docker-compose exec worker_orchestrator_service python -c "
import asyncio
from src.main import WorkerOrchestrator
# Add debugging code here
"
```

## 📈 Scaling

### From 10 to 200+ Accounts

The system scales automatically:

1. **Add accounts to database** - orchestrator deploys workers
2. **No compose file changes** - database-driven deployment
3. **Horizontal scaling** - each account isolated in container
4. **Load balancing** - automatic by comment count

### Resource Planning

**Per Account**:
- RAM: ~50MB per worker container
- CPU: Minimal (idle most of the time)
- Storage: Session file (~10KB)

**For 200 Accounts**:
- RAM: ~10GB total
- CPU: 2-4 cores sufficient
- Storage: ~2MB for sessions

## 🔒 Security Considerations

- **API Credentials**: Stored securely in database
- **Session Files**: Isolated per container
- **Proxy Configuration**: Account-specific binding
- **Network Isolation**: Docker network segmentation

## 🎯 Next Steps

1. **Deploy initial accounts** for testing
2. **Monitor system performance**
3. **Adjust health scoring** based on results
4. **Scale to production** account count
5. **Implement monitoring dashboards**

The system is now ready for production deployment with automatic scaling from 10 to 200+ accounts!
