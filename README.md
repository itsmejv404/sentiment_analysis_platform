# BrandPulse

### Multi-Tenant Social Media Sentiment & Alert Pipeline

BrandPulse is a state-of-the-art enterprise-grade SaaS platform designed to ingest, clean, analyze, and alert organizations on social media sentiment trends in real-time. Built with a robust multi-tenant design, BrandPulse allows organizations to track their brand keyword mentions across platforms (like Reddit), run real-time natural language processing (NLP) pipelines, generate AI-powered insights, and trigger automated alerts when sentiment goes sour.

---

## System Architecture

```mermaid
graph TD
    %% Ingestion Pipeline
    Reddit[Reddit Search API] -->|JSON Ingestion| RedditProducer[Reddit Producer]
    DevConsole[Interactive Console] -->|Custom Post| CustomProducer[Custom Producer]
    
    %% Redis Queue
    RedditProducer -->|LPUSH payload| RedisQueue[(Redis: tweet_queue)]
    CustomProducer -->|LPUSH payload| RedisQueue
    
    %% Processing Worker
    RedisQueue -->|BRPOP payload| ProcWorker[Processing Worker]
    ProcWorker -->|Request Comments| Reddit
    ProcWorker -->|Clean & Format| ProcWorker
    ProcWorker -->|POST /analyze| MlApi[ML NLP API]
    
    %% NLP Stack
    subgraph ML NLP Service [ML NLP Core API]
        MlApi -->|Intent Detection| DeBERTa[DeBERTa-v3-base-zeroshot]
        MlApi -->|Irony & Sarcasm| RoBERTa[Twitter-RoBERTa-Irony]
        MlApi -->|Keyword Extraction| KeyBERT[KeyBERT]
        MlApi -->|Content Safety| SpamSVM[Custom TF-IDF SVM Classifier]
    end
    
    %% DB & Backend
    MlApi -->|Analysis Results| ProcWorker
    ProcWorker -->|Save ProductSentiment| Postgres[(PostgreSQL: social_db)]
    ProcWorker -->|Errors| DLQ[Dead Letter Queue]
    
    %% Backend & Client
    VueFrontend[Vue 3 Client] <--->|HTTP REST / Auth| FastAPI[FastAPI Backend]
    FastAPI <--->|SQLAlchemy| Postgres
    FastAPI -->|Enqueue Tasks| Celery[Celery Task Runner]
    Celery -->|SMTP Mail| MailHog[MailHog SMTP Server]
    
    %% Background Daemons
    AlertCron[Alert Cron Daemon] -->|Check Sentiment Thresholds| FastAPI
    BillingCron[Billing Cron Daemon] -->|Charge/Inactivate Tenants| FastAPI
    
    %% External Integrations
    FastAPI <--->|Verify Payments| Razorpay[Razorpay API]
    FastAPI <--->|Extract Insights| Groq[Groq AI Llama-3.1 API]
```

---

## Key Features

1. **Multi-Tenant SaaS Foundation**
   - Direct organization isolation: users are mapped to tenants with custom roles (`admin`, `manager`, `analyst`).
   - Secure invitation workflow via email tokens and complete tenant ownership transfer flow.
   - Default credit system: users get 500 free credits on sign-up.

2. **Ingestion & De-duplication Pipeline**
   - **Reddit Stream Producer**: Continuously queries the Reddit search JSON endpoint for active tenant keywords, enforcing rate-limit backing-off (429 handling) and de-duplication with a 24-hour Redis TTL cache.
   - **Interactive Developer Console**: Run manual mock text injection directly into the processing pipeline via `custom_producer.py`.
   - **Dead Letter Queue (DLQ)**: Automatic error recovery; failing jobs are stored in the database's `dead_letter_queue` table with payload and stack trace details for diagnosis.

3. **Advanced ML Sentiment & Classifier API**
   - **Intent Detection**: Uses zero-shot classification via the `DeBERTa-v3` transformer model to categorize posts into 7 intents: `QUESTION`, `REQUEST`, `COMPLAINT`, `COMPARISON`, `PRAISE`, `SALE`, or `DISCUSSION`.
   - **Irony & Sarcasm Checker**: Evaluates textual sarcasm using `twitter-roberta-base-irony`.
   - **Content Safety Guard**: Custom-trained machine learning model (Multinomial Naive Bayes + TF-IDF Vectorizer) to classify posts into `SAFE`, `PROMO/SPAM`, or `ADULT/NSFW`.
   - **Context Extraction Isolation**: Restricts long texts to sentences containing target brand names or products to prevent unrelated noise from diluting sentiment calculations.

4. **Groq AI Insights Engine**
   - Performs natural language understanding on analyst searches (e.g. *"Show me how people feel about battery life"*).
   - Dynamically extracts keywords/focus using Groq's Llama-3.1 LLM and automatically drafts rich executive sentiment summaries.

