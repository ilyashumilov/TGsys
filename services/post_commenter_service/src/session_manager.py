from __future__ import annotations

import logging
import os
import shutil
from typing import Dict, List, Optional

from account_repository import AccountRepository, TelegramAccount


class SessionManager:
    """Manages Telegram session files and account discovery."""

    def __init__(self, sessions_dir: str, tracker_api_id: int):
        self._sessions_dir = sessions_dir
        self._tracker_api_id = tracker_api_id
        self._logger = logging.getLogger(__name__)

    def discover_session_files(self) -> Dict[int, str]:
        """Discover all session files in sessions directory."""
        session_files = {}
        
        if not os.path.exists(self._sessions_dir):
            self._logger.warning(f"Sessions directory does not exist: {self._sessions_dir}")
            return session_files

        for filename in os.listdir(self._sessions_dir):
            if filename.endswith("_session.session"):
                # Extract API ID from filename
                api_id_str = filename.replace("_session.session", "")
                try:
                    api_id = int(api_id_str)
                    # Skip tracker account
                    if api_id != self._tracker_api_id:
                        session_path = os.path.join(self._sessions_dir, filename)
                        session_files[api_id] = session_path
                        self._logger.debug(f"Found session file for API ID {api_id}: {filename}")
                except ValueError:
                    self._logger.warning(f"Invalid session filename format: {filename}")
                    continue

        self._logger.info(f"Discovered {len(session_files)} session files (excluding tracker)")
        return session_files

    def validate_session_file(self, session_path: str) -> bool:
        """Check if session file exists and is readable."""
        if not os.path.exists(session_path):
            self._logger.error(f"Session file not found: {session_path}")
            return False

        if not os.access(session_path, os.R_OK):
            self._logger.error(f"Session file not readable: {session_path}")
            return False

        # Check if file is not empty
        if os.path.getsize(session_path) == 0:
            self._logger.error(f"Session file is empty: {session_path}")
            return False

        return True

    def prepare_writable_session(self, session_path: str, runtime_dir: str = "/tmp") -> str:
        """Copy session file to writable runtime location."""
        os.makedirs(runtime_dir, exist_ok=True)
        
        filename = os.path.basename(session_path)
        runtime_session = os.path.join(runtime_dir, filename)
        
        # Copy to writable location
        shutil.copy2(session_path, runtime_session)
        
        # Return session name without .session extension for Telethon
        session_name = runtime_session[:-8] if runtime_session.endswith(".session") else runtime_session
        
        self._logger.debug(f"Prepared writable session: {session_name}")
        return session_name

    def sync_accounts_with_database(self, account_repo: AccountRepository) -> None:
        """Sync discovered session files with database accounts."""
        session_files = self.discover_session_files()
        db_accounts = account_repo.get_all_accounts()
        
        # Create a map of API ID to account for easy lookup
        account_map = {account.api_id: account for account in db_accounts}
        
        # Add new accounts from session files
        for api_id, session_path in session_files.items():
            if api_id not in account_map:
                # New account found, add to database
                if self.validate_session_file(session_path):
                    account_repo.add_account(api_id, "unknown")  # api_hash will be updated separately
                    self._logger.info(f"Added new account to database: API ID {api_id}")
                else:
                    self._logger.error(f"Skipping invalid session for API ID {api_id}")
            else:
                # Update session status based on file existence
                account = account_map[api_id]
                if self.validate_session_file(session_path):
                    if account.session_status != "authorized":
                        account_repo.update_session_status(account.id, "authorized")
                else:
                    if account.session_status == "authorized":
                        account_repo.update_session_status(account.id, "session_missing")
        
        # Mark accounts as inactive if no session file found
        for account in db_accounts:
            if account.api_id not in session_files and account.session_status != "session_missing":
                account_repo.update_session_status(account.id, "session_missing")
                self._logger.warning(f"No session file found for account API ID {account.api_id}")

    def get_available_accounts(self, account_repo: AccountRepository) -> List[TelegramAccount]:
        """Get accounts that have valid session files and are ready for use."""
        session_files = self.discover_session_files()
        available_accounts = []
        
        for account in account_repo.get_active_accounts():
            if account.api_id in session_files:
                session_path = session_files[account.api_id]
                if self.validate_session_file(session_path):
                    available_accounts.append(account)
                else:
                    # Mark as session missing
                    account_repo.update_session_status(account.id, "session_missing")
        
        self._logger.info(f"Found {len(available_accounts)} available accounts for commenting")
        return available_accounts
