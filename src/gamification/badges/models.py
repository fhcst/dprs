"""Badge system Beanie Documents."""
from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field, model_validator



class BadgeDefinition(Document):
    """A badge that can be awarded to students."""
    class_id: str
    name: str
    description: str
    icon: str = "🏅"
    trigger_key: Optional[str] = None  # key into ExtensionRegistry; None = manual only
    trigger_rule_id: Optional[str] = None  # DSL trigger rule reference; mutually exclusive with trigger_key
    created_by: str  # teacher user_id

    @model_validator(mode="after")
    def _check_trigger_exclusivity(self) -> "BadgeDefinition":
        if self.trigger_key is not None and self.trigger_rule_id is not None:
            raise ValueError("trigger_key and trigger_rule_id are mutually exclusive")
        return self

    class Settings:
        name = "badgedefinitions"


class BadgeAward(Document):
    """Records a badge awarded to a student."""
    badge_id: str
    student_id: str
    class_id: str
    awarded_by: str = "system"  # "system" or teacher user_id
    reason: Optional[str] = None
    awarded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Soft delete fields — None means active, non-None means revoked
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None  # teacher user_id who revoked

    class Settings:
        name = "badgeawards"
