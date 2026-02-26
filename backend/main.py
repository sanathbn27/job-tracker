import base64
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from backend.gmail_service import (
    get_gmail_service,
    start_gmail_watch,
    get_new_emails_since
)
from backend.config import (
    get_last_history_id,
    save_history_id
)


# ─── Lifespan Handler ───────────────────────────────────────────────────────
# This runs when FastAPI starts up and shuts down
# We use it to initialize Gmail service and start the watch

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Starting Job Tracker API...")

    # Initialize Gmail service globally so all endpoints can use it
    app.state.gmail_service = get_gmail_service()
    print("Gmail service initialized!")

    # Start/renew Gmail watch so Pub/Sub gets notifications
    watch_response = start_gmail_watch(app.state.gmail_service)
    if watch_response:
        # Save the latest history ID from watch response
        history_id = watch_response.get('historyId')
        if history_id:
            save_history_id(history_id)
        print(f"Gmail watch active. History ID: {history_id}")
    else:
        print("Warning: Gmail watch failed to start!")

    yield  # App runs here

    # SHUTDOWN
    print("Shutting down Job Tracker API...")


# ─── App Instance ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Job Tracker API",
    description="Automatically tracks job applications from Gmail",
    version="1.0.0",
    lifespan=lifespan
)


# ─── Health Check Endpoint ───────────────────────────────────────────────────
@app.get("/")
async def root():
    """
    Health check endpoint.
    Used by Railway and us to verify the app is running.
    """
    return {"status": "Job Tracker API is running!"}


# ─── Pub/Sub Endpoint ────────────────────────────────────────────────────────
@app.post("/pubsub")
async def receive_pubsub_notification(request: Request):
    """
    This endpoint receives push notifications from Google Pub/Sub.
    Called automatically by Pub/Sub whenever Gmail detects a new email.

    Pub/Sub message structure:
    {
        "message": {
            "data": "<base64 encoded json>",
            "messageId": "xxx",
            "publishTime": "xxx"
        },
        "subscription": "projects/xxx/subscriptions/gmail-sub"
    }
    """
    try:
        # Parse the incoming request body
        body = await request.json()

        # Extract the base64 encoded message data
        message = body.get('message', {})
        data_base64 = message.get('data', '')

        if not data_base64:
            print("No data in Pub/Sub message")
            # Still return 200 to prevent Pub/Sub from retrying
            return JSONResponse(status_code=200, content={"status": "no data"})

        # Decode base64 → bytes → string → dict
        # Gmail notification is JSON encoded in base64
        decoded_bytes = base64.b64decode(data_base64)
        decoded_str = decoded_bytes.decode('utf-8')
        notification = json.loads(decoded_str)

        print(f"Received Gmail notification: {notification}")

        # Extract email address and history ID from notification
        email_address = notification.get('emailAddress')
        new_history_id = notification.get('historyId')

        print(f"Email: {email_address}, New History ID: {new_history_id}")

        # Get last processed history ID
        last_history_id = get_last_history_id()

        if not last_history_id:
            print("No last history ID found, saving current and skipping")
            save_history_id(new_history_id)
            return JSONResponse(status_code=200, content={"status": "initialized"})

        # Fetch new emails since last history ID
        gmail_service = request.app.state.gmail_service
        new_emails = get_new_emails_since(gmail_service, last_history_id)

        print(f"Found {len(new_emails)} new email(s) to process")

        # Process each new email
        for email in new_emails:
            print(f"Processing: {email['subject']} from {email['sender']}")
            # TODO: Stage 6 — send to LLM parser
            # TODO: Stage 7 — write to Sheets and Excel

        # Save the new history ID for next time
        save_history_id(new_history_id)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "emails_processed": len(new_emails)
            }
        )

    except Exception as e:
        print(f"Error processing Pub/Sub notification: {e}")
        # ALWAYS return 200 to Pub/Sub even on error
        # Otherwise Pub/Sub will retry and we get duplicate processing
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )


# ─── Manual Trigger Endpoint ─────────────────────────────────────────────────
@app.get("/process-recent")
async def process_recent_emails(request: Request, limit: int = 5):
    """
    Manually trigger processing of recent emails.
    Useful for testing without waiting for a real email.
    Also useful for backfilling emails you received before the app was running.
    """
    try:
        from backend.gmail_service import get_recent_emails
        gmail_service = request.app.state.gmail_service
        emails = get_recent_emails(gmail_service, max_results=limit)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "emails_found": len(emails),
                "emails": [
                    {
                        "subject": e['subject'],
                        "sender": e['sender'],
                        "date": e['date']
                    }
                    for e in emails
                ]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))