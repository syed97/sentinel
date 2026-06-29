"""
NWS Worker - polls api.weather.gov for active alerts.
Runs every 5 minutes via APScheduler.
No API key required.
"""
import httpx
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Event, Team, TeamCounty, AlertTier
from app.workers.classifier import classify_nws_event
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"


async def fetch_nws_alerts(fips_codes: list[str]) -> list[dict]:
    """
    Fetch active NWS alerts for a list of county FIPS codes.
    NWS accepts comma-separated FIPS codes in the 'county' parameter.
    Max ~50 per request; we chunk if needed.
    """
    alerts = []
    chunk_size = 50
    chunks = [fips_codes[i:i+chunk_size] for i in range(0, len(fips_codes), chunk_size)]

    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            # NWS expects FIPS prefixed with state FIPS; county param uses full 5-digit FIPS
            params = {"county": ",".join(chunk)}
            try:
                resp = await client.get(NWS_ALERTS_URL, params=params, headers={
                    "User-Agent": "Sentinel Disaster Management Dashboard (contact@sentinel.app)",
                    "Accept": "application/geo+json"
                })
                resp.raise_for_status()
                data = resp.json()
                alerts.extend(data.get("features", []))
            except Exception as e:
                logger.error(f"NWS fetch error for chunk {chunk}: {e}")

    return alerts


def parse_nws_alert(feature: dict, team_id: str) -> dict | None:
    """Parse a GeoJSON feature from NWS into our Event schema."""
    props = feature.get("properties", {})
    if not props:
        return None

    event_type = props.get("event", "Unknown")
    headline = props.get("headline") or props.get("event", "NWS Alert")
    summary = props.get("description", "")
    source_url = props.get("@id", "")
    external_id = props.get("id", source_url)

    # Parse affected zones/counties
    # NWS returns geocode with FIPS list
    geocode = props.get("geocode", {})
    fips_list = geocode.get("SAME", [])  # SAME codes are 6-digit, first digit is country, next 5 are county FIPS
    county_fips = fips_list[0][1:] if fips_list else None  # strip leading 0

    # Parse times
    sent = props.get("sent")
    expires = props.get("expires")
    issued_at = datetime.fromisoformat(sent.replace("Z", "+00:00")) if sent else None
    expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00")) if expires else None

    tier = classify_nws_event(event_type)

    return {
        "team_id": team_id,
        "source": "nws",
        "event_type": event_type,
        "tier": tier,
        "county_fips": county_fips,
        "headline": headline[:512],
        "summary": summary,
        "source_url": source_url,
        "external_id": external_id,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


async def run_nws_worker():
    """Main worker entry point. Called by APScheduler."""
    logger.info("NWS worker: starting poll")

    async with AsyncSessionLocal() as db:
        # Get all teams and their county FIPS codes
        teams_result = await db.execute(select(Team))
        teams = teams_result.scalars().all()

        for team in teams:
            counties_result = await db.execute(
                select(TeamCounty).where(TeamCounty.team_id == team.id)
            )
            counties = counties_result.scalars().all()
            fips_codes = [c.fips_code for c in counties]

            if not fips_codes:
                continue

            alerts = await fetch_nws_alerts(fips_codes)
            new_count = 0

            for feature in alerts:
                parsed = parse_nws_alert(feature, str(team.id))
                if not parsed:
                    continue

                # Deduplication: skip if external_id already exists for this team
                existing = await db.execute(
                    select(Event).where(
                        Event.team_id == team.id,
                        Event.external_id == parsed["external_id"]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                event = Event(**parsed)
                db.add(event)
                new_count += 1

            await db.commit()
            logger.info(f"NWS worker: {new_count} new events for team {team.name}")
