# PF Intelligence Hub — Production Budget
## Patriotic Front Zambia · 2026 General Election Campaign
**Prepared:** 31 May 2026  
**Campaign Period:** June 2026 – 13 August 2026 (election day) + 3 months post-election  
**Exchange Rate Used:** ZMW 28.00 = USD 1.00

---

## Executive Summary

| Category | USD | ZMW |
|---|---|---|
| Hardware (one-time) | $6,720 | ZMW 188,160 |
| Software & Licences (one-time / annual) | $219 | ZMW 6,132 |
| Cloud & API Infrastructure (12 months) | $3,235 | ZMW 90,580 |
| Contingency (10%) | $1,017 | ZMW 28,476 |
| **GRAND TOTAL** | **$11,191** | **ZMW 313,348** |

---

## 1. Hardware — One-Time Purchase

### Laptops (Qty: 2)
High-specification laptops for the intelligence analysts and campaign strategists running the platform.

| Item | Spec | Unit Price (USD) | Qty | Total (USD) | Total (ZMW) |
|---|---|---|---|---|---|
| Dell XPS 15 9530 or ThinkPad X1 Carbon Gen 12 | Intel Core i7-13700H, 32 GB RAM, 1 TB NVMe SSD, 15" FHD+, backlit keyboard | $2,800 | 2 | $5,600 | ZMW 156,800 |
| Extended Warranty (3-year) | Accidental damage + hardware support | $250 | 2 | $500 | ZMW 14,000 |

**Rationale:** 32 GB RAM is required to run Docker containers (PostgreSQL, Redis, FastAPI, Next.js) locally for development and testing. NVMe SSD ensures fast database operations during demos and offline use.

### Peripherals & Power

| Item | Spec | Unit Price (USD) | Qty | Total (USD) | Total (ZMW) |
|---|---|---|---|---|---|
| UPS (APC Back-UPS 650VA) | Protects against ZESCO load-shedding outages; 20–30 min battery backup | $90 | 2 | $180 | ZMW 5,040 |
| External SSD (Samsung T7, 1 TB) | Encrypted offline data backups | $80 | 2 | $160 | ZMW 4,480 |
| Wireless Mouse & Keyboard Set | Logitech MK470 Slim | $50 | 2 | $100 | ZMW 2,800 |
| USB-C Hub (7-in-1) | Ports for monitor, ethernet, USB storage | $40 | 2 | $80 | ZMW 2,240 |
| Cat6 Ethernet Cable + Router | Stable wired connection for scraper uptime | $60 | 1 | $60 | ZMW 1,680 |
| Surge-Protected Power Strip | 4-outlet, with USB ports | $20 | 2 | $40 | ZMW 1,120 |

**Hardware Subtotal: $6,720 · ZMW 188,160**

---

## 2. Software & Licences — One-Time / Annual

| Item | Description | Cost (USD/yr) | Cost (ZMW/yr) |
|---|---|---|---|
| Domain Name (1 year) | `politicalintelligence.com` via Namecheap/GoDaddy | $15 | ZMW 420 |
| SSL Certificate | Let's Encrypt (auto-renewing) — **FREE** | $0 | ZMW 0 |
| Microsoft 365 Business Basic (2 users) | Email, Teams, OneDrive for team collaboration | $72 | ZMW 2,016 |
| GitHub Team (2 users) | Private repository, code review, CI/CD actions | $48 | ZMW 1,344 |
| NordLayer VPN (2 users) | Secure remote access to production server | $84 | ZMW 2,352 |
| Meta Developer Account | Required for Facebook Graph API — **FREE** | $0 | ZMW 0 |
| PostgreSQL, Redis, Python, Next.js | Open-source — **FREE** | $0 | ZMW 0 |

**Software Subtotal: $219/yr · ZMW 6,132/yr**

---

## 3. Cloud & API Infrastructure — Monthly Recurring

All production infrastructure runs on DigitalOcean. The Facebook scraper and news scraper run continuously; the Claude API is called on-demand for campaign message generation.

### DigitalOcean Hosting

| Service | Spec | Monthly (USD) | Monthly (ZMW) |
|---|---|---|---|
| App Droplet (Dedicated CPU) | 4 vCPU, 8 GB RAM — runs FastAPI + Next.js + scrapers | $48 | ZMW 1,344 |
| Managed PostgreSQL (Basic) | 1 GB RAM, daily automated backups | $15 | ZMW 420 |
| Managed Redis (Basic) | 1 GB RAM, for scraper job queue | $15 | ZMW 420 |
| Load Balancer | HTTPS termination, uptime routing | $12 | ZMW 336 |
| Spaces (Object Storage + CDN) | Exported CSV storage, static assets | $5 | ZMW 140 |
| Automated Backups | 20% of Droplet cost | $9.60 | ZMW 269 |
| **DigitalOcean Subtotal** | | **$104.60/mo** | **ZMW 2,929/mo** |

