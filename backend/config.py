import os
from dotenv import load_dotenv
import json

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

PROCESSED_EMAILS_FILE = 'backend/credentials/processed_emails.json'


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


def load_processed_emails() -> set:
    """Load set of already processed email IDs."""
    try:
        with open(PROCESSED_EMAILS_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_processed_email(email_id: str):
    """Add email ID to processed list."""
    processed = load_processed_emails()
    processed.add(email_id)
    with open(PROCESSED_EMAILS_FILE, 'w') as f:
        json.dump(list(processed), f)