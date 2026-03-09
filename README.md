# 🗂️ Job Application Tracker

An end-to-end automated job application tracking system that monitors your Gmail inbox in real-time, parses emails using AI, and displays live analytics on an interactive dashboard.

## 🚀 Live Demo
- **Dashboard**: *coming soon*
- **API**: *coming soon*

## 🏗️ Architecture
```
Gmail Inbox
    ↓ (Push Notification)
Google Pub/Sub
    ↓ (Webhook)
FastAPI Backend
    ↓ (Email Content)
Groq LLM (Llama 3.3-70b)
    ↓ (Parsed Data)
Google Sheets + Excel
    ↓ (Live Sync)
Streamlit Dashboard
```

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11 |
| AI/LLM | Groq API (Llama 3.3-70b) |
| Email | Gmail API, Google Pub/Sub |
| Storage | Google Sheets, Excel (openpyxl) |
| Frontend | Streamlit, Plotly |
| Deployment | Railway (backend), Streamlit Cloud (frontend) |
| Container | Docker |

## 🔄 How It Works

1. **Email Arrives** — New email lands in Gmail inbox
2. **Push Notification** — Gmail pushes event to Google Pub/Sub topic
3. **Webhook Triggered** — FastAPI `/pubsub` endpoint receives notification
4. **Pre-filtering** — Rule-based filter skips job alerts, newsletters, spam
5. **LLM Parsing** — Groq parses email, extracts company, role, location, status
6. **Smart Matching** — 4-priority matching system links rejections to existing applications
7. **Auto Sync** — Data written to Google Sheets and Excel automatically
8. **Dashboard** — Streamlit shows real-time stats, charts and AI chat assistant

## 📊 Dashboard Features

- **Overview stats** — Total applied, pending, rejected, interviews, offers, response rate
- **Charts** — Applications over time, status breakdown pie chart
- **Smart filters** — Filter by status, date applied, date responded
- **AI Assistant** — Ask natural language questions about your job search
- **Auto refresh** — Dashboard syncs with Google Sheets every 60 seconds

## 🧠 LLM Email Parsing

- Supports emails in **English and German**
- Extracts: company, role, location, status, interview round, source
- Status classification: `Applied` / `Rejected` / `Interview` / `Offer`
- Pre-filter layer avoids wasting API tokens on job alerts and newsletters
- Temperature 0.1 for consistent structured output

## 🔗 Matching Logic

When a rejection or interview invite arrives, the system finds the right application using:

1. **Email Thread ID** — exact match (most reliable)
2. **Company + Role** — matches only `Applied` status rows
3. **Location tiebreaker** — when multiple matches exist
4. **Date proximity** — picks closest application date

## ⚠️ Known Limitations

- Companies with multiple applications and no role data
  may have imprecise matching — date proximity is used as fallback
- Some confirmation emails don't include role title — requires manual update
- Rejection emails without a matching confirmation create new rows 
  with empty Date Applied marked as "No confirmation email received"
- Groq free tier: 100,000 tokens/day — sufficient for ~50 emails/day

## 🐳 Docker
```bash
# Build
docker build -t job-tracker .

# Run locally
docker run --env-file .env -p 8000:8000 \
  -v ./backend/credentials:/app/backend/credentials \
  job-tracker
```

## 🔧 Local Setup
```bash
# Clone repo
git clone https://github.com/yourusername/job-tracker.git
cd job-tracker

# Create conda environment
conda create -n job-tracker python=3.11
conda activate job-tracker

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-frontend.txt

# Set up environment variables
cp .env.example .env
# Fill in your API keys

# Run backend
uvicorn backend.main:app --reload --port 8000

# Run frontend (separate terminal)
streamlit run frontend/dashboard.py
```

## 🌍 Environment Variables
```
GROQ_API_KEY=
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLIENT_SECRET_FILE=
GOOGLE_SERVICE_ACCOUNT_FILE=
SPREADSHEET_ID=
```

## 📁 Project Structure
```
job-tracker/
├── backend/
│   ├── main.py              # FastAPI app, Pub/Sub webhook
│   ├── gmail_service.py     # Gmail API integration
│   ├── llm_parser.py        # Groq email parsing
│   ├── llm_chat.py          # Dashboard chat assistant
│   ├── sheets_service.py    # Google Sheets sync
│   ├── excel_service.py     # Excel sync
│   ├── config.py            # Configuration helpers
│   └── prompts.yml          # LLM prompt templates
├── frontend/
│   ├── dashboard.py         # Streamlit dashboard
│   └── styles.py            # CSS and design components
├── test/
│   ├── test_watch.py        # Gmail watch setup
│   ├── test_parser.py       # LLM parser testing
│   └── test_sheets.py       # Sheets integration test
├── Dockerfile
├── docker-compose.yml
├── requirements.txt         # Backend dependencies
└── requirements-frontend.txt # Frontend dependencies
```

## 👤 Author

**Sanath** — Built as a personal productivity tool to automate job application tracking during an active job search in Germany.