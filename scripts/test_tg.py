import asyncio
import sys

# Add project root to path for imports
sys.path.append('/Users/admin/Desktop/TGsys')

from shared.telegram_session_loader import TDataSessionLoader


async def main():
    """
    Example usage of TDataSessionLoader.
    """
    # Initialize the loader with tdata path and session name
    loader = TDataSessionLoader("sessions/tdata/account1/tdata", "account1.session")
    
    # Load and get the client
    client = await loader.load_client()
    
    # Print all logged-in sessions for verification
    await client.PrintSessions()


if __name__ == "__main__":
    asyncio.run(main())