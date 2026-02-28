import os
import json
import yaml
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# Load prompts from YAML file
PROMPTS_FILE = 'backend/prompts.yml'


def load_prompts() -> dict:
    """Load all prompts from the YAML file."""
    with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# ─── Pre-filter Lists ────────────────────────────────────────────────────────

BLACKLISTED_SENDERS = [
    'jobalerts-noreply@linkedin.com',
    'jobs@mail.xing.com',
    'info@jobagent.stepstone.de',
    'alerts@alerts.haystack.cv',
    'jobalert@indeed.com',
    'noreply@glassdoor.com',
    'noreply@monster.com',
]

BLACKLISTED_SUBJECT_KEYWORDS = [
    # English
    'new jobs match',
    'jobs matching your',
    'job alert',
    'jobs for you',
    'recommended jobs',
    'top jobs',
    'weekly jobs',
    'job recommendations',
    # German
    'neue jobs',
    'jobalert',
    'passende stellen',
    'stellenangebote für dich',
    'dein jobagent',
    'jobs die zu dir passen',
    'entdecke jobs',
    'ähnliche stellen',
    'beliebte stelle',
    'stellt ein',
    'is hiring',
]

WHITELISTED_SENDERS = [
    'myworkday.com',
    'personio.com',
    'greenhouse.io',
    'lever.co',
    'smartrecruiters.com',
    'successfactors.com',
    'taleo.net',
    'jobvite.com',
]


# ─── Pre-filter ──────────────────────────────────────────────────────────────

def should_send_to_llm(email: dict) -> tuple[bool, str]:
    """
    Pre-filters emails using simple rules before sending to LLM.
    Saves tokens and API calls by filtering obvious non-relevant emails.
    Returns (should_process, reason)
    """
    sender = email.get('sender', '').lower()
    subject = email.get('subject', '').lower()

    # Whitelisted senders — known ATS systems, always relevant
    for whitelisted in WHITELISTED_SENDERS:
        if whitelisted in sender:
            return True, f"Whitelisted ATS sender: {whitelisted}"

    # Blacklisted senders — known job alert senders
    for blacklisted in BLACKLISTED_SENDERS:
        if blacklisted in sender:
            return False, f"Blacklisted sender: {blacklisted}"

    # Blacklisted subject keywords — job alert patterns
    for keyword in BLACKLISTED_SUBJECT_KEYWORDS:
        if keyword in subject:
            return False, f"Job alert keyword detected: '{keyword}'"

    return True, "Passed pre-filter checks"


# ─── Date Extraction ─────────────────────────────────────────────────────────

def extract_date_from_email(email: dict) -> str:
    """
    Extracts and formats the email date as YYYY-MM-DD.
    This is used for both Date Applied and Date Responded
    depending on the email status.
    """
    date_str = email.get('date', '')
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')

    # Email dates come in various formats
    # Try common formats
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %z',      # Thu, 26 Feb 2026 12:01:27 +0000
        '%a, %d %b %Y %H:%M:%S %Z',      # Thu, 26 Feb 2026 12:01:27 UTC
        '%d %b %Y %H:%M:%S %z',           # 26 Feb 2026 12:01:27 +0000
        '%Y-%m-%dT%H:%M:%S%z',            # 2026-02-26T12:01:27+00:00
    ]

    for fmt in date_formats:
        try:
            # Remove parenthetical timezone info like "(UTC)"
            clean_date = date_str.split('(')[0].strip()
            parsed_date = datetime.strptime(clean_date, fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # If all formats fail, return today
    print(f"Could not parse date: {date_str}, using today")
    return datetime.now().strftime('%Y-%m-%d')


# ─── LLM Parser ──────────────────────────────────────────────────────────────

def parse_job_email(email: dict) -> dict | None:
    """
    Main function — takes raw email, returns structured job data or None.

    Flow:
    1. Pre-filter check (free, instant)
    2. Send to Groq LLM if passes filter
    3. Add date fields based on status
    4. Return structured data
    """

    # Step 1 — Pre-filter
    should_process, reason = should_send_to_llm(email)
    print(f"  Pre-filter: {reason}")

    if not should_process:
        return None

    # Step 2 — Load prompt from YAML
    prompts = load_prompts()
    parser_prompt = prompts['email_parser']

    # Fill in the prompt template with email data
    user_prompt = parser_prompt['user'].format(
        sender=email.get('sender', ''),
        subject=email.get('subject', ''),
        date=email.get('date', ''),
        body=email.get('body', '')[:3000]  # Limit body to save tokens
    )

    # Step 3 — Call Groq LLM
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": parser_prompt['system']
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.1,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()
        print(f"  LLM Raw Response: {response_text}")

        # Clean markdown if LLM adds it despite instructions
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(response_text)

        # Not relevant according to LLM
        if not parsed.get('relevant', False):
            print(f"  LLM: Not relevant")
            return None

        # Step 4 — Add date fields based on status
        # Date logic:
        # Applied → date_applied = email date, date_responded = empty
        # Rejected/Interview/Offer → date_applied = empty, date_responded = email date
        email_date = extract_date_from_email(email)
        status = parsed.get('status', '')

        if status == 'Applied':
            parsed['date_applied'] = email_date
            parsed['date_responded'] = ''
            parsed['needs_matching'] = False
        else:
            # Rejection, Interview, Offer
            parsed['date_applied'] = ''
            parsed['date_responded'] = email_date
            parsed['needs_matching'] = True  # We will try to match these to existing applications in Sheets/Excel

        # Step 5 — Add Gmail metadata
        parsed['thread_id'] = email.get('thread_id', '')
        parsed['email_id'] = email.get('id', '')

        print(f"  Extracted → Company: {parsed.get('company')}, "
              f"Role: {parsed.get('role')}, "
              f"Status: {parsed.get('status')}, "
              f"Date Applied: {parsed.get('date_applied')}, "
              f"Date Responded: {parsed.get('date_responded')}")

        return parsed

    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e} | Raw: {response_text}")
        return None

    except Exception as e:
        print(f"  LLM error: {e}")
        return None


# ─── Action Determiner ───────────────────────────────────────────────────────

def determine_email_action(parsed_data: dict) -> str:
    """
    Determines what sheet action to take based on email status.
    Applied → create new row
    Rejected/Interview/Offer → update existing row
    """
    status = parsed_data.get('status', '')

    if status == 'Applied':
        return 'create'
    elif status in ['Rejected', 'Interview', 'Offer']:
        return 'update'
    else:
        return 'skip'