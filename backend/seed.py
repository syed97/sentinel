"""
Seed script — run once after migration to populate:
  1. The pilot team and its 24 counties
  2. Default RSS sources for the Northeast region
  3. Default message templates
  4. First admin user (you'll be prompted for email/password)

Usage:
  python seed.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime
from getpass import getpass

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Make sure app is importable
sys.path.insert(0, os.path.dirname(__file__))

from app.models.models import (
    Team, TeamCounty, TeamRSSSource, User, MessageTemplate, UserRole
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set.")
    sys.exit(1)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Pilot team counties ────────────────────────────────────────────────────────
PILOT_COUNTIES = [
    {"fips": "25025", "name": "Suffolk County",          "state": "MA"},
    {"fips": "25017", "name": "Middlesex County",        "state": "MA"},
    {"fips": "36055", "name": "Monroe County",           "state": "NY"},
    {"fips": "36001", "name": "Albany County",           "state": "NY"},
    {"fips": "36027", "name": "Dutchess County",         "state": "NY"},
    {"fips": "36059", "name": "Nassau County",           "state": "NY"},
    {"fips": "36005", "name": "Bronx County",            "state": "NY"},
    {"fips": "36081", "name": "Queens County",           "state": "NY"},
    {"fips": "36047", "name": "Kings County",            "state": "NY"},
    {"fips": "36061", "name": "New York County",         "state": "NY"},
    {"fips": "36085", "name": "Richmond County",         "state": "NY"},
    {"fips": "09001", "name": "Fairfield County",        "state": "CT"},
    {"fips": "34023", "name": "Middlesex County",        "state": "NJ"},
    {"fips": "42101", "name": "Philadelphia County",     "state": "PA"},
    {"fips": "42071", "name": "Lancaster County",        "state": "PA"},
    {"fips": "24031", "name": "Montgomery County",       "state": "MD"},
    {"fips": "24033", "name": "Prince George's County",  "state": "MD"},
    {"fips": "51013", "name": "Arlington County",        "state": "VA"},
    {"fips": "51059", "name": "Fairfax County",          "state": "VA"},
    {"fips": "51087", "name": "Henrico County",          "state": "VA"},
    {"fips": "51041", "name": "Chesterfield County",     "state": "VA"},
    {"fips": "51085", "name": "Hanover County",          "state": "VA"},
    {"fips": "51760", "name": "Richmond City",           "state": "VA"},
    {"fips": "11001", "name": "Washington DC",           "state": "DC"},
]

# ── Default RSS sources ────────────────────────────────────────────────────────
DEFAULT_RSS_SOURCES = [
    {"url": "https://www.boston.com/rss/news",           "label": "Boston Globe",              "state": "MA"},
    {"url": "https://www.wcvb.com/rss",                  "label": "WCVB Boston",               "state": "MA"},
    {"url": "https://www.nbcnewyork.com/feed/",          "label": "NBC New York",              "state": "NY"},
    {"url": "https://www.ny1.com/nyc/all-boroughs/rss.xml", "label": "NY1 Spectrum News",     "state": "NY"},
    {"url": "https://www.wtnh.com/feed/",                "label": "WTNH News 8 Connecticut",  "state": "CT"},
    {"url": "https://www.nj.com/rss/news/",              "label": "NJ.com",                   "state": "NJ"},
    {"url": "https://www.nbcphiladelphia.com/feed/",     "label": "NBC10 Philadelphia",        "state": "PA"},
    {"url": "https://www.inquirer.com/rss/",             "label": "Philadelphia Inquirer",     "state": "PA"},
    {"url": "https://www.wbal.com/rss/",                 "label": "WBAL Baltimore",            "state": "MD"},
    {"url": "https://www.washingtonpost.com/rss/local",  "label": "Washington Post Local",     "state": "DC"},
    {"url": "https://www.nbcwashington.com/feed/",       "label": "NBC4 Washington",           "state": "DC"},
    {"url": "https://www.nbc12.com/rss/",                "label": "NBC12 Richmond",            "state": "VA"},
    {"url": "https://richmond.com/rss/",                 "label": "Richmond Times-Dispatch",   "state": "VA"},
]

# ── Default message templates ──────────────────────────────────────────────────
DEFAULT_TEMPLATES = [
    {
        "name": "Active Alert — General",
        "body": (
            "[{{severity}}] {{event_type}} — {{county}}\n\n"
            "As of {{time}}, {{source}} has issued a {{event_type}} for {{county}}.\n\n"
            "{{summary}}\n\n"
            "Source: {{source_link}}\n"
            "— {{team_name}}"
        ),
    },
    {
        "name": "Monitor — Situation Update",
        "body": (
            "[MONITOR] {{event_type}} — {{county}}\n\n"
            "Situation developing as of {{time}}.\n\n"
            "{{summary}}\n\n"
            "We are monitoring this event and will provide updates as needed.\n"
            "Source: {{source_link}}\n"
            "— {{team_name}}"
        ),
    },
    {
        "name": "All Clear",
        "body": (
            "[ALL CLEAR] {{event_type}} — {{county}}\n\n"
            "The {{event_type}} for {{county}} has ended as of {{time}}.\n\n"
            "No further action required at this time.\n"
            "— {{team_name}}"
        ),
    },
]


async def seed():
    print("\n── Sentinel Seed Script ──────────────────────────────")

    # Prompt for first admin user credentials
    print("\nCreate your first admin user:")
    admin_name  = input("  Full name: ").strip()
    admin_email = input("  Email:     ").strip()
    admin_pass  = getpass("  Password:  ")
    if not admin_name or not admin_email or not admin_pass:
        print("ERROR: All fields are required.")
        sys.exit(1)

    hashed_pw = pwd_context.hash(admin_pass)

    async with SessionLocal() as db:
        # 1. Create pilot team
        print("\n[1/4] Creating pilot team...")
        team = Team(
            id=uuid.uuid4(),
            name="Northeastern US Disaster Management",
            created_at=datetime.utcnow(),
        )
        db.add(team)
        await db.flush()

        # 2. Add counties
        print(f"[2/4] Adding {len(PILOT_COUNTIES)} counties...")
        for c in PILOT_COUNTIES:
            db.add(TeamCounty(
                id=uuid.uuid4(),
                team_id=team.id,
                fips_code=c["fips"],
                county_name=c["name"],
                state_code=c["state"],
            ))

        # 3. Add RSS sources
        print(f"[3/4] Adding {len(DEFAULT_RSS_SOURCES)} RSS sources...")
        for s in DEFAULT_RSS_SOURCES:
            db.add(TeamRSSSource(
                id=uuid.uuid4(),
                team_id=team.id,
                url=s["url"],
                label=s["label"],
                state_code=s["state"],
                active=True,
            ))

        # 4. Add message templates
        print(f"      Adding {len(DEFAULT_TEMPLATES)} message templates...")
        for t in DEFAULT_TEMPLATES:
            db.add(MessageTemplate(
                id=uuid.uuid4(),
                team_id=team.id,
                name=t["name"],
                body=t["body"],
                created_at=datetime.utcnow(),
            ))

        # 5. Create first admin user
        print("[4/4] Creating admin user...")
        admin = User(
            id=uuid.uuid4(),
            team_id=team.id,
            email=admin_email,
            name=admin_name,
            hashed_password=hashed_pw,
            role=UserRole.ADMIN,
            digest_time="09:00",
            timezone="America/New_York",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(admin)

        await db.commit()

    print("\n── Seed complete ─────────────────────────────────────")
    print(f"  Team:  Northeastern US Disaster Management")
    print(f"  Admin: {admin_email}")
    print(f"  Login at your Railway URL or http://localhost:5173 (local)")
    print()


if __name__ == "__main__":
    asyncio.run(seed())
