from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from config import AppConfig, DockerConfig, PostgresConfig, setup_logging
from custom_clients.postgres_client import PostgresClient, PostgresConnection
from session_manager import SessionManager
from docker_manager import DockerManager


class WorkerOrchestrator:
    """Main service for managing comment worker containers dynamically."""

    def __init__(
        self,
        app_config: AppConfig,
        docker_config: DockerConfig,
        postgres_config: PostgresConfig,
    ):
        self._app_config = app_config
        self._docker_config = docker_config
        self._postgres_config = postgres_config
        self._logger = logging.getLogger(__name__)
        
        # Initialize components
        self._db: PostgresClient | None = None
        self._session_manager: SessionManager | None = None
        self._docker_manager: DockerManager | None = None
        
        self._running = False
        self._health_check_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start worker orchestrator service."""
        try:
            self._logger.info("Starting Worker Orchestrator Service...")
            
            # Initialize database connection
            self._db = PostgresClient(PostgresConnection(
                host=self._postgres_config.host,
                port=self._postgres_config.port,
                database=self._postgres_config.db,
                user=self._postgres_config.user,
                password=self._postgres_config.password,
            ))
            await self._db.connect()
            
            # Initialize session manager
            self._session_manager = SessionManager(
                sessions_dir=self._app_config.sessions_dir,
                template_session_path=self._app_config.template_session_file
            )
            
            # Initialize Docker manager
            self._docker_manager = DockerManager()
            
            # Deploy workers for all active accounts
            await self.sync_workers_with_database()
            
            # Start health monitoring
            self._running = True
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._logger.info("Worker Orchestrator Service started successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to start Worker Orchestrator Service: {e}")
            raise

    async def stop(self) -> None:
        """Stop worker orchestrator service."""
        self._logger.info("Stopping Worker Orchestrator Service...")
        
        self._running = False
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Close connections
        if self._docker_manager:
            self._docker_manager.close()
        
        if self._db:
            await self._db.close()
        
        self._logger.info("Worker Orchestrator Service stopped")

    async def sync_workers_with_database(self) -> None:
        """Deploy workers for all active accounts in database."""
        if not self._db or not self._session_manager or not self._docker_manager:
            raise RuntimeError("Service not properly initialized")
        
        try:
            accounts = await self._db.get_active_accounts()
            self._logger.info(f"Found {len(accounts)} active accounts")
            
            # Deploy workers for each account
            for account in accounts:
                try:
                    await self._deploy_worker_for_account(account)
                except Exception as e:
                    self._logger.error(f"Failed to deploy worker for account {account['id']}: {e}")
            
            # Cleanup dead containers
            dead_accounts = await self._docker_manager.cleanup_dead_workers()
            if dead_accounts:
                self._logger.info(f"Cleaned up {len(dead_accounts)} dead worker containers")
                
        except Exception as e:
            self._logger.error(f"Failed to sync workers with database: {e}")
            raise

    async def _deploy_worker_for_account(self, account: Dict[str, Any]) -> None:
        """Deploy worker container for specific account."""
        if not self._session_manager or not self._docker_manager:
            raise RuntimeError("Service not properly initialized")
        
        account_id = account['id']
        
        # Create session file if needed
        session_path = await self._session_manager.create_session_for_account(
            account_name=account['account_name'],
            phone_number=account.get('phone_number')
        )
        
        if not self._session_manager.validate_session_file(session_path):
            raise ValueError(f"Invalid session file: {session_path}")
        
        # Deploy worker container
        await self._docker_manager.deploy_worker_for_account(
            account_id=account_id,
            account_data=account,
            worker_image=self._docker_config.worker_image,
            network=self._docker_config.network
        )
        
        self._logger.info(f"✅ Deployed worker for account {account_id}")

    async def add_account(self, account_data: Dict[str, Any]) -> int:
        """Add new account and deploy worker."""
        if not self._db or not self._session_manager or not self._docker_manager:
            raise RuntimeError("Service not properly initialized")
        
        try:
            # Insert account into database
            account_id = await self._db.insert_account(account_data)
            
            # Get full account data
            account = await self._db.get_account(account_id)
            if not account:
                raise ValueError(f"Failed to retrieve inserted account {account_id}")
            
            # Deploy worker (assumes session file already exists)
            await self._deploy_worker_for_account(account)
            
            self._logger.info(f"✅ Added account {account_id} and deployed worker")
            return account_id
            
        except Exception as e:
            self._logger.error(f"Failed to add account: {e}")
            raise

    async def remove_account(self, account_id: int) -> bool:
        """Remove account and stop worker."""
        if not self._db or not self._docker_manager:
            raise RuntimeError("Service not properly initialized")
        
        try:
            # Stop worker container
            success = await self._docker_manager.stop_worker(account_id)
            
            # Deactivate account in database
            db_success = await self._db.deactivate_account(account_id)
            
            if success and db_success:
                self._logger.info(f"✅ Removed account {account_id}")
                return True
            else:
                self._logger.warning(f"Partial removal of account {account_id}")
                return False
                
        except Exception as e:
            self._logger.error(f"Failed to remove account {account_id}: {e}")
            return False

    async def _health_check_loop(self) -> None:
        """Periodic health monitoring of workers."""
        while self._running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._app_config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)  # Short retry delay

    async def _perform_health_check(self) -> None:
        """Perform health check on all workers."""
        if not self._db or not self._docker_manager:
            return
        
        try:
            workers_status = await self._docker_manager.get_all_workers_status()
            
            for account_id, status in workers_status.items():
                if status['status'] not in ['running']:
                    self._logger.warning(f"Worker {account_id} status: {status['status']}")
                    
                    # Update health score in database
                    if status['status'] == 'exited':
                        await self._db.update_account_health(account_id, 50)
                    elif status['status'] == 'dead':
                        await self._db.update_account_health(account_id, 0)
                        
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")


async def main() -> None:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    orchestrator = None
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        shutdown_event.set()
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Load configuration
        app_config = AppConfig.from_env()
        docker_config = DockerConfig.from_env()
        postgres_config = PostgresConfig.from_env()
        
        # Initialize and start orchestrator
        orchestrator = WorkerOrchestrator(app_config, docker_config, postgres_config)
        await orchestrator.start()
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        if orchestrator:
            await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
