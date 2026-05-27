"""
News site scraper for Zambian political and economics news.
Uses httpx + BeautifulSoup to scrape public news sites.
No API key required — standard web scraping of public content.
"""
import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# ── News sources ─────────────────────────────────────────────────────────────
# All selectors target standard WordPress themes.
# If a site returns 0 articles, inspect its HTML and adjust the selectors.
NEWS_SOURCES = [
    {
        "name": "Mwebantu",
        "base_url": "https://www.mwebantu.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h3.entry-title a, h2 a",
        "content_selector": "div.entry-content p, div.post-content p",
        "date_selector": "time.entry-date, time",
    },
    {
        "name": "Kalemba",
        "base_url": "https://www.kalemba.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h2 a",
        "content_selector": "div.entry-content p, div.td-post-content p",
        "date_selector": "time.entry-date, time",
    },
    {
        "name": "Zambian Watchdog",
        "base_url": "https://www.zambiawatchdog.com",
        "feed_path": "/",
        "article_selector": "article.post, article",
        "title_selector": "h2.entry-title a, h1.entry-title a, h2 a",
        "content_selector": "div.entry-content p",
        "date_selector": "time.entry-date, time",
    },
    {
        "name": "Diggers News",
        "base_url": "https://diggersnews.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h2 a",
        "content_selector": "div.entry-content p, div.post-entry p",
        "date_selector": "time.entry-date, span.date, time",
    },
    {
        "name": "Daily Revelation",
        "base_url": "https://www.daily-revelation.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h2 a",
        "content_selector": "div.entry-content p",
        "date_selector": "time.entry-date, time",
    },
    {
        "name": "Zambia Reports",
        "base_url": "https://zambiareports.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a, h2 a",
        "content_selector": "div.entry-content p",
        "date_selector": "time.entry-date, time",
    },
    {
        "name": "Zambia Monitor",
        "base_url": "https://www.zambiamonitor.com",
        "feed_path": "/category/economy/",
        "article_selector": "article.post",
        "title_selector": "h2.entry-title a",
        "content_selector": "div.entry-content p",
        "date_selector": "time.entry-date",
    },
    {
        "name": "Zambian Observer",
        "base_url": "https://zambianobserver.com",
        "feed_path": "/",
        "article_selector": "article",
        "title_selector": "h2 a",
        "content_selector": "div.entry-content p",
        "date_selector": "time",
    },
    {
        "name": "Lusaka Times",
        "base_url": "https://www.lusakatimes.com",
        "feed_path": "/category/economy/",
        "article_selector": "article.post",
        "title_selector": "h2.post-title a",
        "content_selector": "div.entry p",
        "date_selector": "span.date",
    },
    {
        "name": "The Mast Online",
        "base_url": "https://www.themastonline.com",
        "feed_path": "/category/economy/",
        "article_selector": "article",
        "title_selector": "h2 a",
        "content_selector": "div.entry-content p",
        "date_selector": "time",
    },
]

# Keywords used to decide whether an article is relevant
RELEVANT_KEYWORDS = [
    # Cost-of-living
    "mealie meal", "fuel price", "electricity", "load shedding",
    "cost of living", "inflation", "kwacha", "unemployment",
    "poverty", "hunger", "school fees", "hospital", "fertiliser",
    "price increase", "prices have", "cost of food", "transport",
    "zesco", "fisp", "subsidy",
    # Political / election
    "election", "vote", "ballot", "campaign", "2026",
    "patriotic front", " pf ", " upnd ", "hichilema", "mundubile",
    "parliament", "manifesto", "opposition", "constituency",
    "ecz", "electoral commission", "political party",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def is_relevant(text: str) -> bool:
    """Return True if the text matches any tracked keyword."""
    t = text.lower()
    return any(kw in t for kw in RELEVANT_KEYWORDS)


def _select_first(tag, selector: str):
    """Try each comma-separated CSS selector and return the first match."""
    for s in selector.split(","):
        s = s.strip()
        result = tag.select_one(s)
        if result:
            return result
    return None


def _select_all(tag, selector: str):
    """Try each comma-separated CSS selector and return results from the first match."""
    for s in selector.split(","):
        s = s.strip()
        results = tag.select(s)
        if results:
            return results
    return []


async def scrape_site(source: dict) -> list[dict]:
    """Scrape a single news site and return article list."""
    articles = []
    url = source["base_url"] + source["feed_path"]

    async with httpx.AsyncClient(timeout=20, headers=HEADERS,
                                  follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to fetch {source['name']}: {e}")
            return []

    soup = BeautifulSoup(resp.text, "html.parser")
    article_tags = _select_all(soup, source["article_selector"])[:20]

    async with httpx.AsyncClient(timeout=20, headers=HEADERS,
                                  follow_redirects=True) as client:
        for art in article_tags:
            try:
                title_tag = _select_first(art, source["title_selector"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                article_url = title_tag.get("href", "")
                if article_url and not article_url.startswith("http"):
                    article_url = urljoin(source["base_url"], article_url)

                if not is_relevant(title):
                    continue

                try:
                    art_resp = await client.get(article_url)
                    art_soup = BeautifulSoup(art_resp.text, "html.parser")
                    paragraphs = _select_all(art_soup, source["content_selector"])
                    content = " ".join(p.get_text(strip=True) for p in paragraphs[:10])
                except Exception:
                    content = title

                date_tag = _select_first(art, source["date_selector"])
                pub_date = None
                if date_tag:
                    dt_str = date_tag.get("datetime") or date_tag.get_text(strip=True)
                    try:
                        pub_date = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    except Exception:
                        pub_date = datetime.utcnow()

                full_text = f"{title}. {content}"
                if not is_relevant(full_text):
                    continue

                articles.append({
                    "external_id": article_url,
                    "platform": "news",
                    "source_name": source["name"],
                    "source_url": article_url,
                    "content": full_text[:2000],
                    "published_at": pub_date or datetime.utcnow(),
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                })

            except Exception as e:
                logger.debug(f"Error processing article from {source['name']}: {e}")

    logger.info(f"  → {len(articles)} relevant articles from {source['name']}")
    return articles


async def scrape_all_news() -> list[dict]:
    """Scrape all configured news sites."""
    all_articles = []
    for source in NEWS_SOURCES:
        logger.info(f"Scraping news site: {source['name']}")
        articles = await scrape_site(source)
        all_articles.extend(articles)
    return all_articles
