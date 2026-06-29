"""
Message template renderer.
Simple variable substitution — no external library needed.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.models.models import Event, MessageTemplate


TEMPLATE_VARIABLES = [
    "event_type", "county", "severity", "time",
    "summary", "source", "source_link", "team_name"
]


def render_template(template: MessageTemplate, event: Event, team_name: str, timezone: str = "America/New_York") -> str:
    """
    Render a message template by substituting variables with event data.
    Returns the rendered string ready to copy and send.
    """
    tz = ZoneInfo(timezone)
    event_time = event.issued_at
    if event_time:
        local_time = event_time.astimezone(tz)
        formatted_time = local_time.strftime("%B %-d, %Y at %-I:%M %p %Z")
    else:
        formatted_time = datetime.now(tz).strftime("%B %-d, %Y at %-I:%M %p %Z")

    county_str = event.county_name or "Unknown County"
    if event.state_code:
        county_str = f"{county_str}, {event.state_code}"

    variables = {
        "event_type": event.event_type or "",
        "county": county_str,
        "severity": event.tier.value.upper() if event.tier else "",
        "time": formatted_time,
        "summary": event.summary or "",
        "source": event.source.upper() if event.source else "",
        "source_link": event.source_url or "",
        "team_name": team_name,
    }

    rendered = template.body
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)

    return rendered


def get_variable_list() -> list[dict]:
    """Return variable metadata for the template builder UI."""
    return [
        {"variable": "{{event_type}}", "description": "Category of event", "example": "Tornado Warning"},
        {"variable": "{{county}}", "description": "Affected county and state", "example": "Fairfield County, CT"},
        {"variable": "{{severity}}", "description": "Alert tier", "example": "ACTIVE"},
        {"variable": "{{time}}", "description": "Time event was issued", "example": "June 20, 2026 at 9:14 AM EDT"},
        {"variable": "{{summary}}", "description": "Event summary from source", "example": "A tornado warning is in effect..."},
        {"variable": "{{source}}", "description": "Originating source", "example": "NWS"},
        {"variable": "{{source_link}}", "description": "URL to original alert", "example": "https://alerts.weather.gov/..."},
        {"variable": "{{team_name}}", "description": "Regional team name", "example": "Northeastern US Disaster Management"},
    ]
