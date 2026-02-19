"""
Health check utilities for TGsys services.
"""

import asyncio
import logging
import sys
from typing import Dict, Any, Optional
import psycopg2
from kafka import KafkaProducer, KafkaConsumer
import time


class HealthChecker:
    """Base health checker for services."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_status = {
            "service": self.service_name,
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {}
        }
        
        # Perform individual checks
        checks = [
            self._check_memory_usage,
            self._check_disk_space,
        ]
        
        for check in checks:
            try:
                result = await check()
                health_status["checks"][result["name"]] = result
                if result["status"] != "healthy":
                    health_status["status"] = "unhealthy"
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                health_status["status"] = "unhealthy"
        
        return health_status
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "name": "memory",
                "status": "healthy" if memory.percent < 90 else "unhealthy",
                "details": {
                    "usage_percent": memory.percent,
                    "available_mb": memory.available // 1024 // 1024
                }
            }
        except ImportError:
            return {
                "name": "memory",
                "status": "unknown",
                "details": {"message": "psutil not available"}
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return {
                "name": "disk",
                "status": "healthy" if disk.percent < 90 else "unhealthy",
                "details": {
                    "usage_percent": disk.percent,
                    "free_gb": disk.free // 1024 // 1024 // 1024
                }
            }
        except ImportError:
            return {
                "name": "disk",
                "status": "unknown",
                "details": {"message": "psutil not available"}
            }


class DatabaseHealthChecker(HealthChecker):
    """Health checker for PostgreSQL connections."""
    
    def __init__(self, postgres_client):
        super().__init__("database")
        self.postgres_client = postgres_client
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform database health check."""
        health_status = await super().check_health()
        
        try:
            # Test database connection
            result = self.postgres_client.fetch_one("SELECT 1 as health_check")
            if result and result.get("health_check") == 1:
                health_status["checks"]["database_connection"] = {
                    "name": "database_connection",
                    "status": "healthy",
                    "details": {"message": "Database connection successful"}
                }
            else:
                health_status["checks"]["database_connection"] = {
                    "name": "database_connection",
                    "status": "unhealthy",
                    "details": {"message": "Database query failed"}
                }
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["database_connection"] = {
                "name": "database_connection",
                "status": "unhealthy",
                "details": {"error": str(e)}
            }
            health_status["status"] = "unhealthy"
        
        return health_status


class KafkaHealthChecker(HealthChecker):
    """Health checker for Kafka connections."""
    
    def __init__(self, kafka_broker: str):
        super().__init__("kafka")
        self.kafka_broker = kafka_broker
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform Kafka health check."""
        health_status = await super().check_health()
        
        try:
            # Test Kafka producer connection
            producer = KafkaProducer(
                bootstrap_servers=[self.kafka_broker],
                request_timeout_ms=5000,
                retries=0
            )
            
            # Try to get metadata
            metadata = producer.bootstrap_connected()
            producer.close()
            
            if metadata:
                health_status["checks"]["kafka_connection"] = {
                    "name": "kafka_connection",
                    "status": "healthy",
                    "details": {"broker": self.kafka_broker}
                }
            else:
                health_status["checks"]["kafka_connection"] = {
                    "name": "kafka_connection",
                    "status": "unhealthy",
                    "details": {"message": "Cannot connect to Kafka broker"}
                }
                health_status["status"] = "unhealthy"
                
        except Exception as e:
            health_status["checks"]["kafka_connection"] = {
                "name": "kafka_connection",
                "status": "unhealthy",
                "details": {"error": str(e)}
            }
            health_status["status"] = "unhealthy"
        
        return health_status


async def run_health_check(health_checker: HealthChecker) -> bool:
    """Run health check and return True if healthy."""
    try:
        health_status = await health_checker.check_health()
        if health_status["status"] != "healthy":
            logging.error(f"Health check failed: {health_status}")
            return False
        logging.info(f"Health check passed: {health_status['service']}")
        return True
    except Exception as e:
        logging.error(f"Health check error: {e}")
        return False


def main_health_check():
    """Main health check entry point for Docker health checks."""
    try:
        # Basic health check - just verify Python can import required modules
        import sys
        import json
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "python_version": sys.version
        }
        
        print(json.dumps(health_data))
        sys.exit(0)
        
    except Exception as e:
        error_data = {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }
        print(json.dumps(error_data))
        sys.exit(1)


if __name__ == "__main__":
    main_health_check()
