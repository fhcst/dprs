"""Trigger-rule Beanie Documents."""
from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class TriggerRule(Document):
    """A DSL-based trigger rule scoped to a class."""
    class_id: str
    name: str
    expression: str  # DSL expression text
    is_active: bool = True
    created_by: str  # user_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "triggerrules"
