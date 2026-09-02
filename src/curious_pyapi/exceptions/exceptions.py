"""Custom exceptions and exception handling."""

import json
from typing import Any, Callable

from httpx import codes, HTTPStatusError, RequestError, Response


def allow_existing(
    post: Callable[[], Response], *, warn_if_existing: bool = True, **kwargs: Any
) -> Response | None:
    """Post, but allow existing."""
    try:
        response = post(**kwargs)
    except Exception as e:
        if hasattr(e, "response"):
            _response = getattr(e, "response")
            if getattr(_response, "status_code") == codes.BAD_REQUEST:
                results = getattr(_response, "json")().get("result", [])
                if results:
                    if isinstance(results[0], dict):
                        _request = getattr(e, "request")
                        warning: tuple[str, ...]
                        message = results[0].get("message")
                        match message:
                            case (
                                "That email address is already associated "
                                "with a Curious account."
                            ):
                                warning = (
                                    "%s is already associated with a Curious account.",
                                    str(
                                        json.loads(
                                            getattr(_request, "content", json.dumps({}))
                                        ).get("email", "That email address")
                                    ),
                                )
                            case "Non-unique value.":
                                warning = (
                                    (
                                        "A record with the same unique "
                                        "value already exists."
                                    ),
                                )
                            case _:
                                raise
                        if warn_if_existing:
                            from ..utils.logging import get_logger  # noqa: PLC0415

                            logger = get_logger(__name__)
                            logger.warning(*warning)
                        return None
        raise
    return response


class ApiStatusError(HTTPStatusError):
    """Raised when an API request returns a non-successful status code."""


class AuthenticationError(RequestError):
    """Raised when authentication fails."""


class CuriousApiError(RequestError):
    """Raised for general Curious API errors."""
