"""Data utilities."""

from pydantic import SecretStr


def api_data(data: dict) -> dict:
    """Prep data for API calls."""
    return {
        k: v.get_secret_value() if isinstance(v, SecretStr) else v
        for k, v in data.items()
    }
