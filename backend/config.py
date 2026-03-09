import os
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# ── Environment detection ─────────────────────────────────────────────────────
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None

# ── Google ────────────────────────────────────────────────────────────────────
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
PUBSUB_SUBSCRIPTION = os.getenv('PUBSUB_SUBSCRIPTION')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# ── Credential file paths (local only) ───────────────────────────────────────
_LOCAL_TOKEN_FILE           = 'backend/credentials/token.json'
_LOCAL_HISTORY_ID_FILE      = 'backend/credentials/last_history_id.txt'
_LOCAL_PROCESSED_FILE       = 'backend/credentials/processed_emails.json'
_LOCAL_CLIENT_SECRET_FILE   = os.getenv('GOOGLE_CLIENT_SECRET_FILE', '')
_LOCAL_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '')

# ── Write JSON env vars to temp files (Railway) ───────────────────────────────
def _write_temp_json(env_var_name: str) -> str:
    """Write JSON from environment variable to a temp file, return path."""
    content = os.getenv(env_var_name)
    if not content:
        return ''
    try:
        data = json.loads(content)
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(data, tmp)
        tmp.close()
        return tmp.name
    except json.JSONDecodeError as e:
        print(f"Error parsing {env_var_name}: {e}")
        return ''


def get_client_secret_file() -> str:
    """Returns path to client secret JSON — temp file on Railway, local path otherwise."""
    if IS_RAILWAY:
        return _write_temp_json('GOOGLE_CLIENT_SECRET_FILE')
    return _LOCAL_CLIENT_SECRET_FILE


def get_service_account_file() -> str:
    """Returns path to service account JSON — temp file on Railway, local path otherwise."""
    if IS_RAILWAY:
        return _write_temp_json('GOOGLE_SERVICE_ACCOUNT_FILE')
    return _LOCAL_SERVICE_ACCOUNT_FILE


# ── Token management ──────────────────────────────────────────────────────────
def get_token_file() -> str:
    """Returns path to token.json — temp file on Railway, local path otherwise."""
    if not IS_RAILWAY:
        return _LOCAL_TOKEN_FILE

    token_content = os.getenv('GOOGLE_TOKEN_JSON')
    if not token_content:
        return ''
    try:
        data = json.loads(token_content)
        tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        )
        json.dump(data, tmp)
        tmp.close()
        return tmp.name
    except json.JSONDecodeError as e:
        print(f"Error parsing GOOGLE_TOKEN_JSON: {e}")
        return ''


# ── History ID ────────────────────────────────────────────────────────────────
# On Railway: stored in memory (resets on restart, that's fine)
_memory_history_id = None

def get_last_history_id():
    """Read the last processed history ID."""
    if IS_RAILWAY:
        return _memory_history_id
    try:
        with open(_LOCAL_HISTORY_ID_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_history_id(history_id):
    """Save the latest history ID."""
    global _memory_history_id
    if IS_RAILWAY:
        _memory_history_id = str(history_id)
    else:
        with open(_LOCAL_HISTORY_ID_FILE, 'w', encoding='utf-8') as f:
            f.write(str(history_id))


# ── Processed emails ──────────────────────────────────────────────────────────
# On Railway: stored in memory (resets on restart, deduplication via sheet matching)
_memory_processed_emails = set()

def load_processed_emails() -> set:
    """Load set of already processed email IDs."""
    if IS_RAILWAY:
        return _memory_processed_emails
    try:
        with open(_LOCAL_PROCESSED_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_processed_email(email_id: str):
    """Add email ID to processed list."""
    global _memory_processed_emails
    if IS_RAILWAY:
        _memory_processed_emails.add(email_id)
    else:
        processed = load_processed_emails()
        processed.add(email_id)
        with open(_LOCAL_PROCESSED_FILE, 'w') as f:
            json.dump(list(processed), f)