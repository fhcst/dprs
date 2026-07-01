"""Shared SlowAPI rate-limiter instance.

Import `limiter` from here in both main.py and router modules so every
module references the same object that is registered with the FastAPI app.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
