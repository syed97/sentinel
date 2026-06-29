"""
Web Push notification delivery via VAPID.
Called immediately when an Active-tier event is created.
Also used by the digest worker for daily summaries.
"""
import json
import logging
from pywebpush import webpush, WebPushException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import PushSubscription, User, Team, AlertTier
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_notification_payload(event: dict) -> str:
    """Build the JSON payload sent to the browser's push service."""
    tier_emoji = {
        AlertTier.ACTIVE: "🔴",
        AlertTier.MONITOR: "🟡",
        AlertTier.DIGEST: "📋",
    }
    emoji = tier_emoji.get(event.get("tier"), "")

    payload = {
        "title": f"{emoji} {event.get('event_type', 'Alert')} — {event.get('county_name', '')}",
        "body": event.get("headline", "")[:120],
        "icon": "/icons/icon-192.png",
        "badge": "/icons/badge-72.png",
        "data": {
            "event_id": str(event.get("id", "")),
            "url": f"/events/{event.get('id', '')}",
        }
    }
    return json.dumps(payload)


def send_push(subscription: PushSubscription, payload: str) -> bool:
    """Send a single push notification. Returns True on success."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                }
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": f"mailto:{settings.VAPID_EMAIL}",
            }
        )
        return True
    except WebPushException as e:
        logger.error(f"Push failed for endpoint {subscription.endpoint[:50]}...: {e}")
        return False


async def notify_team_active_event(db: AsyncSession, team_id: str, event: dict):
    """
    Fan out a push notification to all subscribed team members.
    Called immediately when an Active-tier event is saved.
    """
    # Get all users in the team
    users_result = await db.execute(
        select(User).where(User.team_id == team_id, User.is_active == True)
    )
    users = users_result.scalars().all()

    payload = build_notification_payload(event)
    sent = 0

    for user in users:
        subs_result = await db.execute(
            select(PushSubscription).where(PushSubscription.user_id == user.id)
        )
        subscriptions = subs_result.scalars().all()

        for sub in subscriptions:
            if send_push(sub, payload):
                sent += 1

    logger.info(f"Push notifications sent: {sent} for event {event.get('id')}")


async def send_digest_notification(db: AsyncSession, user: User, digest_summary: str):
    """Send the daily digest push notification to a single user."""
    payload = json.dumps({
        "title": "Sentinel Daily Digest",
        "body": digest_summary[:120],
        "icon": "/icons/icon-192.png",
        "data": {"url": "/digest"}
    })

    subs_result = await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    )
    subscriptions = subs_result.scalars().all()

    for sub in subscriptions:
        send_push(sub, payload)
