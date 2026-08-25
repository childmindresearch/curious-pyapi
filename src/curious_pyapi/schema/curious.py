"""Curious schemas."""

from typing import Annotated

import polars as pl
from pydantic.types import StringConstraints


@pl.api.register_dataframe_namespace("curious_pyapi")
class CuriousAccount:
    SCHEMA = pl.Schema(
        {
            "record": pl.String,
            "firstName": pl.String,
            "nickname": pl.String,
            "role": pl.String,
            "tag": pl.String,
            "accountType": pl.String,
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
        return self._df.select(exprs)


CuriousId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-zA-Z0-9]{8}(-[a-zA-Z0-9]{4}){3}-[a-zA-Z0-9]{12}$"),
]
"""ID string for a Curious entity."""
