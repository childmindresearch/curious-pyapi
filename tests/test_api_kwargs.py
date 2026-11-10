"""Tests for ApiKwargs helper."""

from curious_pyapi.schema.pyapi import ApiKwargs


def test_unpack_defaults():
    """Test default unpacking."""
    assert ApiKwargs.unpack({}) == (False, None, False)


def test_unpack_all():
    """Test unpacking all values."""
    assert ApiKwargs.unpack({"dry": True, "limit": 5, "verbose": True}) == (
        True,
        5,
        True,
    )


def test_unpack_partial():
    """Test partial unpacking."""
    assert ApiKwargs.unpack({"limit": 3}) == (False, 3, False)
