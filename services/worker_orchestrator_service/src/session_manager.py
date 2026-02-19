from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from telethon import TelegramClient


class SessionManager:
    def __init__(self, sessions_dir: str, template_session_path: str):
        self.sessions_dir = Path(sessions_dir)
        self.template_session_path = Path(template_session_path)
        self._logger = logging.getLogger(__name__)
        
        # Ensure sessions directory exists
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def create_session_for_account(
        self, 
        api_id: int, 
        api_hash: str, 
        phone_number: Optional[str] = None
    ) -> str:
        """Create session file for new account using template."""
        session_path = self.sessions_dir / f"{api_id}_session.session"
        
        if session_path.exists():
            self._logger.info(f"Session file already exists: {session_path}")
            return str(session_path)
        
        # Copy template session if it exists
        if self.template_session_path.exists():
            try:
                shutil.copy2(self.template_session_path, session_path)
                self._logger.info(f"Copied template session to: {session_path}")
                
                # Customize session for this account if phone is provided
                if phone_number:
                    await self._customize_session(session_path, api_id, api_hash, phone_number)
                
                return str(session_path)
            except Exception as e:
                self._logger.error(f"Failed to copy template session: {e}")
                raise
        else:
            # Create new session from scratch
            await self._create_new_session(session_path, api_id, api_hash, phone_number)
            return str(session_path)

    async def _customize_session(
        self, 
        session_path: Path, 
        api_id: int, 
        api_hash: str, 
        phone_number: str
    ) -> None:
        """Customize existing session with account credentials."""
        try:
            client = TelegramClient(str(session_path), api_id, api_hash)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone_number)
                code = input(f"Enter code for {phone_number}: ")
                await client.sign_in(phone_number, code)
            
            await client.disconnect()
            self._logger.info(f"Customized session for account {api_id}")
        except Exception as e:
            self._logger.error(f"Failed to customize session: {e}")
            # Remove corrupted session
            if session_path.exists():
                session_path.unlink()
            raise

    async def _create_new_session(
        self, 
        session_path: Path, 
        api_id: int, 
        api_hash: str, 
        phone_number: Optional[str] = None
    ) -> None:
        """Create brand new session file."""
        try:
            client = TelegramClient(str(session_path), api_id, api_hash)
            await client.connect()
            
            if phone_number:
                await client.send_code_request(phone_number)
                code = input(f"Enter code for {phone_number}: ")
                await client.sign_in(phone_number, code)
            
            await client.disconnect()
            self._logger.info(f"Created new session for account {api_id}")
        except Exception as e:
            self._logger.error(f"Failed to create session: {e}")
            # Remove corrupted session
            if session_path.exists():
                session_path.unlink()
            raise

    def validate_session_file(self, session_path: str) -> bool:
        """Validate session file integrity."""
        path = Path(session_path)
        if not path.exists():
            return False
        
        # Check file size (should be > 0 for valid session)
        return path.stat().st_size > 0

    def get_session_files(self) -> list[str]:
        """Get all session files."""
        return [str(f) for f in self.sessions_dir.glob("*_session.session")]
