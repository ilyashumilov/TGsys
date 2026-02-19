from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError, ConnectionError

from account_repository import TelegramAccount


@dataclass(frozen=True)
class ProxyConfig:
    """Configuration for a proxy server."""
    proxy_type: str  # 'http', 'socks4', 'socks5'
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def to_telethon_proxy(self) -> tuple:
        """Convert to Telethon proxy format."""
        if self.proxy_type.lower() == 'http':
            return (self.proxy_type, self.host, self.port, self.username, self.password)
        elif self.proxy_type.lower() in ['socks4', 'socks5']:
            return (self.proxy_type, self.host, self.port, self.username, self.password)
        else:
            raise ValueError(f"Unsupported proxy type: {self.proxy_type}")


class ProxyManager:
    """Manages proxy assignment and rotation for Telegram accounts."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._proxy_pool: List[ProxyConfig] = []
        self._account_proxy_map: Dict[int, ProxyConfig] = {}
        self._proxy_usage_count: Dict[str, int] = {}

    def load_proxy_pool(self, proxy_configs: List[ProxyConfig]) -> None:
        """Load proxy pool from configuration."""
        self._proxy_pool = proxy_configs
        self._logger.info(f"Loaded {len(proxy_configs)} proxies into pool")

    def assign_proxy_to_account(self, account: TelegramAccount) -> Optional[ProxyConfig]:
        """Assign a proxy to an account based on availability and usage."""
        if not self._proxy_pool:
            self._logger.warning("No proxies available in pool")
            return None

        # If account already has a proxy, return it
        if account.id in self._account_proxy_map:
            return self._account_proxy_map[account.id]

        # Select proxy with lowest usage count
        available_proxies = [p for p in self._proxy_pool if self._get_proxy_key(p) not in self._account_proxy_map.values()]
        
        if not available_proxies:
            self._logger.warning("No available proxies for assignment")
            return None

        # Sort by usage count (least used first)
        available_proxies.sort(key=lambda p: self._proxy_usage_count.get(self._get_proxy_key(p), 0))
        
        selected_proxy = available_proxies[0]
        self._account_proxy_map[account.id] = selected_proxy
        
        # Increment usage count
        proxy_key = self._get_proxy_key(selected_proxy)
        self._proxy_usage_count[proxy_key] = self._proxy_usage_count.get(proxy_key, 0) + 1
        
        self._logger.info(f"Assigned proxy {selected_proxy.host}:{selected_proxy.port} to account {account.api_id}")
        return selected_proxy

    def release_proxy_for_account(self, account_id: int) -> None:
        """Release proxy assignment for an account."""
        if account_id in self._account_proxy_map:
            proxy = self._account_proxy_map.pop(account_id)
            self._logger.info(f"Released proxy {proxy.host}:{proxy.port} from account {account_id}")

    def get_proxy_for_account(self, account_id: int) -> Optional[ProxyConfig]:
        """Get assigned proxy for an account."""
        return self._account_proxy_map.get(account_id)

    def _get_proxy_key(self, proxy: ProxyConfig) -> str:
        """Generate unique key for proxy."""
        return f"{proxy.host}:{proxy.port}"

    def get_proxy_stats(self) -> Dict[str, int]:
        """Get proxy usage statistics."""
        return self._proxy_usage_count.copy()

    def rotate_proxy_for_account(self, account: TelegramAccount) -> Optional[ProxyConfig]:
        """Rotate to a different proxy for an account."""
        # Release current proxy
        self.release_proxy_for_account(account.id)
        
        # Assign new proxy
        return self.assign_proxy_to_account(account)

    def create_telethon_client_with_proxy(
        self, 
        account: TelegramAccount, 
        session_name: str,
        retry_count: int = 3
    ) -> TelegramClient:
        """Create TelegramClient with proxy configuration and retry logic."""
        
        proxy = self.get_proxy_for_account(account.id)
        if not proxy:
            self._logger.warning(f"No proxy assigned to account {account.api_id}, using direct connection")
            return TelegramClient(session_name, account.api_id, account.api_hash)

        telethon_proxy = proxy.to_telethon_proxy()
        self._logger.info(f"Creating TelegramClient for account {account.api_id} via proxy {proxy.host}:{proxy.port}")
        
        for attempt in range(retry_count):
            try:
                client = TelegramClient(
                    session_name, 
                    account.api_id, 
                    account.api_hash,
                    proxy=telethon_proxy
                )
                
                # Test connection
                self._logger.info(f"Attempt {attempt + 1}: Testing proxy connection for account {account.api_id}")
                return client
                
            except (ConnectionError, OSError) as e:
                self._logger.warning(f"Proxy connection failed (attempt {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    # Try different proxy
                    new_proxy = self.rotate_proxy_for_account(account)
                    if new_proxy:
                        telethon_proxy = new_proxy.to_telethon_proxy()
                        self._logger.info(f"Rotating to new proxy: {new_proxy.host}:{new_proxy.port}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
            except Exception as e:
                self._logger.error(f"Unexpected error creating client (attempt {attempt + 1}): {e}")
                if attempt == retry_count - 1:
                    raise

        raise ConnectionError(f"Failed to create TelegramClient after {retry_count} attempts")

    @staticmethod
    def from_account_data(account_data: Dict) -> Optional[ProxyConfig]:
        """Create ProxyConfig from account database record."""
        if not account_data.get('proxy_host') or not account_data.get('proxy_port'):
            return None
            
        return ProxyConfig(
            proxy_type=account_data.get('proxy_type', 'socks5'),
            host=account_data['proxy_host'],
            port=account_data['proxy_port'],
            username=account_data.get('proxy_username'),
            password=account_data.get('proxy_password')
        )
