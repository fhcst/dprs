"""Tests for the Extension Registry and Protocols."""
import pytest
from contextlib import contextmanager


# --- Protocol existence tests ---

def test_auth_provider_protocol_exists():
    from extensions.protocols import AuthProvider
    assert AuthProvider is not None


def test_reward_provider_protocol_exists():
    from extensions.protocols import RewardProvider
    assert RewardProvider is not None


def test_badge_trigger_protocol_exists():
    from extensions.protocols import BadgeTrigger
    assert BadgeTrigger is not None


def test_submission_validator_protocol_exists():
    from extensions.protocols import SubmissionValidator
    assert SubmissionValidator is not None


# --- Registry tests ---

def test_registry_is_singleton():
    from extensions.registry import registry as r1
    from extensions.registry import registry as r2
    assert r1 is r2


def test_registry_register_and_get():
    from extensions.registry import ExtensionRegistry
    from extensions.protocols import AuthProvider
    from typing import runtime_checkable, Protocol

    @runtime_checkable
    class _TestProvider(AuthProvider, Protocol):
        pass

    class MockProvider:
        async def authenticate(self, credentials):
            return None

    reg = ExtensionRegistry()
    reg.register(AuthProvider, "test", MockProvider())
    result = reg.get(AuthProvider, "test")
    assert result is not None


def test_registry_unknown_key_raises():
    from extensions.registry import ExtensionRegistry
    from extensions.protocols import AuthProvider

    reg = ExtensionRegistry()
    with pytest.raises(KeyError):
        reg.get(AuthProvider, "nonexistent")


def test_registry_invalid_impl_raises():
    from extensions.registry import ExtensionRegistry
    from extensions.protocols import AuthProvider

    reg = ExtensionRegistry()

    class BadImpl:
        pass  # Does not implement AuthProvider

    with pytest.raises(TypeError):
        reg.register(AuthProvider, "bad", BadImpl())


# --- TestRegistry helper ---

def test_test_registry_isolates_and_restores():
    from extensions.registry import registry, TestRegistry
    from extensions.protocols import AuthProvider

    class MockProvider:
        async def authenticate(self, credentials):
            return None

    # Before context: registry should not have "isolated_test"
    with pytest.raises(KeyError):
        registry.get(AuthProvider, "isolated_test")

    with TestRegistry() as test_reg:
        test_reg.register(AuthProvider, "isolated_test", MockProvider())
        result = test_reg.get(AuthProvider, "isolated_test")
        assert result is not None

    # After context: original registry restored, key not present
    with pytest.raises(KeyError):
        registry.get(AuthProvider, "isolated_test")


# --- FastAPI Depends factories ---

def test_get_auth_provider_factory_exists():
    from extensions.deps import get_auth_provider
    assert callable(get_auth_provider)


def test_get_reward_providers_factory_exists():
    from extensions.deps import get_reward_providers
    assert callable(get_reward_providers)


def test_get_badge_triggers_factory_exists():
    from extensions.deps import get_badge_triggers
    assert callable(get_badge_triggers)


def test_get_submission_validators_factory_exists():
    from extensions.deps import get_submission_validators
    assert callable(get_submission_validators)


def test_get_reward_providers_returns_list_of_impls():
    """get_reward_providers() must return a list of implementation objects, not dict keys."""
    from extensions.registry import TestRegistry
    from extensions.protocols import RewardProvider
    from extensions.deps import get_reward_providers

    class FakeRewardProvider:
        async def award(self, event):
            pass

    with TestRegistry() as reg:
        reg.register(RewardProvider, "test_rp", FakeRewardProvider())
        result = get_reward_providers()
        assert isinstance(result, list), f"Expected list, got {type(result)}"
        assert len(result) == 1
        assert isinstance(result[0], FakeRewardProvider), (
            f"Expected FakeRewardProvider instance, got {type(result[0])}"
        )
