# Telegram API Credentials Configuration
# 
# This file contains the API credentials for your TGsys setup.
# Copy this to api_credentials.py and fill in your actual values.

# Channel Parser Account (1 account - for monitoring channels)
CHANNEL_PARSER_CONFIG = {
    "api_id": 33093187,
    "api_hash": "YOUR_ACTUAL_API_HASH_HERE",  # Replace with your real API hash
    "phone_number": "YOUR_PHONE_NUMBER_HERE",  # Optional: for reference
    "session_file": "33093187_session.session"
}

# Comment Worker Accounts (n accounts - for posting comments)
# These will be generated from from your proxies.csv file
# You need to obtain API credentials for each account you want to use

# Example: If you have 5 accounts you want to use as from proxies.csv
COMMENT_WORKER_CONFIGS = [
    # {
    #     "api_id": 12345678,
    #     "api_hash": "ACCOUNT_1_API_HASH",
    #     "phone_number": "+1234567890"
    # },
    # {
    #     "api_id": 87654321,
    #     "api_hash": "ACCOUNT_2_API_HASH", 
    #     "phone_number": "+0987654321"
    # },
    # Add more accounts as needed
]

# How to get API credentials:
# 1. Go to https://my.telegram.org/apps
# 2. Sign in with your phone number
# 3. Create a new application
# 4. Copy the api_id and api_hash
# 5. Each account needs its own phone number and Telegram app

# Security Notes:
# - Never commit this file with real credentials to version control
# - Keep your API hashes secure - they're like passwords
# - Each account should have its own unique phone number