5. **Automated Alerting & Billing Systems**
   - **Alert Daemon**: Evaluates sentiment trends over a 12-hour sliding window. If negative or positive sentiment crosses the 70% threshold, it triggers automated alert emails to tenant admins (using Celery).
   - **Billing Daemon**: Deducts 100 credits/day for each active organization. If a user's credits fall below 100, the system automatically inactivates their tenants to protect computational resources, sending low-credit alerts.
   - **Razorpay Credit Store**: Integrated INR-based credits purchasing workflow.

---

## Project Structure

```text
brandpulse/
├── backend/            # FastAPI REST Web Server & Database Models
│   ├── celery/         # Celery tasks (invitations, alert emails, low credit emails)
│   ├── cron/           # Alert & Billing background daemons
│   ├── db/             # SQLAlchemy schemas, database connection pool, init & migration scripts
│   ├── groq/           # Groq API integration for LLM-powered query insights
│   ├── routes/         # REST API routers (Authentication, Admin/Analytics, Billing/Razorpay)
│   └── main.py         # App entrypoint & CORS middleware configuration
├── frontend/           # Vue 3 UI Application (Vite, Pinia, Vue Router)
│   ├── src/
│   │   ├── api/        # Axios API clients
│   │   ├── components/ # Shared layout components (DashboardLayout)
│   │   ├── views/      # Client views (Dashboard, Billing, Org Management, Auth)
│   │   └── main.js     # Vue initialization
│   └── package.json
├── ml/                 # Machine Learning Services & Sentiment Models
│   ├── jv.py           # FastAPI ML Inference Server (zero-shot, KeyBERT, custom SVM spam check)
│   ├── train_model.py  # Model trainer for the TF-IDF Naive Bayes spam classifier
│   └── spam.csv        # Classification dataset
├── producer/           # Real-Time Data Fetchers & Queuing Workers
│   ├── reddit_producer.py  # Ingests Reddit search feeds based on active keywords
│   ├── custom_producer.py  # Interactive CLI console to manually test posts
│   └── worker.py           # BRPOP queue consumer connecting Ingestors -> ML NLP API -> Postgres
└── start_all.ps1       # Orchestrator script to start all 8 services locally
```

---

## Setup & Installation

### Prerequisites
Make sure you have the following installed on your machine:
- **Python 3.10+**
- **Node.js 18+**
- **Redis Server** (listening on `localhost:6379`)
- **PostgreSQL Database** (listening on `localhost:5432`)
- **MailHog** (local SMTP test server listening on port `1025` with UI on `8025`)

---

### Step-by-Step Setup

#### 1. Setup the Database
Create a PostgreSQL database named `social_db`. Or, you can let the initialization script create it for you. 

Update the configuration in the backend:
Create `backend/.env` using `backend/.env.example` as a template:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/social_db
SECRET_KEY=generate-a-secure-random-key
ALGORITHM=HS256

SMTP_SERVER=localhost
SMTP_PORT=1025
DEFAULT_FROM_EMAIL=alerts@brandpulse.com

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

FRONTEND_URL=http://localhost:5173

RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
```

#### 2. Install Microservice Dependencies
Create virtual environments and install packages for all python services:

**Backend:**
```bash
cd backend
python -m venv .venv
# Activate virtual environment
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

**ML Service:**
```bash
cd ../ml
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Producer Service:**
```bash
cd ../producer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend Installation:**
```bash
cd ../frontend
npm install
```

---

### Running the Project

For ease of development, a PowerShell script is provided to spin up all **8 microservices** concurrently in separate terminal windows:

```powershell
./start_all.ps1
```

This launches:
1. **Backend FastAPI API** (Port `8000`)
2. **Celery Worker** (Handles email processing)
3. **Alert Cron Daemon** (Scans sentiment spikes hourly)
4. **Billing Cron Daemon** (Deducts credits, updates status)
5. **ML Sentiment API** (Port `8001`)
6. **Reddit Stream Producer** (Fetches keywords posts)
7. **Processing Worker** (Processes queue and calls ML API)
8. **Vue 3 Web App** (Port `5173`)

Access points:
- **Frontend App**: http://localhost:5173
- **Backend Swagger Docs**: http://localhost:8000/docs
- **ML NLP Endpoint**: http://localhost:8001/analyze
- **MailHog SMTP Web UI**: http://localhost:8025 (to view outgoing alerts/reset emails)

---

## Testing & Development

### Injecting Custom Test Data
To test the pipeline without waiting for live Reddit API data, run the interactive Custom Producer:
```bash
cd producer
# Activate venv
.venv\Scripts\activate
# Start interactive console
python custom_producer.py --interactive
```
*Type messages directly in the terminal, or include tags like `| keyword=battery engagement=25` to test specific metadata.*

### Retraining the Safety Classifier
If you wish to update the Spam/NSFW Naive Bayes classifier:
1. Place your data in `ml/combined_data.csv` (headers: `message`, `label` where label is 0=Safe, 1=Promo, 2=Adult).
2. Run the training script:
   ```bash
   cd ml
   .venv\Scripts\activate
   python train_model.py
   ```
3. This generates `spam_classifier_v3.pkl` which will automatically be loaded by the FastAPI ML server.
