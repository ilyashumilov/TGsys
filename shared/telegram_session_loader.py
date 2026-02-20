from opentele.td import TDesktop
from opentele.tl import TelegramClient
from opentele.api import API, UseCurrentSession
import asyncio
import os


class TDataSessionLoader:
    """
    Class to load Telegram Desktop tdata and convert it to a Telethon session.
    Returns the authenticated Telethon client for reuse.
    """

    def __init__(self, tdata_folder: str, session_name: str):
        """
        Initialize with paths to tdata folder and desired session name.

        :param tdata_folder: Path to the tdata directory containing Telegram Desktop data.
        :param session_name: Name for the Telethon session file (without .session extension if not included).
        """
        self.tdata_folder = tdata_folder
        self.session_name = session_name

    async def load_client(self) -> TelegramClient:
        """
        Load tdata, convert to Telethon session, and return the connected client.

        :return: Authenticated Telethon TelegramClient.
        :raises AssertionError: If no accounts are loaded from tdata.
        """


        print('folder:', self.tdata_folder)
        # Load TDesktop client from tdata folder
        tdesk = TDesktop(self.tdata_folder)
        
        # Check if we have loaded any accounts
        assert tdesk.isLoaded(), f"No accounts found in tdata folder: {self.tdata_folder}"

        client = await tdesk.ToTelethon(session=self.session_name, flag=UseCurrentSession)
        
        # Connect to ensure the session is valid
        await client.connect()
        
        return client
