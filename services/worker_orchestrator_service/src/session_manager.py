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
        account_name: str,
        phone_number: Optional[str] = None
    ) -> str:
        """Create session file for new account using template."""
        session_path = self.sessions_dir / f"{account_name}.session"
        
        if session_path.exists():
            self._logger.info(f"Session file already exists: {session_path}")
            return str(session_path)
        
        # Copy template session if it exists
        if self.template_session_path.exists():
            try:
                shutil.copy2(self.template_session_path, session_path)
                self._logger.info(f"Copied template session to: {session_path}")
                self._logger.warning(f"Session file copied for account {account_name}. Ensure it is authorized for this account.")
                return str(session_path)
            except Exception as e:
                self._logger.error(f"Failed to copy template session: {e}")
                raise
        else:
            self._logger.info(f"No template session found. Worker will load from tdata for account {account_name}.")
            return str(session_path)

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
