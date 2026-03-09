import base64
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from backend.gmail_service import (
    get_gmail_service,
    start_gmail_watch,
    get_new_emails_since,
    get_recent_emails
)
from backend.config import (
    get_last_history_id,
    save_history_id,
    load_processed_emails,
    save_processed_email
)
from backend.llm_parser import parse_job_email
from backend.sheets_service import process_parsed_email
from backend.excel_service import process_parsed_email_excel


# ─── Lifespan ────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    print("Starting Job Tracker API...")
    app.state.gmail_service = get_gmail_service()
    print("Gmail service initialized!")

    watch_response = start_gmail_watch(app.state.gmail_service)
    if watch_response:
        existing_history_id = get_last_history_id()
        if not existing_history_id:
            # Only save if we don't already have one
            history_id = watch_response.get('historyId')
            save_history_id(history_id)
            print(f"Gmail watch active. New History ID: {history_id}")
        else:
            print(f"Gmail watch active. Using existing History ID: {existing_history_id}")

    yield

    # SHUTDOWN
    print("Shutting down Job Tracker API...")


# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Job Tracker API",
    description="Automatically tracks job applications from Gmail",
    version="1.0.0",
    lifespan=lifespan
)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "Job Tracker API is running!"}


# ─── Pub/Sub Endpoint ─────────────────────────────────────────────────────────
@app.post("/pubsub")
async def receive_pubsub_notification(request: Request):
    """
    Receives push notifications from Google Pub/Sub.
    Called automatically when Gmail detects a new email.
    Always returns 200 OK to prevent Pub/Sub retries.
    """
    try:
        body = await request.json()
        message = body.get('message', {})
        data_base64 = message.get('data', '')

        if not data_base64:
            print("No data in Pub/Sub message")
            return JSONResponse(status_code=200, content={"status": "no data"})

        # Decode base64 → string → dict
        decoded_bytes = base64.b64decode(data_base64)
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        decoded_str = decoded_str.strip().lstrip('\ufeff')
        try:
            notification = json.loads(decoded_str)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in Pub/Sub message: {e}")
            return JSONResponse(status_code=200, content={"status": "invalid json"})

        print(f"Notification received: {notification}")

        new_history_id = notification.get('historyId')
        last_history_id = get_last_history_id()

        # Ignore stale notifications from Pub/Sub backlog
        if last_history_id and int(new_history_id) < int(last_history_id):
            print(f"Stale notification ({new_history_id} < {last_history_id}) — ignoring")
            return JSONResponse(status_code=200, content={"status": "stale"})

        if not last_history_id:
            print("No last history ID — saving current and skipping")
            save_history_id(new_history_id)
            return JSONResponse(status_code=200, content={"status": "initialized"})

        # Fetch new emails since last history ID
        gmail_service = request.app.state.gmail_service
        new_emails = get_new_emails_since(gmail_service, last_history_id)
        print(f"Found {len(new_emails)} new email(s)")

        # Process each email
        processed_count = 0
        for email in new_emails:
            email_id = email.get('id', '')

            # Deduplication check
            if email_id in load_processed_emails():
                print(f"Already processed: {email['subject']} — skipping")
                continue

            print(f"\nProcessing: {email['subject']}")
            print(f"From: {email['sender']}")

            # Parse with LLM
            parsed_data = parse_job_email(email)

            if parsed_data:
                sheets_success = process_parsed_email(parsed_data)
                excel_success = process_parsed_email_excel(parsed_data)
                print(f"Sheets: {'✓' if sheets_success else '✗'} "
                      f"Excel: {'✓' if excel_success else '✗'}")
                processed_count += 1

            # Mark as processed regardless of relevance
            save_processed_email(email_id)

        # Save new history ID
        # Only save if newer than current
        current_id = get_last_history_id()
        if not current_id or int(new_history_id) > int(current_id):
            save_history_id(new_history_id)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "emails_processed": processed_count
            }
        )

    except Exception as e:
        print(f"Error processing notification: {e}")
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )


# ─── Manual Trigger ───────────────────────────────────────────────────────────
@app.get("/process-recent")
async def process_recent_emails(request: Request, limit: int = 5):
    """
    Manually triggers processing of recent emails.
    Useful for testing and backfilling past applications.
    """
    try:
        gmail_service = request.app.state.gmail_service
        emails = get_recent_emails(gmail_service, max_results=limit)

        processed_count = 0
        skipped_count = 0

        for email in emails:
            email_id = email.get('id', '')

            if email_id in load_processed_emails():
                skipped_count += 1
                continue

            parsed_data = parse_job_email(email)

            if parsed_data:
                process_parsed_email(parsed_data)
                process_parsed_email_excel(parsed_data)
                processed_count += 1

            save_processed_email(email_id)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "processed": processed_count,
                "skipped_duplicates": skipped_count
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))