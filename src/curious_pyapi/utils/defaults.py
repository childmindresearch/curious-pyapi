"""Default values."""

from typing import Optional

from httpx import URL

CURIOUS_BASE_URL = URL("https://api-v2.gettingcurious.com")
"""Canonical URL for Curious API."""


def headers(
    token: Optional[str] = None, headers: Optional[dict] = None
) -> dict[str, str]:
    """Return Curious headers."""
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    return {"Content-Type": "application/json"} | auth | (headers or {})
