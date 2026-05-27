"""Database connection, session factory, and seed data."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from database.models import Base, Keyword
from config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI dependency — yields a db session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables and seed keyword data on first run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_keywords()


async def seed_keywords():
    """Insert default cost-of-living keyword tracking list."""
    keywords = [
        # Mealie meal
        ("mealie meal", "mealie_meal", "Mealie meal price", 2.0),
        ("nshima", "mealie_meal", "Mealie meal price", 2.0),
        ("25kg bag", "mealie_meal", "Mealie meal price", 1.8),
        ("breakfast meal", "mealie_meal", "Mealie meal price", 1.5),
        ("roller meal", "mealie_meal", "Mealie meal price", 1.5),
        # Fuel
        ("fuel price", "fuel", "Fuel costs", 2.0),
        ("petrol price", "fuel", "Fuel costs", 2.0),
        ("diesel price", "fuel", "Fuel costs", 2.0),
        ("fuel increase", "fuel", "Fuel costs", 1.8),
        ("pump price", "fuel", "Fuel costs", 1.5),
        # Electricity
        ("load shedding", "electricity", "Electricity/ZESCO", 2.0),
        ("ZESCO", "electricity", "Electricity/ZESCO", 2.0),
        ("power cut", "electricity", "Electricity/ZESCO", 1.8),
        ("electricity bill", "electricity", "Electricity/ZESCO", 1.8),
        ("load management", "electricity", "Electricity/ZESCO", 1.5),
        # Employment
        ("unemployment", "employment", "Youth unemployment", 2.0),
        ("job loss", "employment", "Youth unemployment", 1.8),
        ("retrenchment", "employment", "Youth unemployment", 1.8),
        ("no jobs", "employment", "Youth unemployment", 1.5),
        ("graduates unemployed", "employment", "Youth unemployment", 2.0),
        # Kwacha
        ("kwacha", "kwacha", "Kwacha depreciation", 1.5),
        ("exchange rate", "kwacha", "Kwacha depreciation", 1.8),
        ("dollar rate", "kwacha", "Kwacha depreciation", 1.8),
        ("inflation", "kwacha", "Kwacha depreciation", 1.5),
        # Fertiliser
        ("fertiliser", "fertiliser", "Fertiliser/farming", 1.8),
        ("FISP", "fertiliser", "Fertiliser/farming", 2.0),
        ("subsidy", "fertiliser", "Fertiliser/farming", 1.5),
        ("farming input", "fertiliser", "Fertiliser/farming", 1.5),
        # School/health
        ("school fees", "education", "School/medical fees", 1.5),
        ("hospital fees", "education", "School/medical fees", 1.5),
        ("drug shortage", "education", "School/medical fees", 1.8),
        ("medicine shortage", "education", "School/medical fees", 1.8),
    ]

    async with AsyncSessionLocal() as session:
        existing = await session.execute(text("SELECT COUNT(*) FROM keywords"))
        count = existing.scalar()
        if count == 0:
            for term, issue, display, weight in keywords:
                kw = Keyword(term=term, issue=issue, display_name=display, weight=weight)
                session.add(kw)
            await session.commit()
