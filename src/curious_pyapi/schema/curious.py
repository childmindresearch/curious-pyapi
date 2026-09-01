"""Curious schemas."""

from collections.abc import Mapping
from typing import Annotated

import polars as pl
from pydantic.types import StringConstraints

from ..utils.logging import get_logger
from .regex import EMAIL_REGEX

LOGGER = get_logger(__name__)


type IntStr = int | str
"""Integer or integers string."""
type IntStrContainer = list[IntStr] | set[IntStr] | tuple[IntStr, ...]
"""Iterable container of integers and/or integers strings."""
type Record = (
    dict[str, IntStr | IntStrContainer] | Mapping[str, IntStr | IntStrContainer]
)
"""Dictionary/mapping with string keys and IntStr or IntStrContainer values."""


def _validate(
    df: pl.DataFrame, schema: pl.Schema, required_cols: list[str]
) -> pl.DataFrame:
    """Validate DataFrame, adding missing columns with nulls and casting types."""
    exprs = [
        pl.col(col).cast(dtype)
        if col in df.columns
        else pl.lit(None, dtype=dtype).alias(col)
        for col, dtype in schema.items()
    ]

    out_df = df.select(exprs)

    # Evaluate against out_df where 'email' is guaranteed to exist
    is_valid_email = pl.col("email").str.contains(EMAIL_REGEX).fill_null(False)

    failures_df = out_df.filter(~is_valid_email)
    out_df = out_df.filter(is_valid_email)

    if not failures_df.is_empty():
        log_cols = [col for col in required_cols if col in failures_df.columns]
        LOGGER.error(
            "Dropped %d records due to invalid email addresses:\n%s",
            failures_df.height,
            failures_df.select(log_cols),
        )

    return out_df


@pl.api.register_dataframe_namespace("curious_account")
class CuriousAccount:
    """Curious account invitation."""

    SCHEMA = pl.Schema(
        {
            "email": pl.String,
            "firstName": pl.String,
            "lastName": pl.String,
            "language": pl.String,
            "secretUserId": pl.String,
            "nickname": pl.String,
            "tag": pl.String,
        }
    )

    def __init__(self, df: pl.DataFrame):
        """Initialize CuriousAccount."""
        self._df = df

    def enforce_schema(self) -> pl.DataFrame:
        """Enforces schema, adds missing columns with nulls, and casts types."""
        return _validate(self._df, self.SCHEMA, ["email", "secretUserId", "nickname"])


CuriousId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-zA-Z0-9]{8}(-[a-zA-Z0-9]{4}){3}-[a-zA-Z0-9]{12}$"),
]
"""ID string for a Curious entity."""


@pl.api.register_dataframe_namespace("new_curious_user")
class NewUserData:
    """Required data for creating a new Curious user account."""

    SCHEMA = pl.Schema(
        {
            "email": pl.String,
            "firstName": pl.String,
            "lastName": pl.String,
            "password": pl.String,
        }
    )

    def __init__(self, df: pl.DataFrame):
        """Initialize NewUserData."""
        self._df = df

    def enforce_schema(self) -> pl.DataFrame:
        """Enforces schema, adds missing columns with nulls, and casts types."""
        return _validate(
            self._df, self.SCHEMA, ["email", "firstName", "lastName", "password"]
        )
