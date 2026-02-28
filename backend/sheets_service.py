import os
import json
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Service account credentials — the robot account
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# Scopes for Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Sheet column mapping — matches your exact sheet structure
# This makes it easy to change column order without touching logic
COLUMNS = {
    'ID': 0,              # A
    'Company': 1,         # B
    'Role': 2,            # C
    'Location': 3,        # D
    'Date Applied': 4,    # E
    'Date Responded': 5,  # F
    'Days Taken': 6,      # G
    'Status': 7,          # H
    'Interview Round': 8, # I
    'Source': 9,          # J
    'Email Thread ID': 10,# K
    'Notes': 11           # L
}


def get_sheets_service():
    """
    Authenticates using service account and returns Sheets API service.
    No browser login needed — service account handles it automatically.
    """
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=credentials)
    return service.spreadsheets()


def get_all_rows(sheets) -> list:
    """
    Fetches all rows from the sheet.
    Returns list of rows, each row is a list of cell values.
    Skips the header row.
    """
    try:
        result = sheets.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:L'
        ).execute()

        rows = result.get('values', [])

        # Skip header row, return data rows only
        return rows[1:] if len(rows) > 1 else []

    except Exception as e:
        print(f"Error fetching rows: {e}")
        return []


def generate_job_id(sheets) -> str:
    """
    Generates next Job ID like JOB001, JOB002 etc.
    Looks at existing rows to find the highest ID and increments.
    """
    rows = get_all_rows(sheets)

    if not rows:
        return 'JOB001'

    # Find highest existing job number
    max_num = 0
    for row in rows:
        if row and len(row) > 0:
            job_id = row[0]  # Column A
            if job_id.startswith('JOB'):
                try:
                    num = int(job_id[3:])  # Extract number after 'JOB'
                    max_num = max(max_num, num)
                except ValueError:
                    continue

    # Return next number with zero padding
    return f'JOB{str(max_num + 1).zfill(3)}'


def calculate_days_taken(date_applied: str, date_responded: str) -> str:
    """
    Calculates number of days between application and response.
    Returns empty string if either date is missing.
    """
    if not date_applied or not date_responded:
        return ''

    try:
        applied = datetime.strptime(date_applied, '%Y-%m-%d').date()
        responded = datetime.strptime(date_responded, '%Y-%m-%d').date()
        days = (responded - applied).days
        return str(days)
    except ValueError:
        return ''


def find_matching_row(sheets, company: str, role: str,
                      location: str = '', thread_id: str = '',
                      date_responded: str = '') -> tuple[int, list] | None:
    """
    Searches sheet for a row matching company + role.

    Matching priority:
    1. Thread ID exact match (most reliable)
    2. Company + Role + Location tiebreaker
    3. Company + Role + date proximity (most recent application)
    4. Final fallback — most recently added row
    """
    rows = get_all_rows(sheets)

    if not rows:
        return None

    company_lower = company.lower().strip()
    role_lower = role.lower().strip()

    # ── Priority 1: Thread ID match ──────────────────────────────────────────
    if thread_id:
        for i, row in enumerate(rows):
            while len(row) < 12:
                row.append('')
            row_thread_id = row[COLUMNS['Email Thread ID']]
            if row_thread_id and row_thread_id == thread_id:
                print(f"  Match found via Thread ID: {thread_id}")
                return (i, row)

    # ── Priority 2: Company + Role matching ──────────────────────────────────
    applied_matches = []

    for i, row in enumerate(rows):
        while len(row) < 12:
            row.append('')

        row_company = row[COLUMNS['Company']].lower().strip()
        row_role = row[COLUMNS['Role']].lower().strip()
        row_status = row[COLUMNS['Status']]

        company_match = (
            company_lower in row_company or
            row_company in company_lower
        )
        role_match = (
            role_lower in row_role or
            row_role in role_lower
        )

        # Only consider Applied rows — already closed ones are never updated
        if company_match and role_match and row_status == 'Applied':
            applied_matches.append((i, row))

    if not applied_matches:
        return None

    if len(applied_matches) == 1:
        print(f"  Single match found: {applied_matches[0][1][COLUMNS['ID']]}")
        return applied_matches[0]

    # ── Priority 3: Location tiebreaker ──────────────────────────────────────
    # Only used when multiple matches exist AND location is available
    if location:
        location_lower = location.lower().strip()
        for i, row in applied_matches:
            row_location = row[COLUMNS['Location']].lower().strip()
            if row_location and (
                location_lower in row_location or
                row_location in location_lower
            ):
                print(f"  Match found via location tiebreaker: "
                      f"{row[COLUMNS['ID']]} - {row[COLUMNS['Location']]}")
                return (i, row)

    # ── Priority 4: Date proximity ────────────────────────────────────────────
    # Pick Applied row whose date_applied is closest to date_responded
    print(f"  Multiple matches ({len(applied_matches)}), using date proximity")

    if date_responded:
        best_match = None
        best_date_diff = float('inf')

        for i, row in applied_matches:
            row_date_applied = row[COLUMNS['Date Applied']]
            if row_date_applied:
                try:
                    from datetime import datetime
                    applied_dt = datetime.strptime(row_date_applied, '%Y-%m-%d')
                    responded_dt = datetime.strptime(date_responded, '%Y-%m-%d')
                    diff = (responded_dt - applied_dt).days

                    # Must be positive — response must come after application
                    if 0 <= diff < best_date_diff:
                        best_date_diff = diff
                        best_match = (i, row)
                except ValueError:
                    continue

        if best_match:
            print(f"  Picked by date proximity: "
                  f"{best_match[1][COLUMNS['ID']]} "
                  f"({best_date_diff} days)")
            return best_match

    # ── Final fallback: most recently added row ───────────────────────────────
    last_match = applied_matches[-1]
    print(f"  Fallback — picked most recent row: {last_match[1][COLUMNS['ID']]}")
    return last_match


