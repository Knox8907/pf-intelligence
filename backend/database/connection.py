"""Database connection, session factory, and seed data."""
import gzip
import os
from pathlib import Path
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
    """Create all tables and seed keyword + voter register data on first run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # voter_register and tabulation_results are not in Base (created raw SQL)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS voter_register (
                id                    SERIAL PRIMARY KEY,
                province_num          VARCHAR(5)   NOT NULL,
                province_name         VARCHAR(100) NOT NULL,
                district_code         VARCHAR(10)  NOT NULL,
                district_name         VARCHAR(100) NOT NULL,
                constituency_num      VARCHAR(10)  NOT NULL,
                constituency_name     VARCHAR(100) NOT NULL,
                ward_code             VARCHAR(20)  NOT NULL,
                ward_name             VARCHAR(100) NOT NULL,
                polling_district_code VARCHAR(20)  NOT NULL,
                polling_district      VARCHAR(150) NOT NULL,
                polling_station       VARCHAR(200) NOT NULL,
                male                  INTEGER      NOT NULL DEFAULT 0,
                female                INTEGER      NOT NULL DEFAULT 0,
                total                 INTEGER      NOT NULL DEFAULT 0
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_province     ON voter_register(province_num)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_district     ON voter_register(district_code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_constituency ON voter_register(constituency_num)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_ward         ON voter_register(ward_code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_pd_code      ON voter_register(polling_district_code)"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tabulation_results (
                id                    SERIAL PRIMARY KEY,
                polling_district_code VARCHAR(20)  NOT NULL,
                polling_station       VARCHAR(200) NOT NULL,
                ward_code             VARCHAR(20)  NOT NULL,
                constituency_name     VARCHAR(100) NOT NULL,
                district_name         VARCHAR(100) NOT NULL,
                province_name         VARCHAR(100) NOT NULL,
                registered_voters     INTEGER      NOT NULL,
                votes_cast            INTEGER,
                pf_votes              INTEGER,
                upnd_votes            INTEGER,
                other_votes           INTEGER,
                rejected_ballots      INTEGER,
                agent_name            VARCHAR(200),
                notes                 TEXT,
                submitted_at          TIMESTAMP DEFAULT NOW(),
                is_verified           BOOLEAN DEFAULT FALSE
            )
        """))
        await conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_tab_station
            ON tabulation_results(polling_district_code)
        """))
    await seed_keywords()
    await seed_voter_register()


async def seed_voter_register():
    """Load ECZ 2026 voter register from bundled SQL seed if the table is empty."""
    seed_file = Path(__file__).parent / "migrations" / "voter_register_seed.sql.gz"
    if not seed_file.exists():
        return
    async with AsyncSessionLocal() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM voter_register"))).scalar()
        if count and count > 0:
            return
    # Use raw asyncpg for fast COPY-style bulk insert
    from sqlalchemy.pool import NullPool
    import asyncpg
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    try:
        sql = gzip.decompress(seed_file.read_bytes()).decode()
        # Execute statement by statement (INSERT INTO ... VALUES ...)
        statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
        for stmt in statements:
            if stmt:
                await conn.execute(stmt)
    finally:
        await conn.close()


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
