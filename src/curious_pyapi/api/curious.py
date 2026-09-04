"""Curious API functionality."""

import json
from typing import Any, Optional

import httpx
import polars as pl
from pydantic import AnyHttpUrl, SecretStr

from ..exceptions import ApiStatusError, AuthenticationError, CuriousApiError
from ..schema.curious import CuriousId, NewUserData, Record
from ..schema.pyapi import ApiClient, CuriousAuth, EndpointPath, Tokens, url
from ..utils.data import api_data
from ..utils.defaults import CURIOUS_BASE_URL, headers
from ..utils.logging import get_logger

LOGGER = get_logger(__name__)


class CuriousApiClient(ApiClient):
    """API Client managing authentication, connection pooling, and endpoint routing."""

    # Declarative Endpoints
    applets = EndpointPath("/applets")
    applet_by_id = EndpointPath("/applets/{applet_id}")
    auth_login = EndpointPath("/auth/login")
    invite_user = EndpointPath("/invitations/{applet_id}/{user_type}")
    invitations = EndpointPath("/invitations")
    invitation_accept = EndpointPath("/invitations/{key}/accept")

    me = EndpointPath("/users/me")
    user_create = EndpointPath("/users")

    def __init__(
        self,
        *,
        auth: Optional[CuriousAuth] = None,
        base_url: httpx.URL | AnyHttpUrl = CURIOUS_BASE_URL,
    ) -> None:
        """Initialize Curious API Client."""
        self.base_url = httpx.URL(str(base_url))
        self._tokens: Optional[Tokens] = None
        self._auth_header: Optional[str] = None
        self._my_name: Optional[str] = None
        self._applets: dict[str, Applet] = {}

        # Always initialize a valid client instance
        self._client = httpx.Client(
            base_url=str(self.base_url),
            follow_redirects=True,
            event_hooks={
                "request": [self._inject_auth_header],
                "build": [self._inject_auth_header],
            },
        )

        if auth:
            self.authenticate(auth)
            # Pre-load applets only after successful authentication
            self.get_applets(refresh=True)

    def __str__(self) -> str:
        """Return string representation of Curious API client without side-effects."""
        name_str = self._my_name if self._my_name else "Unauthenticated"
        return f"CuriousApiClient({name_str})"

    def __repr__(self) -> str:
        """Return reproducible string without triggering network calls."""
        name_str = f'"{self._my_name}"' if self._my_name else "None"
        return f'CuriousApiClient(name={name_str}, base_url="{self.base_url}")'

    def fetch_name(self) -> str:
        """Fetch and return the user's name from the API."""
        me = self.me.get()
        me_json = me.json().get("result", {})

        first = me_json.get("firstName", "")
        last = me_json.get("lastName", "")
        self._my_name = " ".join(filter(None, [first, last]))
        return self._my_name

    @property
    def my_name(self) -> str:
        """Return memoized string name, fetching only if authenticated and missing."""
        if self._my_name is None:
            if self.is_authenticated:
                self.fetch_name()
            else:
                return "Unauthenticated"
        assert isinstance(self._my_name, str)
        return self._my_name

    def _inject_auth_header(self, request: httpx.Request) -> None:
        """Event hook executed right before any request is sent over the wire."""
        if self._auth_header:
            request.headers["Authorization"] = self._auth_header

    def get_applets(self, refresh: bool = False) -> None:
        """Gather bound Applets into a dict."""
        if not refresh and self._applets:
            return

        applets: "dict[str, Applet]" = {}
        result = self.applets.get().json().get("result", [])
        for applet in result:
            if {"displayName", "id"}.issubset(applet):
                applets[applet["displayName"]] = Applet(
                    self, applet["id"], display_name=applet["displayName"]
                )
        self._applets = applets

    @property
    def is_authenticated(self) -> bool:
        """Return True if the client is authenticated."""
        return self._auth_header is not None

    def authenticate(self, auth: CuriousAuth) -> None:
        """Authenticate immediately and store Bearer token."""
        tokens = self._fetch_tokens(auth.login_credentials)
        if not tokens.access:
            msg = "Authentication succeeded but accessToken was empty."
            raise AuthenticationError(msg)

        self._tokens = tokens
        self._auth_header = f"Bearer {tokens.access.get_secret_value()}"
        LOGGER.info("Successfully authenticated as Bearer token.")

    def _fetch_tokens(self, credentials: dict[str, str | SecretStr]) -> Tokens:
        """Post login credentials to obtain tokens."""
        target_url = str(self.base_url.join(httpx.URL("auth/login")))
        try:
            response = httpx.post(
                target_url,
                json=api_data(credentials),
                headers=headers(),
            )

            if httpx.codes.is_success(response.status_code):
                data = response.json()
                token_data = data.get("result", {}).get("token", {})
                access = token_data.get("accessToken")
                refresh = token_data.get("refreshToken")

                if not access:
                    msg = f"Auth response missing 'accessToken': {data}"
                    raise AuthenticationError(msg)

                return Tokens(access=access, refresh=refresh)

            msg = f"Login failed with status {response.status_code}: {response.text}"
            raise AuthenticationError(msg)

        except (httpx.HTTPError, json.JSONDecodeError) as e:
            msg = f"Authentication request failed: {e}"
            raise AuthenticationError(msg) from e

    def _retry_request(
        self, error: str, method: str, path: str, _retries: int, **kwargs: Any
    ) -> httpx.Response:
        """Retry the request if retries are left, otherwise raise an error."""
        LOGGER.warning(
            "%s error on '%s' request to '%s'. Retrying... (%d retries left)",
            error,
            method,
            path,
            _retries,
        )
        return self.request(method, path, _retries=_retries - 1, **kwargs)

    def request(
        self, method: str, path: str | httpx.URL, *, _retries: int = 3, **kwargs: Any
    ) -> httpx.Response:
        """Centralized transport gateway with error mapping and auth checking."""
        clean_path = str(path).lstrip("/")

        if not self.is_authenticated:
            LOGGER.warning(
                "Attempting unauthenticated '%s' request to '%s'", method, clean_path
            )
        try:
            response = self._client.request(method, clean_path, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.BAD_GATEWAY and _retries > 0:
                return self._retry_request(
                    "Bad gateway", method, clean_path, _retries - 1, **kwargs
                )
            LOGGER.debug("Sent Headers: %s", dict(e.request.headers))
            LOGGER.debug("Response Error Details: %s", e.response.text)
            raise ApiStatusError(
                str(e.response), request=e.request, response=e.response
            ) from e
        except httpx.HTTPError as e:
            if _retries > 0:
                return self._retry_request(
                    "Network", method, clean_path, _retries - 1, **kwargs
                )
            msg = f"Network transport error: {e}"
            raise CuriousApiError(msg) from e

    def close(self) -> None:
        """Close internal HTTP connection pool."""
        self._client.close()

    def create_accounts_from_df(
        self,
        df: pl.DataFrame,
        applet_id: CuriousId,
        user_type: str = "respondent",
        *,
        limit=None,
    ) -> None:
        """For each row in DataFrame, create an account in Curious."""
        _create_accounts_from_df(self, df, applet_id, user_type, limit=limit)

    def __enter__(self) -> "CuriousApiClient":
        """Enter context manager and return self."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close the client."""
        self.close()


class Applet:
    """Applet bound to a client."""

    def __init__(
        self,
        client: CuriousApiClient,
        applet_id: CuriousId,
        *,
        display_name: Optional[str] = None,
    ) -> None:
        """Initialize Applet."""
        self._id = applet_id
        self._client = client
        if display_name:
            self._name = display_name
        else:
            self._name = (
                self._client.applet_by_id(applet_id=applet_id)
                .get()
                .json()["result"]["displayName"]
            )

    def __str__(self) -> str:
        """Return string representation of Applet."""
        return f"Applet({self._name})"

    def __repr__(self) -> str:
        """Return reproducible string representation of Applet."""
        return (
            f'Applet(client={self._client}, applet_id="{self._id}", '
            f'display_name="{self._name}")'
        )


def create_toplevel_user(new_user_data: NewUserData) -> None:
    """Create a top-level user in Curious."""
    client = CuriousApiClient()
    response = client.user_create.post(json=new_user_data)
    if not httpx.codes.is_success(response.status_code):
        msg = f"Failed to create user: {response.status_code} - {response.text}"
        raise ApiStatusError(
            msg,
            request=response.request,
            response=response,
        )


def get_curious_token(
    curious_data: Record,
    curious_headers: Optional[Record] = None,
    curious_url: httpx.URL | AnyHttpUrl = CURIOUS_BASE_URL,
) -> Optional[Tokens]:
    """
    Process the response to a POST request to the specified URL.

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
    curious_url = url(curious_url)
    try:
        # Sending the POST request
        response = httpx.post(
            curious_url.join("/auth/login"),
            json=api_data(curious_data),
            headers=curious_headers,
        )
        if httpx.codes.is_success(response.status_code):
            response_data = response.json()
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


def create_accounts_from_df(
    client: CuriousApiClient,
    df: pl.DataFrame,
    applet_id: CuriousId,
    user_type: str = "respondent",
    *,
    limit=None,
) -> None:
    """For each row in DataFrame, create an account in Curious."""
    if limit:
        df = df.head(limit)
    for record in df.to_dicts():
        client.invite_user(applet_id=applet_id, user_type=user_type).post(json=record)


_create_accounts_from_df = create_accounts_from_df
