"""ExtensionRegistry — singleton registry for Protocol implementations."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Iterator, Type


class ExtensionRegistry:
    """
    Registry for Protocol-based extension points.

    Usage:
        registry.register(AuthProvider, "local", LocalAuthProvider())
        provider = registry.get(AuthProvider, "local")

    At registration time, the implementation is checked against the Protocol
    using isinstance (requires @runtime_checkable on the Protocol).
    """

    def __init__(self) -> None:
        self._store: dict[type, dict[str, Any]] = {}

    def register(self, protocol: type, key: str, impl: Any) -> None:
        """
        Register an implementation under a protocol type and key.

        Args:
            protocol: The @runtime_checkable Protocol class.
            key: String identifier for this implementation.
            impl: The implementation instance.

        Raises:
            TypeError: If impl does not satisfy the Protocol interface.
        """
        if not isinstance(impl, protocol):
            raise TypeError(
                f"{type(impl).__name__!r} does not implement "
                f"protocol {protocol.__name__!r}"
            )
        if protocol not in self._store:
            self._store[protocol] = {}
        self._store[protocol][key] = impl

    def get(self, protocol: type, key: str) -> Any:
        """
        Retrieve an implementation by protocol and key.

        Raises:
            KeyError: If no implementation is registered for the given key.
        """
        bucket = self._store.get(protocol, {})
        if key not in bucket:
            raise KeyError(
                f"No implementation registered for {protocol.__name__!r} "
                f"with key {key!r}"
            )
        return bucket[key]

    def get_all(self, protocol: type) -> dict[str, Any]:
        """Return all implementations registered for a protocol, keyed by name."""
        return dict(self._store.get(protocol, {}))


# Module-level singleton
registry = ExtensionRegistry()


class TestRegistry:
    """
    Context manager that replaces the module-level registry singleton
    with a fresh instance for test isolation.

    Usage:
        with TestRegistry() as test_reg:
            test_reg.register(AuthProvider, "mock", MockProvider())
            # ... run tests using the fresh registry ...
        # original registry restored after context exits
    """

    def __enter__(self) -> ExtensionRegistry:
        self._original = registry
        fresh = ExtensionRegistry()
        # Patch the module-level singleton
        _this_module = sys.modules[__name__]
        _this_module.registry = fresh
        # Also patch the extensions.registry package __init__
        import extensions.registry as pkg
        pkg.registry = fresh
        return fresh

    def __exit__(self, *args: Any) -> None:
        _this_module = sys.modules[__name__]
        _this_module.registry = self._original
        import extensions.registry as pkg
        pkg.registry = self._original
