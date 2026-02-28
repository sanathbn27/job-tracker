from backend.gmail_service import get_gmail_service, get_recent_emails
from backend.llm_parser import parse_job_email, determine_email_action

print("Fetching recent emails...")
service = get_gmail_service()
emails = get_recent_emails(service, max_results=10)

print(f"Found {len(emails)} emails\n")

relevant_count = 0
skipped_count = 0

for email in emails:
    print(f"\n{'='*50}")
    print(f"Subject: {email['subject']}")
    print(f"From: {email['sender']}")

    result = parse_job_email(email)

    if result is None:
        print("→ SKIPPED")
        skipped_count += 1
    else:
        action = determine_email_action(result)
        print(f"→ RELEVANT!")
        print(f"  Company: {result.get('company')}")
        print(f"  Role: {result.get('role')}")
        print(f"  Location: {result.get('location')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Date Applied: {result.get('date_applied')}")
        print(f"  Date Responded: {result.get('date_responded')}")
        print(f"  Interview Round: {result.get('interview_round')}")
        print(f"  Source: {result.get('source')}")
        print(f"  Action: {action}")
        relevant_count += 1

print(f"\n{'='*50}")
print(f"Summary: {relevant_count} relevant, {skipped_count} skipped")