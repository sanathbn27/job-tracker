from backend.gmail_service import get_gmail_service, start_gmail_watch

print("Connecting to Gmail...")
service = get_gmail_service()
print("Connected!")

print("\nStarting Gmail watch...")
response = start_gmail_watch(service)

if response:
    print("\nSuccess! Gmail will now push notifications to Pub/Sub.")
    print("Every new email in your inbox will trigger your FastAPI app.")
else:
    print("\nFailed to start watch. Check error above.")