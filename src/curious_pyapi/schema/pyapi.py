"""Curious-PyAPI schemas."""

import json
from typing import Optional

from pydantic import BaseModel, EmailStr, SecretStr
import httpx

from .curious import CuriousId
from ..utils.data import api_data
from ..utils.defaults import CURIOUS_BASE_URL
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CuriousAuth(BaseModel):
    """Required data for authentication and decryption."""

    curious_email: EmailStr
    curious_password: SecretStr
    applet_id: CuriousId
    applet_password: SecretStr

    @property
    def login_credentials(self) -> dict[str, str | SecretStr]:
        """Return email and password as dictionary for API request."""
        return {"email": self.curious_email, "password": self.curious_password}


class Tokens(BaseModel):
    """Curious tokens."""

    access: SecretStr
    refresh: SecretStr


def get_curious_token(
    curious_data: dict,
    curious_headers: Optional[dict] = None,
    curious_url: httpx.URL = CURIOUS_BASE_URL,
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
            logger.exception(
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


def headers(
    token: Optional[str] = None, headers: Optional[dict] = None
) -> dict[str, str]:
    """Return Curious headers."""
    auth = {"Authorization": f"Bearer {token}"} if token else {}
    return {"Content-Type": "application/json"} | auth | (headers or {})
