import os
from dotenv import load_dotenv

load_dotenv()

# Google
GOOGLE_CLIENT_SECRET_FILE = os.getenv('GOOGLE_CLIENT_SECRET_FILE')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
PUBSUB_SUBSCRIPTION = os.getenv('PUBSUB_SUBSCRIPTION')

# Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# File paths
TOKEN_FILE = 'backend/credentials/token.json'
HISTORY_ID_FILE = 'backend/credentials/last_history_id.txt'


def get_last_history_id():
    """Read the last processed history ID from file."""
    try:
        with open(HISTORY_ID_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_history_id(history_id):
    """Save the latest history ID to file."""
    with open(HISTORY_ID_FILE, 'w') as f:
        f.write(str(history_id))