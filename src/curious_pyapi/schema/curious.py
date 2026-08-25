"""Curious schemas."""

from typing import Annotated

from pydantic.types import StringConstraints

CuriousId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-zA-Z0-9]{8}(-[a-zA-Z0-9]{4}){3}-[a-zA-Z0-9]{12}$"),
]
"""ID string for a Curious entity."""
