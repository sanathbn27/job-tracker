import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv
from backend.config import get_token_file, get_client_secret_file

load_dotenv()

# These are the exact permissions asking Google 
# We ask for — reading and modifying gmail
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Save the token after first login
# So you don't have to log in every time
# TOKEN_FILE = 'backend/credentials/token.json'
# CLIENT_SECRET_FILE = os.getenv('GOOGLE_CLIENT_SECRET_FILE')


def get_gmail_service():
    """
    Authenticates with Gmail and returns a service object.
    First time: opens browser for you to log in.
    After that: uses saved token automatically.
    """
    creds = None

    # Check if we already have a saved token from a previous login
    token_file = get_token_file()
    client_secret_file = get_client_secret_file()

    if token_file and os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file, SCOPES
            )
            creds = flow.run_local_server(port=8888)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"Token saved to {token_file}")

    # Build and return the Gmail service object
    return build('gmail', 'v1', credentials=creds)


def get_email_by_id(service, email_id):
    """
    Fetches a single email by its ID and extracts subject, body, sender, date.
    """
    try:
        # Fetch the full email
        message = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        # Extract headers (subject, sender, date live here)
        headers = message['payload']['headers']
        subject = next(
            (h['value'] for h in headers if h['name'] == 'Subject'), 
            'No Subject'
        )
        sender = next(
            (h['value'] for h in headers if h['name'] == 'From'), 
            'Unknown Sender'
        )
        date = next(
            (h['value'] for h in headers if h['name'] == 'Date'), 
            'Unknown Date'
        )
        thread_id = message.get('threadId', '')

        # Extract email body — emails can be plain text or HTML
        body = extract_body(message['payload'])

        return {
            'id': email_id,
            'thread_id': thread_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body
        }

    except Exception as e:
        print(f"Error fetching email {email_id}: {e}")
        return None
    
def strip_html(html_text):
    """
    Removes HTML tags and cleans up whitespace.
    Gives us readable plain text from HTML emails.
    """
    import re
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', html_text)
    # Remove extra whitespace and blank lines
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Decode common HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    return clean


def extract_body(payload):
    """
    Extracts plain text body from email payload.
    Emails have a nested structure — this handles both simple and multipart emails.
    """
    body = ""

    # Simple email with direct body
    if 'parts' not in payload:
        mime_type = payload.get('mimeType', '')
        data = payload.get('body', {}).get('data', '')
        if data:
            decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            if mime_type == 'text/plain':
                return decoded
            elif mime_type == 'text/html':
                return strip_html(decoded)
        return body
    
    # Try plain text first
    for part in payload['parts']:
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                return body

    # Multipart email
    # Fall back to HTML if no plain text found
    for part in payload['parts']:
        if part.get('mimeType') == 'text/html':
            data = part.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                return strip_html(body)
        elif part.get('mimeType', '').startswith('multipart'):
            body = extract_body(part)
            if body:
                return body

    return body


def get_recent_emails(service, max_results=5):
    """
    Fetches the most recent emails from inbox.
    Useful for testing and initial setup.
    """
    try:
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            labelIds=['INBOX']
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            email = get_email_by_id(service, msg['id'])
            if email:
                emails.append(email)

        return emails

    except Exception as e:
        print(f"Error fetching recent emails: {e}")
        return []


def start_gmail_watch(service):
    """
    Tells Gmail to start pushing notifications to our Pub/Sub topic
    when new emails arrive.
    Must be called once to start watching and renewed every 7 days
    since Gmail watch expires after 7 days.
    """
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    topic_name = f"projects/{project_id}/topics/gmail-notifications"

    request_body = {
        'labelIds': ['INBOX'],        # Only watch inbox, not sent/spam
        'topicName': topic_name       # Where to send notifications
    }

    try:
        response = service.users().watch(
            userId='me',
            body=request_body
        ).execute()

        print(f"Gmail watch started successfully!")
        print(f"History ID: {response.get('historyId')}")
        print(f"Watch expires: {response.get('expiration')}")
        return response

    except Exception as e:
        print(f"Error starting Gmail watch: {e}")
        return None


def get_new_emails_since(service, history_id):
    """
    Fetches emails that arrived since a given history ID.
    Called every time Pub/Sub notifies us of a new email.
    """
    try:
        # Ask Gmail what changed since this history ID
        history = service.users().history().list(
            userId='me',
            startHistoryId=history_id,
            historyTypes=['messageAdded']  # Only care about new messages
        ).execute()

        new_emails = []
        changes = history.get('history', [])

        for change in changes:
            # Each change can have multiple new messages
            for msg in change.get('messagesAdded', []):
                message = msg.get('message', {})
                email_id = message.get('id')

                # Only process inbox emails, skip sent/drafts
                labels = message.get('labelIds', [])
                if 'INBOX' in labels:
                    email = get_email_by_id(service, email_id)
                    if email:
                        new_emails.append(email)

        return new_emails

    except Exception as e:
        print(f"Error fetching history: {e}")
        return []