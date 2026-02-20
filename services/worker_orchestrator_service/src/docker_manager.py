from __future__ import annotations

import logging
from typing import Dict, Optional, List
import os
import docker
from docker.models.containers import Container


class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self._logger = logging.getLogger(__name__)
        self.worker_containers: Dict[int, Container] = {}

    async def deploy_worker_for_account(
        self, 
        account_id: int, 
        account_data: Dict,
        worker_image: str = "comment_worker:latest",
        network: str = "tgsys_default"
    ) -> Container:
        """Deploy worker container for specific account."""
        container_name = f"comment_worker_{account_id}"
        
        # Stop existing container if it exists
        await self.stop_worker(account_id)
        
        try:
            environment = {
                "ACCOUNT_ID": str(account_id),
                "TELEGRAM_SESSION_PATH": f"/app/sessions/{account_data['account_name']}_session.session",
                "TELEGRAM_TDATA_PATH": f"/app/sessions/tdata/{account_data['account_name']}/tdata",
                "TELEGRAM_API_ID": os.getenv("WORKER_API_ID", "10840"),
                "TELEGRAM_API_HASH": os.getenv("WORKER_API_HASH", "8e2e4c60c6ba4c7f7b9d4e4e6f0c0a2a"),
                "KAFKA_BROKER": "kafka:9092",
                "KAFKA_TOPIC": "comment-tasks",
                "KAFKA_CONSUMER_GROUP": f"worker-{account_id}",
            }
            
            # Add proxy configuration if available
            if account_data.get('proxy_type'):
                environment.update({
                    "PROXY_TYPE": account_data['proxy_type'],
                    "PROXY_HOST": account_data['proxy_host'],
                    "PROXY_PORT": str(account_data['proxy_port']),
                })
                
                if account_data.get('proxy_username'):
                    environment["PROXY_USERNAME"] = account_data['proxy_username']
                if account_data.get('proxy_password'):
                    environment["PROXY_PASSWORD"] = account_data['proxy_password']
            
            container = self.client.containers.run(
                worker_image,
                name=container_name,
                environment=environment,
                volumes={
                    os.getenv("SESSIONS_HOST_DIR", "/Users/admin/Desktop/TGsys/sessions"): {
                        "bind": "/app/sessions", 
                        "mode": "rw"
                    }
                },
                network=network,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            self.worker_containers[account_id] = container
            self._logger.info(f"Deployed worker container for account {account_id}: {container.id}")
            return container
            
        except Exception as e:
            self._logger.error(f"Failed to deploy worker for account {account_id}: {e}")
            raise

    async def stop_worker(self, account_id: int) -> bool:
        """Stop and remove worker container."""
        container_name = f"comment_worker_{account_id}"
        
        try:
            # Try to get existing container
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove()
            self._logger.info(f"Stopped worker container for account {account_id}")
            
            if account_id in self.worker_containers:
                del self.worker_containers[account_id]
            return True
            
        except docker.errors.NotFound:
            self._logger.info(f"Worker container for account {account_id} not found")
            if account_id in self.worker_containers:
                del self.worker_containers[account_id]
            return True
        except Exception as e:
            self._logger.error(f"Failed to stop worker for account {account_id}: {e}")
            return False

    async def restart_worker(self, account_id: int) -> bool:
        """Restart worker container."""
        try:
            container_name = f"comment_worker_{account_id}"
            container = self.client.containers.get(container_name)
            container.restart()
            self._logger.info(f"Restarted worker container for account {account_id}")
            return True
        except docker.errors.NotFound:
            self._logger.warning(f"Worker container for account {account_id} not found for restart")
            return False
        except Exception as e:
            self._logger.error(f"Failed to restart worker for account {account_id}: {e}")
            return False

    async def get_worker_status(self, account_id: int) -> Optional[Dict]:
        """Get status of worker container."""
        container_name = f"comment_worker_{account_id}"
        
        try:
            container = self.client.containers.get(container_name)
            container.reload()
            
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs["Created"],
                "state": container.attrs["State"]
            }
        except docker.errors.NotFound:
            return None
        except Exception as e:
            self._logger.error(f"Failed to get status for worker {account_id}: {e}")
            return None

    async def get_all_workers_status(self) -> Dict[int, Dict]:
        """Get status of all worker containers."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"name": "comment_worker_"}
            )
            
            status = {}
            for container in containers:
                if container.name.startswith("comment_worker_"):
                    try:
                        account_id = int(container.name.split("_")[-1])
                        container.reload()
                        status[account_id] = {
                            "id": container.id,
                            "name": container.name,
                            "status": container.status,
                            "state": container.attrs["State"]
                        }
                    except (ValueError, IndexError):
                        continue
            
            return status
        except Exception as e:
            self._logger.error(f"Failed to get all workers status: {e}")
            return {}

    async def cleanup_dead_workers(self) -> List[int]:
        """Remove dead worker containers."""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"name": "comment_worker_"}
            )
            
            removed_accounts = []
            for container in containers:
                if container.name.startswith("comment_worker_"):
                    container.reload()
                    if container.status == "exited":
                        try:
                            account_id = int(container.name.split("_")[-1])
                            container.remove()
                            removed_accounts.append(account_id)
                            self._logger.info(f"Cleaned up dead worker for account {account_id}")
                            
                            if account_id in self.worker_containers:
                                del self.worker_containers[account_id]
                        except (ValueError, IndexError):
                            continue
            
            return removed_accounts
        except Exception as e:
            self._logger.error(f"Failed to cleanup dead workers: {e}")
            return []

    def close(self):
        """Close Docker client connection."""
        self.client.close()
        self._logger.info("Docker client connection closed")
