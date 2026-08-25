"""Curious API functionality."""

import json
from typing import Optional
import httpx

from pydantic import AnyHttpUrl

from ..schema.pyapi import Tokens
from ..utils.defaults import CURIOUS_BASE_URL, headers
from ..utils.data import api_data
from ..utils.logging import get_logger

LOGGER = get_logger(__name__)


def get_curious_token(
    curious_data: dict,
    curious_headers: Optional[dict] = None,
    curious_url: httpx.URL | AnyHttpUrl = CURIOUS_BASE_URL,
) -> Optional[Tokens]:
    """Process the response to a POST request to the specified URL.

    Parameters
    ----------
    curious_data
        The data to include in the POST request.
    curious_headers
        The headers to include in the POST request.
    curious_url
        The URL to send the POST request to.

    Returns
    -------
    Tokens or None
        An object containing (access, refresh) token strings, or None if unsuccessful.

    Raises
    ------
    RuntimeError
        If there is an error with the request or response.

    """
    curious_headers = headers(headers=curious_headers)
    if isinstance(curious_url, str):
        curious_url = httpx.URL(curious_url)
    assert isinstance(curious_url, httpx.URL)
    try:
        # Sending the POST request
        response = httpx.post(
            curious_url.join("/auth/login"),
            json=api_data(curious_data),
            headers=curious_headers,
        )
        if response.status_code == httpx.codes.OK:
            response_data = response.json()  # Convert response to JSON
            access_token = (
                response_data.get("result", {})
                .get("token", {})
                .get("accessToken", None)
            )  # Get access token
            refresh_token = (
                response_data.get("result", {})
                .get("token", {})
                .get("refreshToken", None)
            )  # Get refresh token
        else:
            LOGGER.exception(
                "Failed to fetch data: %d - %s", response.status_code, response.text
            )
            response.raise_for_status()
            return None

        return Tokens(access=access_token, refresh=refresh_token)

    except httpx.HTTPError as e:
        msg = f"Error sending request: {e}"
        raise RuntimeError(msg) from e
    except json.JSONDecodeError as e:
        msg = f"Error: Response is not valid JSON! {e}"
        raise RuntimeError(msg) from e
