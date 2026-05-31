# PF Intelligence Hub — Technical README
## Patriotic Front Zambia · 2026 General Election Platform
**Last updated:** 31 May 2026  
**Election date:** 13 August 2026 (74 days)  
**Production URL:** https://politicalintelligence.com  
**GitHub:** https://github.com/Knox8907/pf-intelligence  
**Classification:** Confidential — Internal Technical Use Only

---

## Table of Contents

1. [What It Does](#1-what-it-does)
2. [Architecture Overview](#2-architecture-overview)
3. [Tech Stack](#3-tech-stack)
4. [Dashboard Sections](#4-dashboard-sections)
5. [API Reference](#5-api-reference)
6. [Database Schema](#6-database-schema)
7. [NLP Pipeline](#7-nlp-pipeline)
8. [Data Sources](#8-data-sources)
9. [Local Development](#9-local-development)
10. [Production Deployment](#10-production-deployment)
11. [Environment Variables](#11-environment-variables)
12. [Vote Protection System](#12-vote-protection-system)
13. [Security Model](#13-security-model)
14. [Pending Work](#14-pending-work)

---

## 1. What It Does

The PF Intelligence Hub is a private web platform giving the Patriotic Front real-time political intelligence ahead of the 13 August 2026 Zambia general election. It does four things:

1. **Monitors** — scrapes 22 Facebook pages and 10 news websites every 30 minutes, 24/7
2. **Analyses** — classifies every post by sentiment (positive/negative/neutral), issue (mealie meal, fuel, ZESCO, etc.), and province using a custom NLP pipeline tuned for Zambian English
3. **Strategises** — surfaces a province grievance heatmap, issue frequency charts, and AI-generated campaign messages via Claude Opus 4.7
4. **Protects** — provides a parallel vote tabulation system loaded with the ECZ official 2026 voter register (99.9% of all polling stations), enabling real-time election-night monitoring and fraud detection

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      nginx (port 80/443)                 │
│              HTTP → HTTPS redirect + reverse proxy       │
└────────────────┬────────────────────┬────────────────────┘
                 │                    │
         ┌───────▼──────┐    ┌────────▼───────┐
         │  Next.js 14  │    │  FastAPI :8000  │
         │  frontend    │    │  backend        │
         │  :3000       │    │                 │
         └──────────────┘    └────────┬────────┘
                                      │
                        ┌─────────────┼─────────────┐
                        │             │             │
               ┌────────▼───┐  ┌──────▼─────┐  ┌───▼──────────┐
               │ PostgreSQL │  │   Redis 7  │  │  Anthropic   │
               │ 16 (db)    │  │  (queue)   │  │  Claude API  │
               └────────────┘  └────────────┘  └──────────────┘
```

**All four services** (api, frontend, db, redis) run as Docker containers orchestrated by `docker-compose.prod.yml`. nginx handles all incoming traffic and terminates SSL.

**File layout:**

```
pf-intelligence/
├── backend/
│   ├── main.py                     # FastAPI app — all API routes
│   ├── config.py                   # Settings from .env
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── parse_voter_register.py     # ECZ PDF parser (one-time use)
│   ├── database/
│   │   ├── connection.py           # Async SQLAlchemy engine + init_db()
│   │   ├── models.py               # ORM models for all tables
│   │   ├── seed_polls.py           # Seeds initial poll questions
│   │   └── migrations/
│   │       ├── env.py              # Alembic environment
│   │       └── voter_register_seed.sql.gz   # 382 KB — auto-loads on first boot
│   ├── nlp/
│   │   └── sentiment.py            # Sentiment + issue + province detection
│   └── scrapers/
│       ├── facebook_scraper.py     # Meta Graph API scraper (22 pages)
│       ├── news_scraper.py         # BeautifulSoup news site scraper
│       └── scheduler.py            # APScheduler — runs every 30 minutes
├── frontend/
│   └── src/
│       ├── pages/index.tsx         # Single-page app (all 5 tabs)
│       ├── pages/_app.tsx
│       ├── lib/api.ts              # All API calls
│       └── styles/globals.css
├── nginx/
│   └── nginx.conf                  # HTTP→HTTPS redirect + SSL termination
├── docs/
│   ├── PF_Intelligence_Hub_Project_Brief_2026.md
│   └── PF_Intelligence_Hub_Budget_2026.md
├── docker-compose.yml              # Local development
├── docker-compose.prod.yml         # Production
└── deploy.sh                       # One-command server setup script
```

---

## 3. Tech Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Backend | Python / FastAPI | 3.12 / 0.115 | Async throughout (`asyncpg`, `AsyncSession`) |
| Frontend | Next.js | 14 | Static export; Tailwind CSS; TypeScript |
| Database | PostgreSQL | 16 | Managed via SQLAlchemy ORM + raw SQL for vote protection queries |
| Cache / Queue | Redis | 7 | Scraper job queue |
| NLP | TextBlob + custom rules | — | Zambian context overrides; no GPU required |
| AI | Anthropic Claude Opus 4.7 | — | Streaming campaign message generation with adaptive thinking |
| Auth | JWT (HS256) | 24-hour expiry | `python-jose` + `passlib[bcrypt]` |
| Containerisation | Docker + Docker Compose | — | Production: `docker-compose.prod.yml` |
| Web server | nginx | alpine | Reverse proxy + SSL termination |
| SSL | Let's Encrypt (certbot) | — | Auto-renewing; cert path: `/etc/letsencrypt/live/politicalintelligence.com/` |
| Hosting | DigitalOcean Droplet | Ubuntu 24.04 | 4 vCPU, 8 GB RAM (recommended) |

---

## 4. Dashboard Sections

### Section 1 — Dashboard (Command Centre)

The landing view after login. Shows:

- **Countdown** — live days, hours, minutes, seconds to 13 August 2026
- **KPI row** — total posts tracked (7-day window), negative sentiment %, top issue this week, total poll responses
- **Issue Frequency Chart** — bar chart ranking mealie meal, fuel, ZESCO, unemployment, kwacha, fertiliser, school fees by share of posts mentioning each
- **Sentiment Breakdown** — donut of negative / neutral / positive
- **Province Grievance Heatmap** — all 10 provinces scored 0–100 (higher = more public grievance = more opportunity). Score formula: `(neg_pct × 70) + volume_bonus(max 20) + polarity_bonus(max 10)`

Falls back to demo data when the database has no scraped posts yet.

### Section 2 — Social Feed

Live scrolling feed of all scraped posts and articles. Each card shows source name, platform badge, province tag, sentiment chip, issue tags, likes/comments, and relative time.

**Filters:** platform (Facebook/news), sentiment, province, issue, source name  
**Export:** "Export CSV" button downloads all matching posts as `pf_intel_posts_YYYYMMDD_HHMM.csv`

### Section 3 — Opinion Polls

Built-in polling module. Respondents select their province before answering. Results update live. One response per IP per poll (hashed, not stored in plain text). Active polls:

- "What is your single biggest financial concern right now?"
- "Has your household's cost of living improved, stayed the same, or worsened since UPND took power in 2021?"

Results show per-option percentage with a live bar. After submission, the respondent sees the full result breakdown — which encourages sharing.

### Section 4 — Vote Protection

Election-day parallel tabulation system. See [Section 12](#12-vote-protection-system) for full detail.

### Section 5 — Strategy

Two tools:

**A. Strategic Recommendations** — five data-driven recommendations auto-generated from the live sentiment and issue data:
1. Lead with mealie meal
2. Lusaka and Copperbelt are decisive battlegrounds
3. ZESCO is Copperbelt's number-one issue
4. Youth unemployment is the fastest-growing grievance
5. Frame 2026 as forward-looking, not retrospective

**B. AI Campaign Message Generator** — select a province and an issue, click Generate. Streams a 150–200 word campaign message from Claude Opus 4.7 using adaptive thinking. The system prompt briefs the model on specific price data (mealie meal ZMW 150 → ZMW 340+), ZESCO outage hours, youth unemployment statistics, kwacha depreciation, and PF policy positions.

---

## 5. API Reference

All endpoints except `/api/polls`, `/api/polls/respond`, `/api/polls/{id}/results`, `/api/voter-register/*`, `/api/tabulation/*`, and `/api/health` require a **Bearer token** obtained from `/api/auth/login`.

### Auth

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/auth/login` | `{email, password}` | `{access_token, token_type}` |

### Dashboard

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/dashboard/summary` | `{total_mentions, negative_pct, positive_pct, neutral_pct, top_issue, poll_responses, week_start}` |
| `GET` | `/api/dashboard/issues` | Array of `{issue, display, count, pct}` sorted by count desc |
| `GET` | `/api/dashboard/provinces` | Array of `{province, score, post_count, neg_pct, top_issue}` sorted by score desc |

### Social Feed

| Method | Path | Query params | Returns |
|---|---|---|---|
| `GET` | `/api/posts` | `limit`, `issue`, `province`, `platform`, `sentiment`, `source` | Array of post objects (content truncated to 500 chars) |
| `GET` | `/api/export/posts` | Same as above | CSV download (no limit) |

### Polls

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/polls` | All active polls with option counts and percentages. Public (no auth). |
| `POST` | `/api/polls/respond` | Body: `{poll_id, option_id, province?, age_group?, gender?}`. 409 if already responded. |
| `GET` | `/api/polls/{poll_id}/results` | Full results including per-option count + pct. |

### Campaign Message Generation

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/generate-message` | `{province, issue}` | `text/plain` streaming response |

Requires `ANTHROPIC_API_KEY` in `.env`. Returns a streaming `StreamingResponse` — the frontend reads it as a token stream.

### Vote Protection — Voter Register

| Method | Path | Query | Notes |
|---|---|---|---|
| `GET` | `/api/voter-register/summary` | — | National totals + all provinces + tabulation coverage |
| `GET` | `/api/voter-register/districts` | `province_num` | All districts in a province |
| `GET` | `/api/voter-register/constituencies` | `district_code` | All constituencies in a district |
| `GET` | `/api/voter-register/wards` | `constituency_num` | All wards in a constituency |
| `GET` | `/api/voter-register/polling-stations` | `ward_code` | All stations + joined tabulation result |

### Vote Protection — Tabulation

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/tabulation/submit` | Body: `{polling_district_code, votes_cast, pf_votes?, upnd_votes?, other_votes?, rejected_ballots?, agent_name?, notes?}`. UPSERT — resubmitting overwrites. Returns `{discrepancy: true}` if votes > registered. |
| `GET` | `/api/tabulation/overview` | National totals, province-by-province coverage, top 50 discrepancies |
| `GET` | `/api/tabulation/discrepancies` | All stations where votes cast > registered voters |

### Health

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/health` | `{status: "ok", timestamp}` |

---

## 6. Database Schema

### `posts`
Scraped social media posts and news articles.

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | — |
| `external_id` | varchar(255) unique | Platform's own ID (prevents duplicates) |
| `platform` | enum | `facebook`, `news`, `twitter`, `manual` |
| `source_name` | varchar(255) | e.g. "Lusaka Times", "Hakainde Hichilema" |
| `source_url` | varchar(500) | — |
| `content` | text | Full post/article text |
| `author` | varchar(255) | — |
| `province` | varchar(100) | Detected by NLP |
| `likes`, `comments`, `shares` | int | Engagement metrics |
| `published_at` | datetime | Original publish time |
| `scraped_at` | datetime | When we collected it |
| `is_processed` | bool | Whether NLP has been run |

### `sentiments`
NLP result for each post (1:1 with posts).

| Column | Type | Notes |
|---|---|---|
| `post_id` | int FK unique | — |
| `label` | enum | `positive`, `negative`, `neutral` |
| `score` | float | Confidence 0.0–1.0 |
| `issues_found` | JSON array | e.g. `["mealie_meal", "fuel"]` |
| `analysed_at` | datetime | — |

### `polls` / `poll_options` / `poll_responses`
Opinion poll system. `poll_responses.ip_hash` stores a SHA-256 hash of `{ip}-{poll_id}` — prevents duplicate votes without storing raw IPs.

### `province_scores`
Daily snapshot of each province's grievance score. Computed from: `(neg_pct × 70) + volume_bonus + polarity_bonus`.

### `keywords` / `post_keywords`
Tracked keyword terms mapped to issue categories (many-to-many with posts).

### `voter_register`
ECZ official 2026 voter register. 13,518 rows (one per polling station).

| Column | Type | Notes |
|---|---|---|
| `province_num` | varchar(5) | ECZ province code |
| `province_name` | varchar(100) | — |
| `district_code` | varchar(10) | — |
| `constituency_num` | varchar(10) | — |
| `ward_code` | varchar(20) | — |
| `polling_district_code` | varchar(20) | Unique station identifier |
| `polling_district` | varchar(150) | — |
| `polling_station` | varchar(200) | — |
| `male`, `female`, `total` | int | Registered voters |

### `tabulation_results`
Party parallel vote count. One row per polling station (UNIQUE on `polling_district_code`). Submitted by PF field agents on election night.

| Column | Type | Notes |
|---|---|---|
| `polling_district_code` | varchar(20) unique | Joins to `voter_register` |
| `registered_voters` | int | Copied from register at submit time |
| `votes_cast` | int | Total ballots counted |
| `pf_votes`, `upnd_votes`, `other_votes` | int | Party breakdown |
| `rejected_ballots` | int | — |
| `agent_name` | varchar(200) | Field agent who submitted |
| `is_verified` | bool | HQ verification flag |

---

## 7. NLP Pipeline

File: `backend/nlp/sentiment.py`

**Step 1 — Base polarity:** TextBlob runs on the raw text, returning a polarity score from -1.0 (very negative) to +1.0 (very positive).

**Step 2 — Zambian context adjustments:** A dictionary of 20+ Zambian-English and Bemba/Nyanja phrases adjusts the polarity. Examples:
- `"life is hard"` → -0.6
- `"ba hichilema"` (dismissive usage) → -0.3
- `"new dawn"` (ironic) → -0.2
- `"bring back pf"` → +0.5

**Step 3 — Government criticism patterns:** Eight regex patterns catch explicit criticism phrased neutrally (e.g. "cost of living has risen") and apply an additional -0.3 adjustment.

**Step 4 — Label assignment:**
- polarity < -0.1 → `negative` (confidence = `min(1.0, |polarity| + 0.3)`)
- polarity > +0.1 → `positive`
- otherwise → `neutral`

**Step 5 — Issue extraction:** Keyword list scans for 7 issue categories. A post can carry multiple issues (stored as JSON array).

**Step 6 — Province detection:** Province keyword list (40+ place names, Zambian constituency names, local area names). Order matters — `North-Western` is checked before `Western` to avoid false matches.

**Known limitations:** Sarcasm, heavy Bemba code-switching, and highly localised references may be misclassified. Read trends, not individual posts.

---

## 8. Data Sources

### Facebook Pages (22 pages via Meta Graph API)

**Political pages — all posts captured:**
| Page | Why monitored |
|---|---|
| UPND Official | Opposition strategy and attack lines |
| Hakainde Hichilema | Presidential messaging |
| Patriotic Front | Our own page — reach and engagement |
| Brian Mundubile | PF Secretary General communications |
| Makebi Zulu | Senior PF voice |
| NRPUP | Third-party signals |
| Emmanuel Mwamba | High-volume political commentator |
| Miles Sampa | Lusaka Mayor — urban voter intelligence |
| Bowman Lusambo | Copperbelt dynamics |
| Given Lubinda | Senior PF leadership |

**Media pages — keyword filtered:**
Mwebantu · Kalemba · Zambian Watchdog · Diggers News · Daily Revelation · Zambia Reports · Lusaka Times · The Mast Online · ZNBC · Zambian Observer · Zambia Monitor · Zambia Daily Mail

### News Websites (10 sites via BeautifulSoup)
Mwebantu · Kalemba · Zambian Watchdog · Diggers News · Daily Revelation · Zambia Reports · Zambia Monitor · Zambian Observer · Lusaka Times · The Mast Online

> **Note:** Facebook scraping requires a Meta Graph API access token from a verified Meta Business Account. App Review takes 5–10 business days. News scraping works without any credentials.

### Scrape Schedule
Every 30 minutes via APScheduler in `backend/scrapers/scheduler.py`.

---

## 9. Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+ (use `/usr/share/nodejs/corepack/shims/npm` on this VM — add to PATH)
- PostgreSQL 16+ running on port 5432
- Redis 7+ running on port 6379

### 1. Backend

```bash
cd ~/pf-intelligence/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — fill in DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY at minimum
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/pf_intel \
  python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The database tables and voter register seed are created automatically on first startup by `init_db()`.

### 2. Frontend

```bash
PATH="$PATH:/usr/share/nodejs/corepack/shims" \
  npm --prefix ~/pf-intelligence/frontend start
```

Or for development with hot reload:
```bash
PATH="$PATH:/usr/share/nodejs/corepack/shims" \
  npm --prefix ~/pf-intelligence/frontend run dev
```

### 3. Health check

```bash
curl http://localhost:8000/api/health
# {"status":"ok","timestamp":"..."}
```

### Admin login (local)
- Email: `admin@pf-intelligence.zm`
- Password: `changeme_on_first_run`

---

## 10. Production Deployment

### Server requirements
- Ubuntu 24.04 LTS
- 4 vCPU, 8 GB RAM minimum (DigitalOcean "Basic Dedicated" or equivalent)
- 80 GB SSD
- Public IPv4 address

### Step 1 — Point the domain

In your domain registrar (Namecheap/GoDaddy), create an **A record**:
```
Type: A
Name: @  (root domain)
Value: <your-droplet-IP>
TTL: 300
```
Also add:
```
Type: A
Name: www
Value: <your-droplet-IP>
```

### Step 2 — Get SSL certificate (before starting Docker)

```bash
apt-get update && apt-get install -y certbot
certbot certonly --standalone \
  -d politicalintelligence.com \
  -d www.politicalintelligence.com \
  --non-interactive --agree-tos -m emulenga89@gmail.com
```

This writes certs to `/etc/letsencrypt/live/politicalintelligence.com/` — the path nginx.conf already expects.

### Step 3 — Deploy

```bash
apt-get install -y docker.io docker-compose-plugin
git clone https://github.com/Knox8907/pf-intelligence.git /opt/pf-intelligence
cd /opt/pf-intelligence
cp backend/.env.example backend/.env
nano backend/.env    # fill in all required values (see Section 11)
docker compose -f docker-compose.prod.yml up -d --build
```

Or run the automated deploy script:
```bash
bash deploy.sh
```

### Step 4 — Verify

```bash
curl https://politicalintelligence.com/api/health
# {"status":"ok","timestamp":"..."}
```

### Useful commands

```bash
# View live logs
docker compose -f docker-compose.prod.yml logs -f

# Restart all services
docker compose -f docker-compose.prod.yml restart

# Stop everything
docker compose -f docker-compose.prod.yml down

# Pull latest code and redeploy
git -C /opt/pf-intelligence pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
```

### SSL auto-renewal

Certbot installs a cron job automatically. To test renewal manually:
```bash
certbot renew --dry-run
```

---

## 11. Environment Variables

All variables live in `backend/.env`. The file is never committed to git (listed in `.gitignore`). Use `backend/.env.example` as the template.

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:<POSTGRES_PASSWORD>@db:5432/pf_intel` |
| `REDIS_URL` | Yes | `redis://redis:6379` |
| `POSTGRES_PASSWORD` | Yes | Strong random password — matches the password in DATABASE_URL |
| `SECRET_KEY` | Yes | Minimum 32 random characters — signs JWT tokens |
| `ADMIN_EMAIL` | Yes | Login email for the admin account |
| `ADMIN_PASSWORD` | Yes | Login password — change from default on first run |
| `ANTHROPIC_API_KEY` | Yes | From [console.anthropic.com](https://console.anthropic.com) — required for campaign message generation |
| `ALLOWED_ORIGINS` | Yes | `https://politicalintelligence.com,https://www.politicalintelligence.com` |
| `META_ACCESS_TOKEN` | No | Meta Graph API token — required for live Facebook scraping |
| `META_APP_ID` | No | From Meta Developer console |
| `META_APP_SECRET` | No | From Meta Developer console |
| `SCRAPE_INTERVAL_MINUTES` | No | Default: `30` |

---

## 12. Vote Protection System

### Background

The ECZ (Electoral Commission of Zambia) publishes official results over several days after polling closes. PF's parallel tabulation system gives party leadership an independent, real-time count as field agents submit results from each polling station — enabling rapid legal intervention if discrepancies appear and an independent projection before the official announcement.

### Voter Register

Source: ECZ official PDF register dated 8 May 2026 (387 pages).  
Parser: `backend/parse_voter_register.py` — two-pass (regex, then word-position fallback for edge cases).  
Seed file: `backend/database/migrations/voter_register_seed.sql.gz` (382 KB gzipped) — auto-loads on first `init_db()` call.

**Coverage:**
- **13,518 of 13,529** polling stations (99.9%)
- **8,777,312 of 8,786,300** registered voters

### Frontend

The Vote Protection tab has two views:

**Voter Register view**  
Province → District → Constituency → Ward → Polling Station cascade with breadcrumb navigation. National KPI bar shows total stations (12,933 displayed), total voters (8.77M), female/male split, and parallel tabulation coverage %.

**Tabulation view**  
Province-by-province coverage table. Below it: a red-flagged discrepancy table listing every station where submitted votes exceed registered voters, sorted by excess count. Clicking any station opens a modal with: PF / UPND / other breakdown, rejected ballots, agent name, timestamp, and notes.

### Fraud detection logic

When a result is submitted via `POST /api/tabulation/submit`:
1. The station's registered voter count is looked up from `voter_register`
2. If `votes_cast > registered_voters`, the response includes `"discrepancy": true` and a warning message
3. The station appears in the discrepancy table visible to HQ in real time

---

## 13. Security Model

| Control | Implementation |
|---|---|
| Authentication | JWT (HS256), 24-hour expiry. All protected endpoints use `Depends(require_auth)`. |
| Password hashing | bcrypt via `passlib` |
| CORS | Restricted to `ALLOWED_ORIGINS` in `.env` |
| HTTPS | nginx TLS termination with Let's Encrypt cert; HTTP permanently redirects to HTTPS |
| Database | Not exposed outside Docker network — only the API container has access |
| Poll deduplication | IP hashed with poll ID (SHA-256); raw IPs never stored |
| Voter data | No personal identifying information stored — only aggregate counts per station |
| Secrets | `.env` in `.gitignore`; never committed to the repository |
| Source code | Private GitHub repository (https://github.com/Knox8907/pf-intelligence) |

---

## 14. Pending Work

| Item | Priority | Notes |
|---|---|---|
| Register `politicalintelligence.com` | **Critical** | Namecheap/GoDaddy — $15/yr. Point A record to droplet IP before running certbot. |
| Provision DigitalOcean droplet | **Critical** | Ubuntu 24.04, 4 vCPU / 8 GB RAM. Run `deploy.sh` after SSL cert is issued. |
| Apply for Meta Business Account & App Review | **Urgent** | Takes 5–10 business days. Without this, Facebook scraping is disabled; only news sites run. |
| Procure Anthropic API key | High | From [console.anthropic.com](https://console.anthropic.com). Required for campaign message generation. |
| Per-agent accounts for election day | High | Currently one shared admin login. Before 13 August, add per-agent accounts so tabulation submissions are individually attributable. Agent management UI needed. |
| Grant credentials to campaign leadership | Medium | After server is live. |
| Laptop procurement | Medium | See budget doc. 2× Dell XPS 15 or ThinkPad X1 Carbon Gen 12 recommended. |

---

*Prepared by PF Intelligence Hub technical team*  
*Confidential — Internal use only — Do not distribute outside authorised personnel*
