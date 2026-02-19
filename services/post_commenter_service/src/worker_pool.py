from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set

from account_repository import AccountRepository, TelegramAccount


class WorkerPool:
    """Manages pool of Telegram workers with rate limiting."""

    def __init__(self, account_repo: AccountRepository, min_cooldown: int, max_cooldown: int):
        self._account_repo = account_repo
        self._min_cooldown = min_cooldown
        self._max_cooldown = max_cooldown
        self._logger = logging.getLogger(__name__)
        
        # Track currently busy workers
        self._busy_workers: Set[int] = set()
        
        # Cache for available workers
        self._available_cache: Optional[List[TelegramAccount]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=30)  # Cache for 30 seconds

    def get_available_worker(self) -> Optional[TelegramAccount]:
        """Get an available worker, excluding tracker account."""
        # Check cache first
        now = datetime.now(timezone.utc)
        if (self._available_cache is None or 
            self._cache_timestamp is None or 
            now - self._cache_timestamp > self._cache_ttl):
            
            # Refresh cache
            self._refresh_available_cache()
        
        if not self._available_cache:
            return None
        
        # Find a worker that's not currently busy
        available_workers = [
            account for account in self._available_cache 
            if account.id not in self._busy_workers
        ]
        
        if not available_workers:
            self._logger.debug("No available workers (all busy)")
            return None
        
        # Random selection from available workers
        selected_worker = random.choice(available_workers)
        self._busy_workers.add(selected_worker.id)
        
        self._logger.info(f"Selected worker {selected_worker.api_id} (ID: {selected_worker.id})")
        return selected_worker

    def release_worker(self, worker_id: int) -> None:
        """Release a worker back to the pool."""
        self._busy_workers.discard(worker_id)
        self._logger.debug(f"Released worker {worker_id}")

    def set_cooldown(self, worker: TelegramAccount) -> None:
        """Set cooldown for a worker."""
        # Generate random cooldown between min and max minutes
        cooldown_minutes = random.randint(self._min_cooldown, self._max_cooldown)
        cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)
        
        # Update database
        self._account_repo.set_cooldown(worker.id, cooldown_until)
        
        # Clear cache to force refresh
        self._available_cache = None
        self._cache_timestamp = None
        
        self._logger.info(f"Set {cooldown_minutes}min cooldown for worker {worker.api_id} until {cooldown_until}")

    def _refresh_available_cache(self) -> None:
        """Refresh cache of available workers."""
        self._available_cache = self._account_repo.get_active_accounts()
        self._cache_timestamp = datetime.now(timezone.utc)
        
        # Clean up busy workers that are no longer in available list
        available_ids = {account.id for account in self._available_cache}
        self._busy_workers.intersection_update(available_ids)
        
        self._logger.debug(f"Refreshed available workers cache: {len(self._available_cache)} workers")

    def get_pool_status(self) -> Dict[str, int]:
        """Get current pool status."""
        if self._available_cache is None:
            self._refresh_available_cache()
        
        total_accounts = len(self._available_cache) if self._available_cache else 0
        busy_count = len(self._busy_workers)
        available_count = total_accounts - busy_count
        
        return {
            "total_accounts": total_accounts,
            "busy_workers": busy_count,
            "available_workers": available_count,
        }

    async def wait_for_available_worker(self, timeout: Optional[int] = None) -> Optional[TelegramAccount]:
        """Wait for an available worker."""
        start_time = datetime.now(timezone.utc)
        
        while True:
            worker = self.get_available_worker()
            if worker:
                return worker
            
            # Check timeout
            if timeout and (datetime.now(timezone.utc) - start_time).total_seconds() > timeout:
                self._logger.warning("Timeout waiting for available worker")
                return None
            
            # Wait a bit before retrying
            self._logger.debug("No available workers, waiting...")
            await asyncio.sleep(5)  # Wait 5 seconds before retrying
