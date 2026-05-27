# CLAUDE.md — PF Intelligence Hub

Political intelligence platform for the Patriotic Front, Zambia 2026 general election (13 August 2026).

## Architecture

```
pf-intelligence/
├── backend/          # FastAPI (Python 3.11) — runs on :8000
│   ├── main.py       # All API routes
│   ├── config.py     # Settings via pydantic-settings (.env)
│   ├── database/     # SQLAlchemy async models + session factory
│   ├── nlp/          # Sentiment analysis (TextBlob + Zambian context)
│   └── scrapers/     # Facebook + news site scrapers + APScheduler
└── frontend/         # Next.js 14 + TypeScript + Tailwind — runs on :3000
    └── src/
        ├── pages/index.tsx   # Single-page dashboard (all tabs)
        └── lib/api.ts        # SWR hooks for every endpoint
```

## Running locally (Docker — recommended)

```bash
# Start Postgres + Redis + API + Frontend
docker compose up

# Seed polls (first run only)
docker compose exec api python database/seed_polls.py
```

## Running without Docker

### Backend (requires PostgreSQL 15+ and Redis 7+ running locally)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, META tokens, SECRET_KEY
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev   # starts on :3000
```

Health check: `curl http://localhost:8000/api/health`

## Import conventions

All Python imports in `backend/` are **absolute** (not relative dots).
Run uvicorn from the `backend/` directory: `uvicorn main:app`.
Sub-packages (`database/`, `nlp/`, `scrapers/`) each have `__init__.py`.

## API endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/dashboard/summary` | KPI hero row (7-day window) |
| `GET` | `/api/dashboard/issues` | Issue frequency for bar chart |
| `GET` | `/api/dashboard/provinces` | Grievance score per province |
| `GET` | `/api/posts` | Social feed with `issue`, `province`, `platform`, `sentiment` filters |
| `GET` | `/api/polls` | Active polls with live counts |
| `POST` | `/api/polls/respond` | Submit poll answer (one per IP per poll) |
| `GET` | `/api/polls/{id}/results` | Full poll results breakdown |

## Frontend tabs

`Dashboard` → KPIs, issue bars, sentiment pie, province grid  
`Social Feed` → filtered post list from DB  
`Opinion Polls` → live poll with real-time result reveal  
`Strategy` → static recs + "Generate campaign message" (calls Claude API — not yet wired)

## Database

PostgreSQL 16. SQLAlchemy async with `asyncpg`. Tables auto-created on startup via `init_db()`.
Keyword seed data auto-inserted on first run.

Alembic is configured (`alembic.ini`) but migrations not yet generated — use `alembic revision --autogenerate`.

## Environment variables (backend)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/pf_intel` |
| `REDIS_URL` | `redis://localhost:6379` |
| `META_ACCESS_TOKEN` | Meta Graph API token for Facebook scraper |
| `META_APP_ID` / `META_APP_SECRET` | Meta app credentials |
| `SECRET_KEY` | JWT signing key (min 32 chars) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins |

## Key design notes

- All endpoints return demo/seed data when the DB is empty — safe to test without scrapers running.
- Sentiment analysis (`nlp/sentiment.py`) uses TextBlob + Zambian phrase overrides; no external API needed.
- Facebook scraper requires a valid `META_ACCESS_TOKEN`; news scraper uses `httpx` + `beautifulsoup4`.
- "Generate campaign message" button on Strategy tab calls the Anthropic API — needs wiring up.
- Province grievance score formula: `(neg_pct × 70) + volume_bonus(max 20) + polarity_bonus(max 10)`.
