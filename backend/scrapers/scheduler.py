"""
Scraper scheduler.
Runs the Facebook and news scrapers on a schedule,
processes sentiment, and stores results to the database.

Run with: python -m scrapers.scheduler
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from scrapers.facebook_scraper import scrape_all_pages
from scrapers.news_scraper import scrape_all_news
from database.connection import AsyncSessionLocal
from database.models import Post, Sentiment, ProvinceScore
from nlp.sentiment import analyse_sentiment, compute_province_score
from config import settings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def run_scrape_cycle():
    """Full scrape → analyse → store cycle."""
    logger.info("=" * 50)
    logger.info(f"Scrape cycle started at {datetime.utcnow().isoformat()}")

    # 1. Collect raw posts from all sources
    facebook_posts = await scrape_all_pages(since_hours=settings.SCRAPE_INTERVAL_MINUTES / 60 + 1)
    news_articles   = await scrape_all_news()
    all_items = facebook_posts + news_articles
    logger.info(f"Total items collected: {len(all_items)}")

    if not all_items:
        logger.info("No new items — skipping.")
        return

    # 2. Store and analyse
    new_count = 0
    async with AsyncSessionLocal() as session:
        for item in all_items:
            # Skip duplicates (by external_id)
            ext_id = item.get("external_id")
            if ext_id:
                existing = await session.execute(
                    select(Post).where(Post.external_id == ext_id)
                )
                if existing.scalar_one_or_none():
                    continue

            # Run sentiment analysis
            analysis = analyse_sentiment(item["content"])

            # Create Post record
            post = Post(
                external_id  = ext_id,
                platform     = item["platform"],
                source_name  = item["source_name"],
                source_url   = item.get("source_url"),
                content      = item["content"],
                province     = analysis["province"],
                likes        = item.get("likes", 0),
                comments     = item.get("comments", 0),
                shares       = item.get("shares", 0),
                published_at = item.get("published_at", datetime.utcnow()),
                is_processed = True,
            )
            session.add(post)
            await session.flush()  # get post.id

            # Create Sentiment record
            sent = Sentiment(
                post_id      = post.id,
                label        = analysis["label"],
                score        = analysis["score"],
                issues_found = analysis["issues"],
            )
            session.add(sent)
            new_count += 1

        await session.commit()

    logger.info(f"Stored {new_count} new posts with sentiment.")

    # 3. Recompute province scores
    await update_province_scores()


async def update_province_scores():
    """Recalculate grievance scores for all 10 provinces."""
    from collections import defaultdict

    provinces = [
        "Lusaka", "Copperbelt", "Eastern", "Southern", "Central",
        "Western", "Northern", "Luapula", "North-Western", "Muchinga"
    ]

    async with AsyncSessionLocal() as session:
        for province in provinces:
            # Get last 7 days of posts for this province
            result = await session.execute(
                select(Sentiment, Post)
                .join(Post, Sentiment.post_id == Post.id)
                .where(Post.province == province)
            )
            rows = result.all()

            if not rows:
                continue

            post_count = len(rows)
            neg_count  = sum(1 for s, p in rows if s.label == "negative")
            neg_pct    = (neg_count / post_count) * 100
            avg_pol    = sum(s.score * (-1 if s.label == "negative" else 1)
                             for s, p in rows) / post_count

            # Find top issue
            issue_counts = defaultdict(int)
            for s, p in rows:
                for issue in (s.issues_found or []):
                    issue_counts[issue] += 1
            top_issue = max(issue_counts, key=issue_counts.get) if issue_counts else None

            score = compute_province_score(neg_pct / 100, post_count, avg_pol)

            ps = ProvinceScore(
                province   = province,
                score      = score,
                post_count = post_count,
                neg_pct    = round(neg_pct, 1),
                top_issue  = top_issue,
            )
            session.add(ps)

        await session.commit()
    logger.info("Province scores updated.")


def start_scheduler():
    """Start the APScheduler background job."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scrape_cycle,
        "interval",
        minutes=settings.SCRAPE_INTERVAL_MINUTES,
        id="scrape_cycle",
        next_run_time=datetime.now(),  # run immediately on start
    )
    scheduler.start()
    logger.info(f"Scheduler started — running every {settings.SCRAPE_INTERVAL_MINUTES} min")
    return scheduler


if __name__ == "__main__":
    async def main():
        scheduler = start_scheduler()
        try:
            await asyncio.Event().wait()   # run forever
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()

    asyncio.run(main())
