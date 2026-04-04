"""User Beanie Document and related models."""
from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import IndexModel


class IdentityTag(str, Enum):
    """Identity classification tags — separate from permission flags."""
    TEACHER = "teacher"
    STUDENT = "student"
    STAFF   = "staff"


class StudentProfile(BaseModel):
    """Embedded profile for students only."""
    class_name: str = ""    # Administrative class (e.g. "302班")
    seat_number: int = 0    # Seat number within the class


class User(Document):
    username: str
    hashed_password: str
    display_name: str
    name: str = ""                                      # Real name (管理者才能改)
    email: str = ""
    permissions: int = 0
    identity_tags: list[IdentityTag] = Field(default_factory=list)
    student_profile: StudentProfile | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_active: bool = True

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("username", 1)], unique=True),
        ]