### API Costs

| Service | Usage Estimate | Rate | Monthly (USD) | Monthly (ZMW) |
|---|---|---|---|---|
| Anthropic API — Claude Opus 4.7 | 30 campaign message generations/day × 2,000 output tokens = ~1.8M tokens/month | $75/M output tokens + $15/M input | $150 | ZMW 4,200 |
| Meta Graph API (Facebook) | 22 pages × 24 fetches/day — within free tier | Free up to 200 calls/hr/token | $0 | ZMW 0 |
| Mailgun (email alerts) | Scraper error alerts, daily digests | Flex plan | $15 | ZMW 420 |
| **API Subtotal** | | | **$165/mo** | **ZMW 4,620/mo** |

### Monthly Infrastructure Total

| | Monthly (USD) | Monthly (ZMW) |
|---|---|---|
| DigitalOcean | $104.60 | ZMW 2,929 |
| APIs | $165.00 | ZMW 4,620 |
| **Monthly Total** | **$269.60** | **ZMW 7,549** |

### 12-Month Infrastructure Total: **$3,235 · ZMW 90,580**

---

## 4. Full Budget Summary

### One-Time Costs

| Item | USD | ZMW |
|---|---|---|
| Hardware (laptops, peripherals, UPS) | $6,720 | ZMW 188,160 |
| Software licences (annual) | $219 | ZMW 6,132 |
| **One-Time Subtotal** | **$6,939** | **ZMW 194,292** |

### Recurring Costs (12 months)

| Item | USD | ZMW |
|---|---|---|
| Cloud infrastructure (12 × $269.60) | $3,235 | ZMW 90,580 |
| **Recurring Subtotal** | **$3,235** | **ZMW 90,580** |

### Totals Before Contingency

| | USD | ZMW |
|---|---|---|
| One-time | $6,939 | ZMW 194,292 |
| 12-month recurring | $3,235 | ZMW 90,580 |
| **Subtotal** | **$10,174** | **ZMW 284,872** |
| Contingency 10% | $1,017 | ZMW 28,487 |
| **GRAND TOTAL** | **$11,191** | **ZMW 313,359** |

---

## 5. Payment Schedule Recommendation

| Phase | Timing | Items | Amount (ZMW) |
|---|---|---|---|
| Phase 1 — Immediate | June 2026 | Laptops + peripherals + domain + licences | ZMW 194,292 |
| Phase 2 — Monthly | Jun–Aug 2026 (3 months) | Cloud + API infrastructure | ZMW 22,647 |
| Phase 3 — Post-election | Sep–Oct 2026 (2 months) | Wind-down + final infrastructure | ZMW 15,098 |
| Contingency Reserve | Held in reserve | Buffer for price changes, exchange rate movements | ZMW 28,487 |
| **Total** | | | **ZMW 260,524** |

> Note: Post-election (Sep–Nov 2026) infrastructure can be scaled down to the cheapest DigitalOcean tier (~$24/mo) or shut down entirely, saving ~ZMW 98,000 vs running at full scale for 12 months.

---

## 6. Notes & Assumptions

1. **Exchange rate risk:** The ZMW/USD rate is volatile. The 10% contingency partially covers this. Consider purchasing USD upfront for annual DigitalOcean and Anthropic billing.

2. **Facebook Graph API:** The Meta access token requires a verified Meta Business Account and submission of the app for App Review (free but takes 5–10 business days). Start this process immediately.

3. **Anthropic API cost scaling:** The $150/month API estimate assumes moderate use (~30 message generations/day). If strategists use it heavily (100+/day during the final campaign sprint), budget an additional ZMW 8,400/month.

4. **Laptop procurement in Zambia:** Prices above are USD import prices. Expect a 20–30% premium if purchasing locally from Zambian retailers. Consider importing directly from RSA (Incredible Connection, Takealot) or Dubai duty-free if possible.

5. **UPS is essential:** Given ZESCO load-shedding schedules of 8–16 hours/day in Lusaka and Copperbelt, UPS units are mandatory for uninterrupted operation during campaign strategy sessions.

6. **Open-source stack:** PostgreSQL, Redis, Python/FastAPI, and Next.js are all free and open-source — no licence fees.

---

*Prepared by PF Intelligence Hub technical team · Confidential — Internal use only*