def create_new_row(sheets, parsed_data: dict, note_override: str = '') -> bool:
    """
    Creates a new row in the sheet for a new job application.
    Called when status is Applied OR when rejection arrives with no existing row.
    """
    try:
        job_id = generate_job_id(sheets)

        company = parsed_data.get('company', '')
        role = parsed_data.get('role', '')
        location = parsed_data.get('location', '')
        date_applied = parsed_data.get('date_applied', '')
        date_responded = parsed_data.get('date_responded', '')
        status = parsed_data.get('status', 'Applied')
        interview_round = parsed_data.get('interview_round', '')
        source = parsed_data.get('source', '')
        thread_id = parsed_data.get('thread_id', '')
        notes = note_override if note_override else parsed_data.get('notes', '')

        # Calculate days taken if both dates present
        days_taken = calculate_days_taken(date_applied, date_responded)

        # Build the row in exact column order
        new_row = [
            job_id,           # A - ID
            company,          # B - Company
            role,             # C - Role
            location,         # D - Location
            date_applied,     # E - Date Applied
            date_responded,   # F - Date Responded
            days_taken,       # G - Days Taken
            status,           # H - Status
            interview_round,  # I - Interview Round
            source,           # J - Source
            thread_id,        # K - Email Thread ID
            notes             # L - Notes
        ]

        # Append row to sheet
        sheets.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:L',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [new_row]}
        ).execute()

        print(f"Created new row: {job_id} - {company} - {role} - {status}")
        return True

    except Exception as e:
        print(f"Error creating row: {e}")
        return False


def update_existing_row(sheets, row_index: int, row_data: list, parsed_data: dict) -> bool:
    """
    Updates an existing row when rejection, interview, or offer arrives.
    Only updates relevant fields — preserves existing data.
    """
    try:
        # Pad row to full length
        while len(row_data) < 12:
            row_data.append('')

        # Update only these fields
        date_responded = parsed_data.get('date_responded', '')
        date_applied = row_data[COLUMNS['Date Applied']]
        new_status = parsed_data.get('status', '')
        interview_round = parsed_data.get('interview_round', '')
        notes = parsed_data.get('notes', '')

        # Calculate days taken now that we have both dates
        days_taken = calculate_days_taken(date_applied, date_responded)

        # Update the row data
        row_data[COLUMNS['Date Responded']] = date_responded
        row_data[COLUMNS['Days Taken']] = days_taken
        row_data[COLUMNS['Status']] = new_status
        if interview_round:
            row_data[COLUMNS['Interview Round']] = interview_round
        if notes:
            row_data[COLUMNS['Notes']] = notes

        # Sheet row number = row_index + 2
        # +1 because rows list is 0-indexed
        # +1 because header is row 1
        sheet_row_num = row_index + 2

        sheets.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'Sheet1!A{sheet_row_num}:L{sheet_row_num}',
            valueInputOption='RAW',
            body={'values': [row_data]}
        ).execute()

        job_id = row_data[COLUMNS['ID']]
        print(f"Updated row: {job_id} - {row_data[COLUMNS['Company']]} → {new_status}")
        return True

    except Exception as e:
        print(f"Error updating row: {e}")
        return False


def process_parsed_email(parsed_data: dict) -> bool:
    """
    Main function — takes LLM parsed data and writes/updates sheet.
    This is called from FastAPI after LLM parsing.

    Handles all cases:
    - Applied → create new row
    - Rejected/Interview/Offer + existing row → update row
    - Rejected/Interview/Offer + no existing row → create new row with note
    """
    sheets = get_sheets_service()
    status = parsed_data.get('status', '')
    company = parsed_data.get('company', '')
    role = parsed_data.get('role', '')
    location = parsed_data.get('location', '')

    if status == 'Applied':
        # Simple case — create new row
        return create_new_row(sheets, parsed_data)

    elif status in ['Rejected', 'Interview', 'Offer']:
        # Try to find existing row first
        match = find_matching_row(sheets, company, role, location)

        if match:
            row_index, row_data = match
            return update_existing_row(sheets, row_index, row_data, parsed_data)
        else:
            # No existing row found — create new one with note
            print(f"No existing row found for {company} - {role}. Creating new row.")
            return create_new_row(
                sheets,
                parsed_data,
                note_override=f"No confirmation email received. {parsed_data.get('notes', '')}"
            )
    else:
        print(f"Unknown status: {status}, skipping")
        return False