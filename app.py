"""Backward-compatible ASGI entrypoint.

Run with:
    uvicorn app:app --host 127.0.0.1 --port 8010
"""

from vox_local.main import app, health

__all__ = ["app", "health"]
