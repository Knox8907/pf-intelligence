"""
Parse ECZ 'Registered Voters per Polling Station 2026' PDF into the voter_register table.
Run from backend/ directory:
  python3 parse_voter_register.py
"""
import re
import sys
import asyncio
import pdfplumber
from sqlalchemy import text
from database.connection import AsyncSessionLocal

PDF_PATH = "/media/sf_VMShare/rptPDListing20260508 voters per polling station.pdf"

RE_PROVINCE     = re.compile(r'^Province:\s+(\d+)\s+(.+?)(?:\s+0)?$')
RE_DISTRICT     = re.compile(r'^District\s+(\w+)\s+(.+)$')
RE_CONSTITUENCY = re.compile(r'^Constituency\s+(\d+)\s+(.+)$')
RE_WARD         = re.compile(r'^Ward\s*:\s*(\S+)\s*,\s*(.+)$')
RE_TOTAL        = re.compile(r'^Totals for (Ward|District|Constituency|Province|Report)')
RE_HEADER       = re.compile(r'^Polling District\s+Polling Station')
# Data row: 12-digit code, UPPER district name, Title-case station name, 5 numbers
RE_DATA         = re.compile(
    r'^(\d{12})\s+'           # polling district code
    r'([A-Z0-9][A-Z0-9 \-]+?)\s+'  # polling district name (ALL CAPS)
    r'([A-Z][a-z].+?)\s+'    # polling station name (Title case)
    r'([\d,]+)\s+'            # male
    r'([\d,]+)\s+'            # female
    r'[\d.]+\s+'              # % male (skip)
    r'[\d.]+\s+'              # % female (skip)
    r'([\d,]+)$'              # total voters
)


def clean_int(s: str) -> int:
    return int(s.replace(',', ''))


def parse_pdf() -> list[dict]:
    rows = []
    province_num = province_name = ""
    district_code = district_name = ""
    constituency_num = constituency_name = ""
    ward_code = ward_name = ""

    with pdfplumber.open(PDF_PATH) as pdf:
        total = len(pdf.pages)
        for page_idx, page in enumerate(pdf.pages):
            if page_idx % 50 == 0:
                print(f"  Page {page_idx+1}/{total}...", flush=True)
            text = page.extract_text()
            if not text:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if RE_HEADER.match(line) or RE_TOTAL.match(line):
                    continue

                m = RE_PROVINCE.match(line)
                if m:
                    province_num, province_name = m.group(1), m.group(2).strip()
                    continue

                m = RE_DISTRICT.match(line)
                if m:
                    district_code, district_name = m.group(1), m.group(2).strip()
                    continue

                m = RE_CONSTITUENCY.match(line)
                if m:
                    constituency_num, constituency_name = m.group(1), m.group(2).strip()
                    continue

                m = RE_WARD.match(line)
                if m:
                    ward_code, ward_name = m.group(1), m.group(2).strip()
                    continue

                m = RE_DATA.match(line)
                if m:
                    rows.append({
                        "province_num":       province_num,
                        "province_name":      province_name,
                        "district_code":      district_code,
                        "district_name":      district_name,
                        "constituency_num":   constituency_num,
                        "constituency_name":  constituency_name,
                        "ward_code":          ward_code,
                        "ward_name":          ward_name,
                        "polling_district_code": m.group(1),
                        "polling_district":   m.group(2).strip(),
                        "polling_station":    m.group(3).strip(),
                        "male":               clean_int(m.group(4)),
                        "female":             clean_int(m.group(5)),
                        "total":              clean_int(m.group(6)),
                    })

    return rows


async def load_to_db(rows: list[dict]):
    async with AsyncSessionLocal() as session:
        # Create table if not exists
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS voter_register (
                id                   SERIAL PRIMARY KEY,
                province_num         VARCHAR(5)   NOT NULL,
                province_name        VARCHAR(100) NOT NULL,
                district_code        VARCHAR(10)  NOT NULL,
                district_name        VARCHAR(100) NOT NULL,
                constituency_num     VARCHAR(10)  NOT NULL,
                constituency_name    VARCHAR(100) NOT NULL,
                ward_code            VARCHAR(20)  NOT NULL,
                ward_name            VARCHAR(100) NOT NULL,
                polling_district_code VARCHAR(20) NOT NULL,
                polling_district     VARCHAR(150) NOT NULL,
                polling_station      VARCHAR(200) NOT NULL,
                male                 INTEGER      NOT NULL DEFAULT 0,
                female               INTEGER      NOT NULL DEFAULT 0,
                total                INTEGER      NOT NULL DEFAULT 0
            )
        """))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_province ON voter_register(province_num)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_district ON voter_register(district_code)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_constituency ON voter_register(constituency_num)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_ward ON voter_register(ward_code)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS ix_vr_pd_code ON voter_register(polling_district_code)"))

        # Also create the tabulation table while we're here
        await session.execute(text("""
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
        await session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_tab_station
            ON tabulation_results(polling_district_code)
        """))

        # Clear and reload
        count = (await session.execute(text("SELECT COUNT(*) FROM voter_register"))).scalar()
        if count and count > 0:
            print(f"  voter_register already has {count} rows — skipping insert.")
            await session.commit()
            return

        print(f"  Inserting {len(rows)} rows into voter_register...", flush=True)
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            await session.execute(
                text("""
                    INSERT INTO voter_register
                        (province_num, province_name, district_code, district_name,
                         constituency_num, constituency_name, ward_code, ward_name,
                         polling_district_code, polling_district, polling_station,
                         male, female, total)
                    VALUES
                        (:province_num, :province_name, :district_code, :district_name,
                         :constituency_num, :constituency_name, :ward_code, :ward_name,
                         :polling_district_code, :polling_district, :polling_station,
                         :male, :female, :total)
                """),
                batch
            )
            if (i // batch_size) % 10 == 0:
                print(f"    {i+len(batch)}/{len(rows)} rows inserted...", flush=True)

        await session.commit()
        print(f"  Done. {len(rows)} rows committed.", flush=True)


async def main():
    print("Parsing PDF...", flush=True)
    rows = parse_pdf()
    print(f"Parsed {len(rows)} polling station rows.", flush=True)
    if not rows:
        print("ERROR: No rows parsed — check regex or PDF format.", file=sys.stderr)
        sys.exit(1)
    print("Loading into database...", flush=True)
    await load_to_db(rows)
    print("Complete.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
