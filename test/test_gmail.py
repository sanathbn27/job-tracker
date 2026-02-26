from backend.gmail_service import get_gmail_service, get_recent_emails

print("Connecting to Gmail...")
service = get_gmail_service()
print("Connected successfully!")

print("\nFetching 3 most recent emails...")
emails = get_recent_emails(service, max_results=3)

for i, email in enumerate(emails, 1):
    print(f"\n--- Email {i} ---")
    print(f"From: {email['sender']}")
    print(f"Subject: {email['subject']}")
    print(f"Date: {email['date']}")
    print(f"Body preview: {email['body'][:200]}...")

