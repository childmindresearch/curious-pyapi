"""Curious schemas."""

from typing import Annotated

import polars as pl
from pydantic.types import StringConstraints

from .regex import EMAIL_REGEX
from ..utils.logging import get_logger

LOGGER = get_logger(__name__)


@pl.api.register_dataframe_namespace("curious_pyapi")
class CuriousAccount:
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
        self._df = df


def enforce_schema(self) -> pl.DataFrame:
    """Enforces schema, adds missing columns with nulls, and casts types."""
    exprs = [
        pl.col(col).cast(dtype)
        if col in self._df.columns
        else pl.lit(None, dtype=dtype).alias(col)
        for col, dtype in self.SCHEMA.items()
    ]

    out_df = self._df.select(exprs)

    # Evaluate against out_df where 'email' is guaranteed to exist
    is_valid_email = pl.col("email").str.contains(EMAIL_REGEX).fill_null(False)

    failures_df = out_df.filter(~is_valid_email)
    out_df = out_df.filter(is_valid_email)

    if not failures_df.is_empty():
        log_cols = [
            col
            for col in ["email", "secretUserId", "nickname"]
            if col in failures_df.columns
        ]
        LOGGER.error(
            "Dropped %d records due to invalid email addresses:\n%s",
            failures_df.height,
            failures_df.select(log_cols),
        )

    return out_df


CuriousId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-zA-Z0-9]{8}(-[a-zA-Z0-9]{4}){3}-[a-zA-Z0-9]{12}$"),
]
"""ID string for a Curious entity."""
