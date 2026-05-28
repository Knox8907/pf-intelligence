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
RE_CODE         = re.compile(r'^\d{12}\s+')

# Primary regex: district name ends with ' - N', station name ends with '-NN'
# Handles apostrophes, mixed case district names, and missing spaces.
RE_DATA = re.compile(
    r'^(\d{12})\s+'
    r"(.+?)\s+-\s+(\d+)\s*"   # district name + ' - N' (zero or more spaces after N)
    r'(.+?-\d{2,})\s+'        # station name ending in -NN
    r'([\d,]+)\s+'            # male
    r'([\d,]+)\s+'            # female
    r'[\d.]+\s+'              # % male (skip)
    r'[\d.]+\s+'              # % female (skip)
    r'([\d,]+)$'              # total voters
)

# Column x-boundaries (calibrated from word-level extraction across multiple pages)
X_CODE_MAX    = 90    # code column ends here
X_DISTRICT_MAX = 207  # district name column ends here
X_STATION_MAX  = 390  # station name column ends here


def clean_int(s: str) -> int:
    return int(s.replace(',', '').strip())


def words_for_code(page, code: str) -> list | None:
    """Return the ordered list of words on the row that starts with `code`."""
    words = page.extract_words(x_tolerance=2, y_tolerance=3)
    # Build rows keyed by rounded y
    rows: dict[float, list] = {}
    for w in words:
        y = round(w['top'] / 3) * 3
        rows.setdefault(y, []).append(w)
    for ws in rows.values():
        if any(w['text'] == code for w in ws):
            return sorted(ws, key=lambda w: w['x0'])
    return None


def parse_from_words(words: list) -> dict | None:
    """
    Use x-position to split words into district / station / numbers columns.
    Returns {polling_district, polling_station, male, female, total} or None.
    """
    district_words, station_words, number_words = [], [], []
    for w in words:
        x = w['x0']
        if x < X_CODE_MAX:
            continue  # skip the code itself
        elif x < X_DISTRICT_MAX:
            district_words.append(w['text'])
        elif x < X_STATION_MAX:
            station_words.append(w['text'])
        else:
            number_words.append(w['text'])

    if len(number_words) < 3:
        return None

    # Numbers: male, female, %male, %female, total (in order)
    nums = []
    for t in number_words:
        try:
            nums.append(clean_int(t.replace('%', '')))
        except ValueError:
            continue
    if len(nums) < 3:
        return None

    male, female, total = nums[0], nums[1], nums[-1]

    # Reconstruct names — join, strip garbled prefix/suffix tokens
    district = ' '.join(district_words).strip()
    station  = ' '.join(station_words).strip()

    if not station:
        return None

    return {
        "polling_district": district,
        "polling_station":  station,
        "male":   male,
        "female": female,
        "total":  total,
    }


def parse_pdf() -> list[dict]:
    rows = []
    province_num = province_name = ""
    district_code = district_name = ""
    constituency_num = constituency_name = ""
    ward_code = ward_name = ""
    missed_codes: list[str] = []

    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        # ── Pass 1: text-line parsing ─────────────────────────────
        for page_idx, page in enumerate(pdf.pages):
            if page_idx % 50 == 0:
                print(f"  Page {page_idx+1}/{total_pages}...", flush=True)
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
                    district = (m.group(2) + ' - ' + m.group(3)).strip()
                    rows.append({
                        "province_num":          province_num,
                        "province_name":         province_name,
                        "district_code":         district_code,
                        "district_name":         district_name,
                        "constituency_num":      constituency_num,
                        "constituency_name":     constituency_name,
                        "ward_code":             ward_code,
                        "ward_name":             ward_name,
                        "polling_district_code": m.group(1),
                        "polling_district":      district,
                        "polling_station":       m.group(4).strip(),
                        "male":                  clean_int(m.group(5)),
                        "female":                clean_int(m.group(6)),
                        "total":                 clean_int(m.group(7)),
                    })
                elif RE_CODE.match(line):
                    # Record context so fallback pass can use it
                    code = line.split()[0]
                    missed_codes.append((
                        code, province_num, province_name,
                        district_code, district_name,
                        constituency_num, constituency_name,
                        ward_code, ward_name,
                    ))

    print(f"  Pass 1: {len(rows)} rows, {len(missed_codes)} unmatched", flush=True)
    if not missed_codes:
        return rows

    # ── Pass 2: word-position fallback for unmatched codes ────────
    print("  Pass 2: word-position fallback...", flush=True)
    missed_set = {t[0] for t in missed_codes}
    context_map = {t[0]: t[1:] for t in missed_codes}
    recovered = 0

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            codes_on_page = [c for c in missed_set if c in text]
            if not codes_on_page:
                continue
            for code in codes_on_page:
                ws = words_for_code(page, code)
                if ws is None:
                    continue
                result = parse_from_words(ws)
                if result is None:
                    continue
                ctx = context_map[code]
                rows.append({
                    "province_num":          ctx[0],
                    "province_name":         ctx[1],
                    "district_code":         ctx[2],
                    "district_name":         ctx[3],
                    "constituency_num":      ctx[4],
                    "constituency_name":     ctx[5],
                    "ward_code":             ctx[6],
                    "ward_name":             ctx[7],
                    "polling_district_code": code,
                    "polling_district":      result["polling_district"],
                    "polling_station":       result["polling_station"],
                    "male":                  result["male"],
                    "female":               result["female"],
                    "total":                result["total"],
                })
                missed_set.discard(code)
                recovered += 1

    print(f"  Pass 2 recovered: {recovered} | Still missing: {len(missed_set)}", flush=True)
    if missed_set:
        print(f"  Unrecoverable codes: {sorted(missed_set)[:10]}", flush=True)
    return rows


async def load_to_db(rows: list[dict]):
    async with AsyncSessionLocal() as session:
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

        # Truncate and reload
        await session.execute(text("TRUNCATE voter_register RESTART IDENTITY CASCADE"))
        print(f"  Inserting {len(rows)} rows...", flush=True)
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
                print(f"    {i+len(batch)}/{len(rows)} rows...", flush=True)
        await session.commit()
        print(f"  Done. {len(rows)} rows committed.", flush=True)


async def main():
    print("Parsing PDF...", flush=True)
    rows = parse_pdf()
    print(f"Total parsed: {len(rows)} polling station rows.", flush=True)
    if not rows:
        print("ERROR: No rows parsed.", file=sys.stderr)
        sys.exit(1)
    print("Loading into database...", flush=True)
    await load_to_db(rows)
    print("Complete.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
