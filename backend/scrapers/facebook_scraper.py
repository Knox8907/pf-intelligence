"""
Facebook Graph API scraper.

Monitors public Facebook pages for posts mentioning
Zambian politics and cost-of-living issues.

Requirements:
- A Meta developer app with pages_read_engagement permission
- Page access tokens for pages you manage, OR
- A Meta research API access for public page data

Public pages monitored (read-only, no login required via Graph API):
  - Lusaka Times, Zambia Daily Mail, The Mast, ZNBC, etc.
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)

# Public Zambian news/political Facebook pages to monitor
# Replace page IDs with the actual numeric IDs from the Graph API
MONITORED_PAGES = [
    {"id": "lusakatimes",     "name": "Lusaka Times"},
    {"id": "zambiamo",        "name": "Zambia Daily Mail"},
    {"id": "themastZambia",   "name": "The Mast Online"},
    {"id": "ZNBCZambia",      "name": "ZNBC"},
    {"id": "zambianobserver", "name": "Zambian Observer"},
    {"id": "ZambiaMonitor",   "name": "Zambia Monitor"},
]

# Keywords to search for in post content
SEARCH_TERMS = [
    "mealie meal", "fuel price", "load shedding", "cost of living",
    "ZESCO", "kwacha", "unemployment", "inflation", "prices",
    "poverty", "hunger", "school fees", "fertiliser", "FISP",
    "cost of food", "transport fare", "electricity bill",
]

GRAPH_BASE = "https://graph.facebook.com/v19.0"


async def fetch_page_posts(page_id: str, since_hours: int = 24) -> list[dict]:
    """
    Fetch recent posts from a public Facebook page.

    Args:
        page_id: Page username or numeric ID
        since_hours: How many hours back to fetch

    Returns:
        List of post dicts with id, message, created_time, likes, comments, shares
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

                    # Only include posts mentioning our keywords
                    msg_lower = message.lower()
                    if not any(term.lower() in msg_lower for term in SEARCH_TERMS):
                        continue

                    posts.append({
                        "external_id": post["id"],
                        "content": message,
                        "likes": post.get("likes", {}).get("summary", {}).get("total_count", 0),
                        "comments": post.get("comments", {}).get("summary", {}).get("total_count", 0),
                        "shares": post.get("shares", {}).get("count", 0),
                        "published_at": datetime.fromisoformat(
                            post["created_time"].replace("Z", "+00:00")
                        ),
                    })

                # Handle pagination
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
    """
    Scrape all monitored pages and return combined post list.
    Each post includes the source_name field.
    """
    all_posts = []
    for page in MONITORED_PAGES:
        logger.info(f"Scraping Facebook page: {page['name']}")
        posts = await fetch_page_posts(page["id"], since_hours)
        for post in posts:
            post["source_name"] = page["name"]
            post["platform"] = "facebook"
            post["source_url"] = f"https://facebook.com/{page['id']}"
        all_posts.extend(posts)
        logger.info(f"  → {len(posts)} relevant posts from {page['name']}")

    return all_posts
