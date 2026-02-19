from __future__ import annotations

import logging
from typing import Optional

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserDeactivatedBanError,
    UserDeactivatedError,
    PhoneNumberBannedError,
)


class TelegramCommentClient:
    """Telegram client for posting comments."""

    def __init__(self, session_file: str, proxy_config: dict = None):
        self.session_file = session_file
        self.proxy_config = proxy_config
        self._logger = logging.getLogger(__name__)
        self._client: Optional[TelegramClient] = None

    async def connect(self) -> bool:
        """Connect to Telegram."""
        try:
            # Setup proxy if configured
            proxy = None
            if self.proxy_config and self.proxy_config.get('proxy_type'):
                if self.proxy_config['proxy_type'] == 'socks5':
                    proxy = (
                        self.proxy_config['proxy_type'],
                        self.proxy_config['proxy_host'],
                        self.proxy_config['proxy_port'],
                        True,  # rdns
                        self.proxy_config.get('proxy_username'),
                        self.proxy_config.get('proxy_password')
                    )
                elif self.proxy_config['proxy_type'] == 'http':
                    proxy = (
                        self.proxy_config['proxy_type'],
                        self.proxy_config['proxy_host'],
                        self.proxy_config['proxy_port'],
                        True,  # rdns
                        self.proxy_config.get('proxy_username'),
                        self.proxy_config.get('proxy_password')
                    )
            
            # Create client
            self._client = TelegramClient(
                self.session_file,
                proxy=proxy
            )
            
            await self._client.connect()
            
            # Check if authorized
            if not await self._client.is_user_authorized():
                self._logger.error("Session is not authorized")
                return False
            
            self._logger.info("Connected to Telegram successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to connect to Telegram: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._client:
            await self._client.disconnect()
            self._logger.info("Disconnected from Telegram")

    async def post_comment(self, channel_username: str, message_id: int, comment_text: str) -> bool:
        """Post a comment to a specific message."""
        if not self._client:
            raise RuntimeError("Client not connected")
        
        try:
            # Get the message to comment to
            message = await self._client.get_messages(channel_username, ids=message_id)
            if not message:
                self._logger.error(f"Message {message_id} not found in {channel_username}")
                return False
            
            # Post comment as reply
            await message.reply(comment_text)
            
            self._logger.info(
                f"✅ Posted comment to {channel_username}:{message_id} "
                f"'{comment_text[:50]}...'"
            )
            return True
            
        except FloodWaitError as e:
            self._logger.warning(f"Rate limited, wait {e.seconds} seconds")
            # Don't retry immediately, let the system handle it
            return False
            
        except ChatWriteForbiddenError:
            self._logger.error("Cannot write to this chat (permissions revoked)")
            return False
            
        except (UserDeactivatedBanError, UserDeactivatedError, PhoneNumberBannedError):
            self._logger.error("Account is banned or deactivated")
            return False
            
        except Exception as e:
            self._logger.error(f"Failed to post comment: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test if the connection is working."""
        if not self._client:
            return False
        
        try:
            # Try to get self info
            me = await self._client.get_me()
            if me:
                self._logger.info(f"Connection test passed: {me.first_name} {me.last_name}")
                return True
            return False
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            return False
