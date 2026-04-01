"""FastAPI Depends factories for Extension Registry."""
from typing import Any

import extensions.registry as _registry_pkg
from extensions.protocols import AuthProvider, BadgeTrigger, RewardProvider, SubmissionValidator


def get_auth_provider(key: str = "local"):
    """Return a FastAPI Depends factory for the AuthProvider with the given key."""
    def _dep() -> Any:
        return _registry_pkg.registry.get(AuthProvider, key)
    return _dep


def get_reward_providers() -> list[Any]:
    """Return all registered RewardProvider implementations as a list."""
    return list(_registry_pkg.registry.get_all(RewardProvider).values())


def get_badge_triggers() -> list[Any]:
    """Return all registered BadgeTrigger implementations as a list."""
    return list(_registry_pkg.registry.get_all(BadgeTrigger).values())


def get_submission_validators() -> list[Any]:
    """Return all registered SubmissionValidator implementations as a list."""
    return list(_registry_pkg.registry.get_all(SubmissionValidator).values())
