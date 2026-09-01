"""Data utilities."""

from pydantic import SecretStr

from ..schema.curious import Record


def api_data(data: Record | dict[str, str | SecretStr]) -> Record:
    """Prep data for API calls."""
    return {
        k: v.get_secret_value() if isinstance(v, SecretStr) else v
        for k, v in data.items()
    }
