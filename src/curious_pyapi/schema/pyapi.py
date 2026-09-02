"""Curious-PyAPI schemas."""

from typing import Any, Optional, overload

from httpx import Response, URL
from pydantic import AnyHttpUrl, BaseModel, EmailStr, SecretStr

from ..utils.logging import get_logger
from .curious import CuriousId

logger = get_logger(__name__)


class CuriousAuth(BaseModel):
    """Required data for authentication and decryption."""

    curious_email: EmailStr
    curious_password: SecretStr
    applet_id: Optional[CuriousId] = None
    applet_password: Optional[SecretStr] = None

    @property
    def login_credentials(self) -> dict[str, str | SecretStr]:
        """Return email and password as dictionary for API request."""
        return {"email": self.curious_email, "password": self.curious_password}


class ApiClient:
    """Generic API client."""

    base_url: URL

    def request(self, method: str, path: str | URL, **kwargs: Any) -> Response:
        """Centralized transport gateway with error mapping and auth checking."""
        return NotImplemented()


class BoundEndpoint:
    """Class to bind endpoint to an instance."""

    def __init__(self, client: ApiClient, path: str) -> None:
        """Initialize bound endpoint."""
        self._client = client
        self.path = path

    def __call__(self, **kwargs: Any) -> "BoundEndpoint":
        """Allow calling endpoint as a function to format path parameters."""
        return BoundEndpoint(self._client, self.path.format(**kwargs))

    @property
    def url(self) -> URL:
        """Return base URL."""
        return self._client.base_url.join(URL(self.path.lstrip("/")))

    def get(self, **kwargs: Any) -> Response:
        """Return GET response."""
        return self._client.request("GET", self.path, **kwargs)

    def post(self, **kwargs: Any) -> Response:
        """Return POST response."""
        return self._client.request("POST", self.path, **kwargs)


class EndpointPath:
    """Endpoint path or full URL."""

    def __init__(self, path: str) -> None:
        """Initialize endpoint path."""
        self.path = path

    @overload
    def __get__(self, instance: None, owner: Any) -> str: ...

    @overload
    def __get__(self, instance: ApiClient, owner: Any) -> BoundEndpoint: ...

    def __get__(self, instance: Optional[ApiClient], owner: Any) -> str | BoundEndpoint:
        """Return path or bound endpoint."""
        if instance is None:
            return self.path
        return BoundEndpoint(instance, self.path)


class Endpoint:
    """API endpoint."""

    auth = EndpointPath("/auth/login")

    def __init__(self, base_url: URL | AnyHttpUrl) -> None:
        """Initialize API endpoint."""
        self._base_url = url(base_url)

    @property
    def base_url(self) -> URL:
        """Return base URL for API endpoint."""
        return self._base_url

    @base_url.setter
    def base_url(self, value: URL) -> None:
        """Update base URL for API endpoint."""
        self._base_url = value


class Tokens(BaseModel):
    """Curious tokens."""

    access: SecretStr
    refresh: SecretStr


def url(url: URL | AnyHttpUrl) -> URL:
    """Typecheck and cast to `httpx.URL`."""
    if isinstance(url, str):
        url = URL(url)
    assert isinstance(url, URL)
    return url
