# PF Intelligence Hub — Zambia 2026 Election Platform

Political intelligence platform for the Patriotic Front, focused on cost-of-living sentiment analysis ahead of the 13 August 2026 general election.

## Architecture

```
pf-intelligence/
├── backend/          # Python FastAPI server
│   ├── api/          # REST API routes
│   ├── scrapers/     # Facebook + news site scrapers
│   ├── nlp/          # Sentiment analysis pipeline
│   └── database/     # PostgreSQL models + migrations
└── frontend/         # Next.js 14 dashboard
    └── src/
        ├── components/
        ├── pages/
        ├── hooks/
        └── lib/
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 1. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your keys
alembic upgrade head            # run database migrations
uvicorn main:app --reload       # start API on :8000
```

### 2. Frontend setup
```bash
cd frontend
npm install
cp .env.example .env.local      # fill in API URL
npm run dev                     # start on :3000
```

### 3. Start scrapers (separate terminal)
```bash
cd backend
python -m scrapers.scheduler    # runs every 30 minutes
```

## Environment Variables

### Backend `.env`
```
DATABASE_URL=postgresql://user:pass@localhost:5432/pf_intel
REDIS_URL=redis://localhost:6379
META_ACCESS_TOKEN=your_meta_graph_api_token
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
SECRET_KEY=your_jwt_secret_key_min_32_chars
ALLOWED_ORIGINS=https://politicalintelligence.com,https://www.politicalintelligence.com
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_NAME=PF Intelligence Hub
```

## Key Features
- Social media monitoring (Facebook public pages + Zambian news sites)
- NLP sentiment analysis tuned for Zambian English
- Province-level grievance scoring across 10 provinces
- Live opinion poll engine with real-time results
- AI-powered campaign message generator
- Strategy dashboard with data-driven recommendations

## Data Sources Monitored
- Lusaka Times Facebook page
- Zambia Daily Mail Facebook page
- The Mast Online Facebook page
- Zambian Observer website
- Zambia Monitor website
- ZNBC Facebook page
- Public political Facebook groups (read-only)
