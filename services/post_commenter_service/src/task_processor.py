from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError

from account_repository import TelegramAccount
from comment_generator import CommentGenerator
from session_manager import SessionManager
from worker_pool import WorkerPool


class TaskProcessor:
    """Processes Kafka events using available workers."""

    def __init__(
        self,
        session_manager: SessionManager,
        worker_pool: WorkerPool,
        comment_generator: CommentGenerator,
    ):
        self._session_manager = session_manager
        self._worker_pool = worker_pool
        self._comment_generator = comment_generator
        self._logger = logging.getLogger(__name__)

    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """Process a single post event and post a comment."""
        channel_id = event_data.get("channel_id")
        message_id = event_data.get("message_id")
        channel_identifier = event_data.get("channel_identifier")
        
        if not channel_id or not message_id:
            self._logger.error(f"Invalid event data: {event_data}")
            return False
        
        self._logger.info(f"Processing new post: {channel_identifier} (ID: {channel_id}), message: {message_id}")
        
        # Get available worker
        worker = await self._worker_pool.wait_for_available_worker(timeout=300)  # 5 minutes timeout
        if not worker:
            self._logger.error("No available workers to process event")
            return False
        
        try:
            success = await self._post_comment_with_worker(worker, channel_id, message_id, channel_identifier)
            return success
        finally:
            # Always release worker
            self._worker_pool.release_worker(worker.id)

    async def _post_comment_with_worker(
        self,
        worker: TelegramAccount,
        channel_id: int,
        message_id: int,
        channel_identifier: str,
    ) -> bool:
        """Post comment using specific worker account."""
        session_path = f"{self._session_manager._sessions_dir}/{worker.api_id}_session.session"
        
        if not self._session_manager.validate_session_file(session_path):
            self._logger.error(f"Invalid session file for worker {worker.api_id}")
            return False
        
        try:
            # Prepare writable session
            session_name = self._session_manager.prepare_writable_session(session_path)
            
            # Connect to Telegram
            async with TelegramClient(session_name, worker.api_id, worker.api_hash) as client:
                if not await client.is_user_authorized():
                    self._logger.error(f"Worker {worker.api_id} is not authorized")
                    return False
                
                self._logger.info(f"Connected with worker {worker.api_id}")
                
                # Generate comment
                comment = self._comment_generator.generate_comment()
                self._logger.info(f"Generated comment: {comment}")
                
                # Post comment
                await self._post_comment(client, channel_id, message_id, comment)
                
                # Set cooldown
                self._worker_pool.set_cooldown(worker)
                
                self._logger.info(f"Successfully posted comment with worker {worker.api_id}")
                return True
                
        except Exception as e:
            self._logger.error(f"Error posting comment with worker {worker.api_id}: {e}", exc_info=True)
            return False

    async def _post_comment(
        self,
        client: TelegramClient,
        channel_id: int,
        message_id: int,
        comment: str,
    ) -> None:
        """Post comment to Telegram message."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get message entity
                message = await client.get_messages(channel_id, ids=message_id)
                if not message:
                    raise ValueError(f"Message {message_id} not found in channel {channel_id}")
                
                # Post comment as a reply
                await message.reply(comment)
                self._logger.info(f"Comment posted successfully: {comment}")
                return
                
            except FloodWaitError as e:
                wait_time = e.seconds
                self._logger.warning(f"Flood wait for {wait_time}s (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (ChannelPrivateError, ChatAdminRequiredError) as e:
                self._logger.error(f"Cannot access channel: {e}")
                raise
            except Exception as e:
                self._logger.error(f"Error posting comment (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
