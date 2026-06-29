"""
Alert classification logic.
Assigns an AlertTier to every incoming event based on source and event type.
"""
from app.models.models import AlertTier

# NWS event types that map directly to Active tier
NWS_ACTIVE_TYPES = {
    "Tornado Warning",
    "Tornado Emergency",
    "Flash Flood Emergency",
    "Flash Flood Warning",
    "Severe Thunderstorm Warning",
    "Hurricane Warning",
    "Tropical Storm Warning",
    "Winter Storm Warning",
    "Blizzard Warning",
    "Ice Storm Warning",
    "Extreme Wind Warning",
    "Dust Storm Warning",
    "Tsunami Warning",
    "Evacuation Immediate",
}

# NWS event types that map to Monitor tier
NWS_MONITOR_TYPES = {
    "Tornado Watch",
    "Flash Flood Watch",
    "Severe Thunderstorm Watch",
    "Hurricane Watch",
    "Tropical Storm Watch",
    "Winter Storm Watch",
    "Blizzard Watch",
    "Ice Storm Watch",
    "Flood Watch",
    "High Wind Watch",
    "Tropical Depression",
    "Tropical Storm",            # Developing, not yet warning level
    "Hurricane",                 # Category tracking before warning issued
}

# Everything else from NWS defaults to Digest
# (Advisories, Statements, Outlooks, etc.)


def classify_nws_event(event_type: str) -> AlertTier:
    """Classify a National Weather Service event by type string."""
    if event_type in NWS_ACTIVE_TYPES:
        return AlertTier.ACTIVE
    if event_type in NWS_MONITOR_TYPES:
        return AlertTier.MONITOR
    return AlertTier.DIGEST


def classify_fema_event(event_type: str) -> AlertTier:
    """FEMA IPAWS events are always Active tier."""
    return AlertTier.ACTIVE


def classify_rss_event(text: str, keywords: list[str]) -> AlertTier:
    """
    RSS events are Monitor if they match a team keyword, Digest otherwise.
    Human review is required before a Monitor RSS item can become Active.
    """
    if not keywords:
        return AlertTier.DIGEST

    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return AlertTier.MONITOR

    return AlertTier.DIGEST


def classify_event(
    source: str,
    event_type: str,
    text: str = "",
    keywords: list[str] = None,
) -> AlertTier:
    """
    Main entry point. Dispatch to source-specific classifier.
    source: one of 'nws', 'fema', 'rss', 'manual'
    """
    if source == "nws":
        return classify_nws_event(event_type)
    if source == "fema":
        return classify_fema_event(event_type)
    if source == "rss":
        return classify_rss_event(text, keywords or [])
    # Manual events default to Monitor so a human sets the final tier
    return AlertTier.MONITOR
