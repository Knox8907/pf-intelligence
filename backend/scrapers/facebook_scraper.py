"""
Facebook Graph API scraper.

Monitors public Zambian political and media Facebook pages.

Page types:
  "political" — party pages, leaders, politicians: ALL posts captured (no keyword filter)
  "news"      — media pages: keyword-filtered for relevance

Requirements:
- A Meta developer app with pages_read_engagement permission
- Page access tokens for the pages you manage, OR
- Meta research API access for public page data

Note: page "id" values are Facebook usernames or numeric page IDs.
Verify/update IDs at https://www.facebook.com/<username>/about if a
page returns a 404 from the Graph API.
"""
import httpx
import logging
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger(__name__)

# ── Monitored pages ──────────────────────────────────────────────────────────
# type="political" → capture ALL posts (these are direct intelligence sources)
# type="news"      → capture only keyword-matching posts

MONITORED_PAGES = [
    # ── Political parties ────────────────────────────────────────────────────
    {"id": "upnd",                     "name": "UPND",                    "type": "political"},
    {"id": "PatrioticFrontZambia",     "name": "Patriotic Front",         "type": "political"},
    {"id": "nrpupzambia",              "name": "NRPUP",                   "type": "political"},

    # ── Party leaders & key politicians ─────────────────────────────────────
    {"id": "HakaindehichilemaNow",     "name": "Hakainde Hichilema",      "type": "political"},
    {"id": "BrianMundubile",           "name": "Brian Mundubile",         "type": "political"},
    {"id": "MakebiZuluOfficial",       "name": "Makebi Zulu",             "type": "political"},
    {"id": "EmmanuelMwamba",           "name": "Emmanuel Mwamba",         "type": "political"},
    {"id": "MilesSampa",               "name": "Miles Sampa",             "type": "political"},
    {"id": "BowmanLusambo",            "name": "Bowman Lusambo",          "type": "political"},
    {"id": "GivenLubindaOfficial",     "name": "Given Lubinda",           "type": "political"},
    {"id": "EdifyHamukale",            "name": "Edify Hamukale",          "type": "political"},

    # ── High-traffic Zambian media pages ────────────────────────────────────
    {"id": "mwebantu",                 "name": "Mwebantu",                "type": "news"},
    {"id": "kalemba",                  "name": "Kalemba",                 "type": "news"},
    {"id": "zambiawatchdog",           "name": "Zambian Watchdog",        "type": "news"},
    {"id": "diggersnewsonline",        "name": "Diggers News",            "type": "news"},
    {"id": "dailyrevelationzambia",    "name": "Daily Revelation",        "type": "news"},
    {"id": "zambiareports",            "name": "Zambia Reports",          "type": "news"},
    {"id": "lusakatimes",              "name": "Lusaka Times",            "type": "news"},
    {"id": "zambiamo",                 "name": "Zambia Daily Mail",       "type": "news"},
    {"id": "themastZambia",            "name": "The Mast Online",         "type": "news"},
    {"id": "ZNBCZambia",               "name": "ZNBC",                    "type": "news"},
    {"id": "zambianobserver",          "name": "Zambian Observer",        "type": "news"},
    {"id": "ZambiaMonitor",            "name": "Zambia Monitor",          "type": "news"},
]

# Keywords applied only to "news" pages (political pages bypass this filter)
SEARCH_TERMS = [
    # Cost-of-living
    "mealie meal", "fuel price", "load shedding", "cost of living",
    "ZESCO", "kwacha", "unemployment", "inflation", "prices",
    "poverty", "hunger", "school fees", "fertiliser", "FISP",
    "cost of food", "transport fare", "electricity bill",
    # Political / election
    "election", "vote", "ballot", "campaign", "2026",
    "PF", "UPND", "HH", "Mundubile", "Hichilema",
    "parliament", "manifesto", "opposition", "government",
    "ECZ", "Electoral Commission", "constituency",
]

GRAPH_BASE = "https://graph.facebook.com/v19.0"


async def fetch_page_posts(
    page_id: str,
    since_hours: int = 24,
    apply_keyword_filter: bool = True,
) -> list[dict]:
    """
    Fetch recent posts from a public Facebook page via the Graph API.

    Args:
        page_id: Facebook page username or numeric ID
        since_hours: How many hours back to look
        apply_keyword_filter: If False, return ALL posts regardless of content
    """
    if not settings.META_ACCESS_TOKEN:
        logger.warning("META_ACCESS_TOKEN not set — skipping Facebook scrape")
        return []

    since_ts = int((datetime.utcnow() - timedelta(hours=since_hours)).timestamp())

    params = {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
        "since": since_ts,
        "limit": 50,
        "access_token": settings.META_ACCESS_TOKEN,
    }

    posts = []
    url = f"{GRAPH_BASE}/{page_id}/posts"

    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                for post in data.get("data", []):
                    message = post.get("message", "")
                    if not message:
                        continue

                    if apply_keyword_filter:
                        msg_lower = message.lower()
                        if not any(term.lower() in msg_lower for term in SEARCH_TERMS):
                            continue

                    posts.append({
                        "external_id": post["id"],
                        "content": message,
                        "likes":    post.get("likes",    {}).get("summary", {}).get("total_count", 0),
                        "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares":   post.get("shares",   {}).get("count", 0),
                        "published_at": datetime.fromisoformat(
                            post["created_time"].replace("Z", "+00:00")
                        ),
                    })

                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # next URL already has params embedded

            except httpx.HTTPStatusError as e:
                logger.error(f"Facebook API error for {page_id}: {e.response.status_code}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching {page_id}: {e}")
                break

    return posts


async def scrape_all_pages(since_hours: int = 24) -> list[dict]:
    """Scrape all monitored pages and return combined post list."""
    all_posts = []
    for page in MONITORED_PAGES:
        logger.info(f"Scraping Facebook page: {page['name']} [{page['type']}]")
        # Political pages: capture everything; news pages: keyword-filter
        posts = await fetch_page_posts(
            page["id"],
            since_hours,
            apply_keyword_filter=(page["type"] == "news"),
        )
        for post in posts:
            post["source_name"] = page["name"]
            post["platform"]    = "facebook"
            post["source_url"]  = f"https://facebook.com/{page['id']}"
        all_posts.extend(posts)
        logger.info(f"  → {len(posts)} posts from {page['name']}")

    return all_posts
