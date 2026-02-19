# TGsys Architecture Diagrams

## 📋 Overview

This document contains PlantUML diagrams visualizing the TGsys Telegram automation system architecture.

## 🎯 Files

1. **`architecture.puml`** - High-level system overview
2. **`detailed_architecture.puml`** - Detailed component view

## 🖼️ Viewing the Diagrams

### Online Viewer
1. Go to [PlantUML Online Server](http://www.plantuml.com/plantuml/uml/)
2. Copy-paste the content of either `.puml` file
3. Click "Generate"

### Local Rendering
```bash
# Install PlantUML
brew install plantuml

# Generate PNG
plantuml architecture.puml
plantuml detailed_architecture.puml

# Generate SVG
plantuml -tsvg architecture.puml
plantuml -tsvg detailed_architecture.puml
```

### VS Code Extension
1. Install "PlantUML" extension
2. Open `.puml` files
3. Use command palette: "PlantUML: Preview"

## 🏗️ Architecture Components

### High-Level View (`architecture.puml`)
- **External Services**: Telegram API
- **Database**: PostgreSQL with channels and accounts
- **Message Queue**: Apache Kafka
- **Services**: Parser, Commenter, Logger
- **Storage**: Session files with proxy binding

### Detailed View (`detailed_architecture.puml`)
- **Component Breakdown**: Internal service components
- **Data Flow**: Step-by-step event processing
- **Proxy Management**: Fixed account-proxy binding
- **Rate Limiting**: Cooldown and worker pool logic

## 🔄 Data Flow

```
1. Telegram → Channel Parser (monitor posts)
2. Parser → PostgreSQL (update message IDs)
3. Parser → Kafka (publish events)
4. Kafka → Post Commenter (consume events)
5. Commenter → Database (get accounts, update cooldowns)
6. Commenter → Session Files (read with proxy binding)
7. Commenter → Telegram (post comments via proxy)
```

## 🔒 Proxy Architecture

### Fixed Binding Strategy
- **1 Account = 1 Proxy** (permanent)
- **No rotation** for account safety
- **Consistent IP** per account
- **Health monitoring** only

### Benefits
- ✅ Lower ban risk
- ✅ Account reputation building
- ✅ Consistent behavior patterns
- ✅ Simplified management

## 📊 Key Features

### Rate Limiting
- **10-30 minute** random cooldowns
- **Per-account** tracking
- **Worker pool** management
- **Natural** timing patterns

### Reliability
- **Manual Kafka acknowledgment**
- **No message loss**
- **Exactly-once processing**
- **Retry logic** with exponential backoff

### Scalability
- **Multi-account** support
- **Dynamic** account loading
- **Database-driven** configuration
- **Docker** containerization

## 🎯 System Benefits

1. **Safety**: Proxy protection prevents IP blocks
2. **Reliability**: Manual acknowledgment ensures no data loss
3. **Scalability**: Easy to add more accounts/proxies
4. **Monitoring**: Built-in logging and health checks
5. **Maintainability**: Clean microservices architecture

## 🚀 Next Steps

To view the complete architecture:
1. Open either `.puml` file in a PlantUML viewer
2. Review the component interactions
3. Understand the data flow patterns
4. Identify optimization opportunities

The diagrams provide both **high-level overview** and **detailed component view** for comprehensive system understanding!
