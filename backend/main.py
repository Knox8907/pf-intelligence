"""
PF Intelligence Hub — FastAPI backend.
Provides REST API for the Next.js frontend dashboard.
"""
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from datetime import datetime, timedelta
from collections import defaultdict
from pydantic import BaseModel
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import json
import csv
import io
import anthropic

from config import settings
from database.connection import get_db, init_db
from database.models import (
    Post, Sentiment, Poll, PollOption, PollResponse,
    ProvinceScore, SentimentLabel, VoterStation, TabulationResult
)

app = FastAPI(title="PF Intelligence Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


# ── Auth ─────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


def _create_token(email: str) -> str:
    return jwt.encode(
        {"sub": email, "exp": datetime.utcnow() + timedelta(hours=24)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub", "")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Pydantic schemas ────────────────────────────────────────

class PollResponseCreate(BaseModel):
    poll_id: int
    option_id: int
    province: Optional[str] = None
    age_group: Optional[str] = None
    gender: Optional[str] = None


class MessageGenerateRequest(BaseModel):
    province: str
    issue: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Auth endpoint ────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    if payload.email != settings.ADMIN_EMAIL or payload.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": _create_token(payload.email), "token_type": "bearer"}


# ── Dashboard endpoints ──────────────────────────────────────

@app.get("/api/dashboard/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    """Overall KPI summary for the dashboard hero row."""
    since = datetime.utcnow() - timedelta(days=7)

    # Total posts this week
    total = await db.execute(
        select(func.count(Post.id)).where(Post.scraped_at >= since)
    )
    total_count = total.scalar() or 0

    # Sentiment breakdown
    sent_result = await db.execute(
        select(Sentiment.label, func.count(Sentiment.id))
        .join(Post, Sentiment.post_id == Post.id)
        .where(Post.scraped_at >= since)
        .group_by(Sentiment.label)
    )
    sent_counts = {row[0]: row[1] for row in sent_result}
    neg = sent_counts.get("negative", 0)
    pos = sent_counts.get("positive", 0)
    neu = sent_counts.get("neutral", 0)
    total_sent = neg + pos + neu or 1

    # Issue frequency
    issue_result = await db.execute(
        select(Sentiment.issues_found)
        .join(Post, Sentiment.post_id == Post.id)
        .where(Post.scraped_at >= since)
    )
    issue_counts = defaultdict(int)
    for (issues,) in issue_result:
        for issue in (issues or []):
            issue_counts[issue] += 1

    top_issue = max(issue_counts, key=issue_counts.get) if issue_counts else "mealie_meal"

    # Poll responses
    poll_count = await db.execute(select(func.count(PollResponse.id)))

    return {
        "total_mentions":   total_count,
        "negative_pct":     round(neg / total_sent * 100, 1),
        "positive_pct":     round(pos / total_sent * 100, 1),
        "neutral_pct":      round(neu / total_sent * 100, 1),
        "top_issue":        top_issue,
        "poll_responses":   poll_count.scalar() or 0,
        "week_start":       since.isoformat(),
    }


@app.get("/api/dashboard/issues")
async def issue_frequency(db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    """Issue frequency breakdown for the bar chart."""
    since = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(Sentiment.issues_found)
        .join(Post, Sentiment.post_id == Post.id)
        .where(Post.scraped_at >= since)
    )

    issue_counts = defaultdict(int)
    total = 0
    for (issues,) in result:
        total += 1
        for issue in (issues or []):
            issue_counts[issue] += 1

    if total == 0:
        # Return demo data if no real data yet
        return [
            {"issue": "mealie_meal",  "display": "Mealie meal price",    "count": 0, "pct": 84},
            {"issue": "fuel",         "display": "Fuel costs",           "count": 0, "pct": 71},
            {"issue": "electricity",  "display": "Electricity/ZESCO",    "count": 0, "pct": 68},
            {"issue": "employment",   "display": "Youth unemployment",   "count": 0, "pct": 63},
            {"issue": "kwacha",       "display": "Kwacha depreciation",  "count": 0, "pct": 58},
        ]

    display_map = {
        "mealie_meal": "Mealie meal price",
        "fuel":        "Fuel costs",
        "electricity": "Electricity/ZESCO",
        "employment":  "Youth unemployment",
        "kwacha":      "Kwacha depreciation",
        "fertiliser":  "Fertiliser/farming",
        "education":   "School/medical fees",
    }

    return sorted([
        {
            "issue":   issue,
            "display": display_map.get(issue, issue),
            "count":   count,
            "pct":     round(count / total * 100, 1),
        }
        for issue, count in issue_counts.items()
    ], key=lambda x: x["count"], reverse=True)


@app.get("/api/dashboard/provinces")
async def province_scores(db: AsyncSession = Depends(get_db), _: str = Depends(require_auth)):
    """Latest grievance score per province."""
    result = await db.execute(
        select(ProvinceScore)
        .order_by(desc(ProvinceScore.recorded_at))
        .limit(100)
    )
    rows = result.scalars().all()

    # Keep only latest per province
    seen = {}
    for row in rows:
        if row.province not in seen:
            seen[row.province] = {
                "province":   row.province,
                "score":      row.score,
                "post_count": row.post_count,
                "neg_pct":    row.neg_pct,
                "top_issue":  row.top_issue,
            }

    # Fallback to demo data if empty
    if not seen:
        demo = [
            ("Lusaka",       88, "mealie_meal"),
            ("Copperbelt",   82, "electricity"),
            ("Eastern",      79, "mealie_meal"),
            ("Southern",     74, "fuel"),
            ("Central",      71, "mealie_meal"),
            ("Western",      69, "employment"),
            ("Northern",     62, "fuel"),
            ("North-Western",58, "electricity"),
            ("Luapula",      55, "mealie_meal"),
            ("Muchinga",     51, "employment"),
        ]
        return [{"province": p, "score": s, "top_issue": i,
                 "post_count": 0, "neg_pct": 0} for p, s, i in demo]

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


# ── Social feed endpoints ────────────────────────────────────

@app.get("/api/posts")
async def get_posts(
    limit: int = 20,
    issue: Optional[str] = None,
    province: Optional[str] = None,
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Paginated post feed with optional filters."""
    query = (
        select(Post, Sentiment)
        .join(Sentiment, Sentiment.post_id == Post.id, isouter=True)
        .order_by(desc(Post.scraped_at))
        .limit(min(limit, 100))
    )

    if province:
        query = query.where(Post.province == province)
    if platform:
        query = query.where(Post.platform == platform)
    if sentiment:
        query = query.where(Sentiment.label == sentiment)
    if source:
        query = query.where(Post.source_name == source)
    if issue:
        # JSON array contains — works on PostgreSQL
        query = query.where(
            Sentiment.issues_found.cast(str).contains(issue)
        )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id":           post.id,
            "source_name":  post.source_name,
            "platform":     post.platform,
            "content":      post.content[:500],
            "province":     post.province,
            "likes":        post.likes,
            "comments":     post.comments,
            "published_at": post.published_at.isoformat() if post.published_at else None,
            "sentiment":    sent.label if sent else None,
            "issues":       sent.issues_found if sent else [],
        }
        for post, sent in rows
    ]


# ── Poll endpoints ───────────────────────────────────────────

@app.get("/api/polls")
async def get_polls(db: AsyncSession = Depends(get_db)):
    """Return all active polls with current result counts."""
    result = await db.execute(
        select(Poll).where(Poll.is_active == True)
    )
    polls = result.scalars().all()

    output = []
    for poll in polls:
        opts_result = await db.execute(
            select(PollOption).where(PollOption.poll_id == poll.id)
            .order_by(PollOption.order)
        )
        options = opts_result.scalars().all()

        opt_data = []
        for opt in options:
            count_result = await db.execute(
                select(func.count(PollResponse.id))
                .where(PollResponse.option_id == opt.id)
            )
            count = count_result.scalar() or 0
            opt_data.append({
                "id": opt.id, "text": opt.text, "order": opt.order, "count": count
            })

        total = sum(o["count"] for o in opt_data) or 1
        for o in opt_data:
            o["pct"] = round(o["count"] / total * 100, 1)

        output.append({
            "id": poll.id,
            "question": poll.question,
            "options": opt_data,
            "total_responses": total - 1 if total == 1 else total,
        })

    return output


@app.post("/api/polls/respond")
async def submit_poll_response(
    payload: PollResponseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit a single poll response. One response per IP per poll."""
    # Hash IP to prevent duplicates without storing raw IPs
    ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(
        f"{ip}-{payload.poll_id}".encode()
    ).hexdigest()[:32]

    # Check for existing response from this IP
    existing = await db.execute(
        select(PollResponse).where(
            PollResponse.poll_id == payload.poll_id,
            PollResponse.ip_hash == ip_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already responded to this poll")

    response = PollResponse(
        poll_id    = payload.poll_id,
        option_id  = payload.option_id,
        province   = payload.province,
        age_group  = payload.age_group,
        gender     = payload.gender,
        ip_hash    = ip_hash,
    )
    db.add(response)
    await db.commit()

    return {"status": "ok", "message": "Response recorded"}


@app.get("/api/polls/{poll_id}/results")
async def poll_results(poll_id: int, db: AsyncSession = Depends(get_db)):
    """Full results for a specific poll including province breakdown."""
    result = await db.execute(
        select(PollOption, func.count(PollResponse.id).label("count"))
        .outerjoin(PollResponse, PollResponse.option_id == PollOption.id)
        .where(PollOption.poll_id == poll_id)
        .group_by(PollOption.id)
        .order_by(PollOption.order)
    )
    rows = result.all()

    total = sum(r.count for r in rows) or 1
    return {
        "poll_id": poll_id,
        "options": [
            {"text": r.PollOption.text, "count": r.count,
             "pct": round(r.count / total * 100, 1)}
            for r in rows
        ],
        "total": total,
    }


# ── Data export ──────────────────────────────────────────────

@app.get("/api/export/posts")
async def export_posts(
    issue: Optional[str] = None,
    province: Optional[str] = None,
    platform: Optional[str] = None,
    sentiment: Optional[str] = None,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    """Export all matching posts with sentiment as a CSV download."""
    query = (
        select(Post, Sentiment)
        .join(Sentiment, Sentiment.post_id == Post.id, isouter=True)
        .order_by(desc(Post.scraped_at))
    )
    if province:
        query = query.where(Post.province == province)
    if platform:
        query = query.where(Post.platform == platform)
    if sentiment:
        query = query.where(Sentiment.label == sentiment)
    if source:
        query = query.where(Post.source_name == source)
    if issue:
        query = query.where(Sentiment.issues_found.cast(str).contains(issue))

    result = await db.execute(query)
    rows = result.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "platform", "source_name", "province", "sentiment", "score",
        "issues", "likes", "comments", "published_at", "scraped_at", "content",
    ])
    for post, sent in rows:
        writer.writerow([
            post.id,
            post.platform,
            post.source_name,
            post.province or "",
            sent.label if sent else "",
            sent.score if sent else "",
            "|".join(sent.issues_found or []) if sent else "",
            post.likes,
            post.comments,
            post.published_at.isoformat() if post.published_at else "",
            post.scraped_at.isoformat() if post.scraped_at else "",
            post.content,
        ])

    filename = f"pf_intel_posts_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Campaign message generation ──────────────────────────────

_CAMPAIGN_SYSTEM = """\
You are a senior political campaign strategist for the Patriotic Front (PF), \
Zambia's main opposition party ahead of the 13 August 2026 general election. \
Your expertise is writing targeted, emotionally resonant campaign messages in \
simple Zambian English that connect with working-class Zambians.

Key context:
- The UPND government led by President Hakainde Hichilema has been in power since August 2021.
- The cost of living has risen sharply: a 25 kg bag of mealie meal rose from ~ZMW 150 to ~ZMW 340+.
- ZESCO load-shedding is severe — 10–16 hours daily in many areas, destroying small businesses.
- Youth unemployment is intense among the 18–35 age group, which makes up 60%+ of the electorate.
- The kwacha has depreciated significantly against the US dollar since 2021.
- PF's message is: "We understand your struggles — here's exactly how PF will fix them."

Write a punchy, emotionally resonant campaign message (150–200 words) targeted at voters \
in the specified province, focused on the specified issue. Use specific numbers where relevant. \
End with a clear, concrete PF pledge. Write in a direct, accessible voice — no jargon.\
"""


@app.post("/api/generate-message")
async def generate_message(payload: MessageGenerateRequest, _: str = Depends(require_auth)):
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY.startswith("sk-ant-YOUR"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured — add your key to backend/.env")

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def stream_text():
        try:
            async with client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=_CAMPAIGN_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Write a PF 2026 campaign message for voters in {payload.province} "
                        f"province, focused on the issue of {payload.issue}."
                    ),
                }],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.AuthenticationError:
            yield "\n[Error: Invalid Anthropic API key. Update ANTHROPIC_API_KEY in backend/.env]"
        except anthropic.RateLimitError:
            yield "\n[Error: Anthropic rate limit reached. Try again in a moment.]"
        except Exception as e:
            yield f"\n[Error: {str(e)}]"

    return StreamingResponse(stream_text(), media_type="text/plain")


# ── Vote Protection: Voter Register ──────────────────────────

@app.get("/api/voter-register/summary")
async def vr_summary(db: AsyncSession = Depends(get_db)):
    """National totals and per-province breakdown."""
    r = await db.execute(text("""
        SELECT province_num, province_name,
               COUNT(*)    AS stations,
               SUM(male)   AS male,
               SUM(female) AS female,
               SUM(total)  AS total
        FROM voter_register
        GROUP BY province_num, province_name
        ORDER BY province_num
    """))
    provinces = [dict(r) for r in r.mappings()]

    national = {
        "stations":  sum(p["stations"] for p in provinces),
        "male":      sum(p["male"]     for p in provinces),
        "female":    sum(p["female"]   for p in provinces),
        "total":     sum(p["total"]    for p in provinces),
    }

    tab_r = await db.execute(text("""
        SELECT COUNT(*) AS submitted,
               SUM(CASE WHEN votes_cast > registered_voters THEN 1 ELSE 0 END) AS discrepancies
        FROM tabulation_results
    """))
    tab = tab_r.mappings().one()

    return {
        "national":    national,
        "provinces":   provinces,
        "tabulation": {
            "submitted":     int(tab["submitted"] or 0),
            "total_stations": national["stations"],
            "discrepancies": int(tab["discrepancies"] or 0),
        },
    }


@app.get("/api/voter-register/districts")
async def vr_districts(province_num: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("""
        SELECT district_code, district_name,
               COUNT(*)    AS stations,
               SUM(male)   AS male,
               SUM(female) AS female,
               SUM(total)  AS total
        FROM voter_register
        WHERE province_num = :p
        GROUP BY district_code, district_name
        ORDER BY district_code
    """), {"p": province_num})
    return [dict(r) for r in r.mappings()]


@app.get("/api/voter-register/constituencies")
async def vr_constituencies(district_code: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("""
        SELECT constituency_num, constituency_name,
               COUNT(*)    AS stations,
               SUM(male)   AS male,
               SUM(female) AS female,
               SUM(total)  AS total
        FROM voter_register
        WHERE district_code = :d
        GROUP BY constituency_num, constituency_name
        ORDER BY constituency_name
    """), {"d": district_code})
    return [dict(r) for r in r.mappings()]


@app.get("/api/voter-register/wards")
async def vr_wards(constituency_num: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("""
        SELECT ward_code, ward_name,
               COUNT(*)    AS stations,
               SUM(male)   AS male,
               SUM(female) AS female,
               SUM(total)  AS total
        FROM voter_register
        WHERE constituency_num = :c
        GROUP BY ward_code, ward_name
        ORDER BY ward_name
    """), {"c": constituency_num})
    return [dict(r) for r in r.mappings()]


@app.get("/api/voter-register/polling-stations")
async def vr_polling_stations(ward_code: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("""
        SELECT vr.polling_district_code, vr.polling_district, vr.polling_station,
               vr.male, vr.female, vr.total,
               tr.votes_cast, tr.pf_votes, tr.upnd_votes, tr.other_votes,
               tr.rejected_ballots, tr.agent_name, tr.submitted_at, tr.is_verified,
               CASE WHEN tr.votes_cast IS NOT NULL AND tr.votes_cast > vr.total
                    THEN true ELSE false END AS has_discrepancy
        FROM voter_register vr
        LEFT JOIN tabulation_results tr
               ON tr.polling_district_code = vr.polling_district_code
        WHERE vr.ward_code = :w
        ORDER BY vr.polling_district
    """), {"w": ward_code})
    return [dict(r) for r in r.mappings()]


# ── Vote Protection: Parallel Tabulation ─────────────────────

class TabulationSubmit(BaseModel):
    polling_district_code: str
    votes_cast:            int
    pf_votes:              Optional[int] = None
    upnd_votes:            Optional[int] = None
    other_votes:           Optional[int] = None
    rejected_ballots:      Optional[int] = None
    agent_name:            Optional[str] = None
    notes:                 Optional[str] = None


@app.post("/api/tabulation/submit")
async def tabulation_submit(
    payload: TabulationSubmit,
    _: str = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    # Look up station in register
    station_r = await db.execute(text("""
        SELECT polling_station, ward_code, constituency_name,
               district_name, province_name, total
        FROM voter_register
        WHERE polling_district_code = :code
        LIMIT 1
    """), {"code": payload.polling_district_code})
    station = station_r.mappings().one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Polling station not found in voter register")

    discrepancy = payload.votes_cast > station["total"]

    await db.execute(text("""
        INSERT INTO tabulation_results
            (polling_district_code, polling_station, ward_code, constituency_name,
             district_name, province_name, registered_voters,
             votes_cast, pf_votes, upnd_votes, other_votes, rejected_ballots,
             agent_name, notes, submitted_at)
        VALUES
            (:code, :station, :ward, :constituency, :district, :province, :registered,
             :votes_cast, :pf, :upnd, :other, :rejected,
             :agent, :notes, NOW())
        ON CONFLICT (polling_district_code) DO UPDATE SET
            votes_cast       = EXCLUDED.votes_cast,
            pf_votes         = EXCLUDED.pf_votes,
            upnd_votes       = EXCLUDED.upnd_votes,
            other_votes      = EXCLUDED.other_votes,
            rejected_ballots = EXCLUDED.rejected_ballots,
            agent_name       = EXCLUDED.agent_name,
            notes            = EXCLUDED.notes,
            submitted_at     = NOW(),
            is_verified      = FALSE
    """), {
        "code":         payload.polling_district_code,
        "station":      station["polling_station"],
        "ward":         station["ward_code"],
        "constituency": station["constituency_name"],
        "district":     station["district_name"],
        "province":     station["province_name"],
        "registered":   station["total"],
        "votes_cast":   payload.votes_cast,
        "pf":           payload.pf_votes,
        "upnd":         payload.upnd_votes,
        "other":        payload.other_votes,
        "rejected":     payload.rejected_ballots,
        "agent":        payload.agent_name,
        "notes":        payload.notes,
    })
    await db.commit()

    return {
        "status":       "ok",
        "discrepancy":  discrepancy,
        "registered":   station["total"],
        "votes_cast":   payload.votes_cast,
        "message":      "DISCREPANCY FLAGGED — votes exceed registered voters" if discrepancy else "Result recorded",
    }


@app.get("/api/tabulation/overview")
async def tabulation_overview(db: AsyncSession = Depends(get_db)):
    """High-level parallel tabulation coverage and discrepancy report."""
    r = await db.execute(text("""
        SELECT
            COUNT(*)                                                      AS total_submitted,
            SUM(registered_voters)                                        AS registered_in_submitted,
            SUM(votes_cast)                                               AS total_votes_cast,
            SUM(pf_votes)                                                 AS total_pf,
            SUM(upnd_votes)                                               AS total_upnd,
            SUM(other_votes)                                              AS total_other,
            SUM(rejected_ballots)                                         AS total_rejected,
            SUM(CASE WHEN votes_cast > registered_voters THEN 1 ELSE 0 END) AS discrepancy_count
        FROM tabulation_results
    """))
    overview = dict(r.mappings().one())

    discrepancies_r = await db.execute(text("""
        SELECT tr.polling_district_code, tr.polling_station,
               tr.constituency_name, tr.district_name, tr.province_name,
               tr.registered_voters, tr.votes_cast,
               tr.votes_cast - tr.registered_voters AS excess,
               tr.agent_name, tr.submitted_at
        FROM tabulation_results tr
        WHERE tr.votes_cast > tr.registered_voters
        ORDER BY (tr.votes_cast - tr.registered_voters) DESC
        LIMIT 50
    """))
    discrepancies = [dict(r) for r in discrepancies_r.mappings()]

    province_r = await db.execute(text("""
        SELECT tr.province_name,
               COUNT(*)    AS submitted,
               SUM(CASE WHEN tr.votes_cast > tr.registered_voters THEN 1 ELSE 0 END) AS flags
        FROM tabulation_results tr
        GROUP BY tr.province_name
        ORDER BY tr.province_name
    """))
    by_province = [dict(r) for r in province_r.mappings()]

    total_stations_r = await db.execute(text("SELECT COUNT(*) FROM voter_register"))
    total_stations = total_stations_r.scalar()

    return {
        "total_stations":   total_stations,
        "overview":         overview,
        "by_province":      by_province,
        "discrepancies":    discrepancies,
    }


@app.get("/api/tabulation/discrepancies")
async def tabulation_discrepancies(db: AsyncSession = Depends(get_db)):
    r = await db.execute(text("""
        SELECT tr.polling_district_code, tr.polling_station,
               tr.ward_code, tr.constituency_name, tr.district_name, tr.province_name,
               tr.registered_voters, tr.votes_cast,
               tr.pf_votes, tr.upnd_votes, tr.other_votes, tr.rejected_ballots,
               tr.votes_cast - tr.registered_voters AS excess,
               tr.agent_name, tr.notes, tr.submitted_at
        FROM tabulation_results tr
        WHERE tr.votes_cast > tr.registered_voters
        ORDER BY (tr.votes_cast - tr.registered_voters) DESC
    """))
    return [dict(r) for r in r.mappings()]


# ── Health check ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
