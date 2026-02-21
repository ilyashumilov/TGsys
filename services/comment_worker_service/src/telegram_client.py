from __future__ import annotations

import os
import logging
import sys
from typing import Optional
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, ChatWriteForbiddenError, UserDeactivatedBanError, UserDeactivatedError, PhoneNumberBannedError, AuthKeyUnregisteredError

from shared.telegram_session_loader import TDataSessionLoader


class TelegramCommentClient:
    """Telegram client for posting comments."""

    def __init__(self, api_id: int, api_hash: str, session_file: str, tdata_path: str = None):
        self._api_id = api_id
        self._api_hash = api_hash
        self.session_file = session_file
        self.tdata_path = tdata_path
        self._logger = logging.getLogger(__name__)
        self._client: Optional[TelegramClient] = None

    async def connect(self) -> bool:
        """Connect to Telegram."""
        try:
            proxy = None
            proxy_type = os.getenv("PROXY_TYPE")
            if proxy_type:
                proxy_host = os.getenv("PROXY_HOST")
                proxy_port = int(os.getenv("PROXY_PORT", "0"))
                proxy_username = os.getenv("PROXY_USERNAME")
                proxy_password = os.getenv("PROXY_PASSWORD")
                if proxy_type in ('socks5', 'http'):
                    proxy = (
                        proxy_type,
                        proxy_host,
                        proxy_port,
                        True,
                        proxy_username,
                        proxy_password
                    )

            loader = TDataSessionLoader(self.tdata_path, self.session_file)
            
            self._logger.info(f"self.tdata_path: {self.tdata_path}")
            self._client = await loader.load_client()

            await self._client.PrintSessions()

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
            # Get the channel entity
            chat = await self._client.get_entity(channel_username)

            self._logger.info("Chat: %s", chat)
            self._logger.info("Chat hasattr(chat, 'username'): %s", hasattr(chat, 'username'))

            # Join public channels if not already joined
            # if hasattr(chat, 'username') and chat.username:
            try:
                await self._client(JoinChannelRequest(chat))
                self._logger.info(f"Joined channel {channel_username}")
            except Exception as e:
                self._logger.warning(f"Failed to join channel {channel_username}: {e}")
            
            # Get the message to comment to
            message = await self._client.get_messages(chat, ids=message_id)
            if not message:
                self._logger.error(f"Message {message_id} not found in {channel_username}")
                return False
            
            # Post comment as reply
            if hasattr(chat, 'linked_chat_id') and chat.linked_chat_id:
                await self._client.send_message(chat.linked_chat_id, comment_text, reply_to_msg_id=message.id)
            else:
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
            
        # except ChatWriteForbiddenError:
            # self._logger.error("Cannot write to this chat (permissions revoked)")
            # return False
            
        except (UserDeactivatedBanError, UserDeactivatedError, PhoneNumberBannedError):
            self._logger.error("Account is banned or deactivated")
            return False
            
        except AuthKeyUnregisteredError:
            self._logger.error("Session is invalid or expired")
            return False
            
        except Exception as e:
            import traceback
            traceback.print_exc()
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
