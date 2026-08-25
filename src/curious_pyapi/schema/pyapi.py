"""Curious-PyAPI schemas."""

from pydantic import BaseModel, EmailStr, SecretStr

from .curious import CuriousId
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
