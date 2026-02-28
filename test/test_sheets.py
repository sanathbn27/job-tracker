from backend.gmail_service import get_gmail_service, get_recent_emails
from backend.llm_parser import parse_job_email
from backend.sheets_service import process_parsed_email
from backend.excel_service import process_parsed_email_excel
from backend.config import load_processed_emails, save_processed_email

print("Fetching recent emails...")
service = get_gmail_service()
emails = get_recent_emails(service, max_results=10)

print(f"Found {len(emails)} emails\n")

relevant_count = 0
skipped_count = 0
duplicate_count = 0

for email in emails:
    print(f"\n{'='*50}")
    print(f"Subject: {email['subject']}")
    print(f"From: {email['sender']}")

    email_id = email.get('id', '')

    # Deduplication check
    if email_id in load_processed_emails():
        print("→ ALREADY PROCESSED — skipping")
        duplicate_count += 1
        continue

    parsed = parse_job_email(email)

    if parsed is None:
        print("→ SKIPPED (not relevant)")
        save_processed_email(email_id)
        skipped_count += 1
        continue

    print(f"→ RELEVANT!")
    print(f"  Company: {parsed.get('company')}")
    print(f"  Role: {parsed.get('role')}")
    print(f"  Status: {parsed.get('status')}")
    print(f"  Date Applied: {parsed.get('date_applied')}")
    print(f"  Date Responded: {parsed.get('date_responded')}")

    sheets_result = process_parsed_email(parsed)
    excel_result = process_parsed_email_excel(parsed)

    print(f"→ Sheets: {'✓' if sheets_result else '✗'}")
    print(f"→ Excel: {'✓' if excel_result else '✗'}")

    save_processed_email(email_id)
    relevant_count += 1

print(f"\n{'='*50}")
print(f"Summary:")
print(f"  Relevant and processed: {relevant_count}")
print(f"  Not relevant (skipped): {skipped_count}")
print(f"  Already processed (duplicates): {duplicate_count}")