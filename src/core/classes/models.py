"""Class, ClassMembership, and JoinRequest Beanie Documents."""
from datetime import datetime, timezone
from typing import Literal

from beanie import Document
from pymongo import IndexModel, ASCENDING
from pydantic import BaseModel, Field

ClassVisibility = Literal["public", "private"]
MemberRole = Literal["student", "teacher"]
JoinRequestStatus = Literal["pending", "approved", "rejected"]


class DiscordTemplate(BaseModel):
    title_format: str = ""
    description_template: str = ""
    footer_text: str = ""


class Class(Document):
    name: str
    description: str = ""
    visibility: ClassVisibility
    owner_id: str
    invite_code: str
    leaderboard_enabled: bool = True
    is_archived: bool = False
    discord_webhook_url: str | None = None
    discord_template: DiscordTemplate | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "classes"


class ClassMembership(Document):
    class_id: str
    user_id: str
    role: MemberRole
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "classmemberships"
        indexes = [
            IndexModel(
                [("class_id", ASCENDING), ("user_id", ASCENDING)],
                unique=True,
            ),
        ]


class JoinRequest(Document):
    class_id: str
    user_id: str
    status: JoinRequestStatus = "pending"
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    invite_code_used: str

    class Settings:
        name = "join_requests"
