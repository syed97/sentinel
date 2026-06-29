"""Initial schema - all tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-01

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # teams
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # team_counties
    op.create_table(
        "team_counties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("fips_code", sa.String(5), nullable=False),
        sa.Column("county_name", sa.String(255), nullable=False),
        sa.Column("state_code", sa.String(2), nullable=False),
    )
    op.create_index("ix_team_counties_team_id", "team_counties", ["team_id"])
    op.create_index("ix_team_counties_fips", "team_counties", ["fips_code"])

    # team_keywords
    op.create_table(
        "team_keywords",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_team_keywords_team_id", "team_keywords", ["team_id"])

    # team_rss_sources
    op.create_table(
        "team_rss_sources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("state_code", sa.String(2), nullable=True),
        sa.Column("active", sa.Boolean, default=True),
    )
    op.create_index("ix_team_rss_sources_team_id", "team_rss_sources", ["team_id"])

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin", "member", name="userrole"), nullable=False, server_default="member"),
        sa.Column("digest_time", sa.String(5), default="09:00"),
        sa.Column("timezone", sa.String(50), default="America/New_York"),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_users_team_id", "users", ["team_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # push_subscriptions
    op.create_table(
        "push_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text, nullable=False),
        sa.Column("p256dh", sa.Text, nullable=False),
        sa.Column("auth", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    # events (live, rolling 30-day window)
    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("tier", sa.Enum("active", "monitor", "digest", name="alerttier"), nullable=False),
        sa.Column("county_fips", sa.String(5), nullable=True),
        sa.Column("county_name", sa.String(255), nullable=True),
        sa.Column("state_code", sa.String(2), nullable=True),
        sa.Column("headline", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("issued_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("reviewed", sa.Boolean, default=False),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_events_team_id", "events", ["team_id"])
    op.create_index("ix_events_tier", "events", ["tier"])
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_external_id", "events", ["external_id"])

    # event_archive (long-term storage, same schema + archived_at)
    op.create_table(
        "event_archive",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("tier", sa.Enum("active", "monitor", "digest", name="alerttier"), nullable=False),
        sa.Column("county_fips", sa.String(5), nullable=True),
        sa.Column("county_name", sa.String(255), nullable=True),
        sa.Column("state_code", sa.String(2), nullable=True),
        sa.Column("headline", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("issued_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("reviewed", sa.Boolean, default=False),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("archived_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_event_archive_team_id", "event_archive", ["team_id"])
    op.create_index("ix_event_archive_created_at", "event_archive", ["created_at"])

    # message_templates
    op.create_table(
        "message_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_message_templates_team_id", "message_templates", ["team_id"])


def downgrade() -> None:
    op.drop_table("message_templates")
    op.drop_table("event_archive")
    op.drop_table("events")
    op.drop_table("push_subscriptions")
    op.drop_table("users")
    op.drop_table("team_rss_sources")
    op.drop_table("team_keywords")
    op.drop_table("team_counties")
    op.drop_table("teams")
    op.execute("DROP TYPE IF EXISTS alerttier")
    op.execute("DROP TYPE IF EXISTS userrole")
