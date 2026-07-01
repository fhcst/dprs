"""SystemConfig — singleton Beanie Document for system-level settings."""
from beanie import Document


class SystemConfig(Document):
    site_name: str
    admin_email: str
    join_request_reject_cooldown_hours: int = 24

    class Settings:
        name = "system_config"
