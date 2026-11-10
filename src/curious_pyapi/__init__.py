"""Python API for Curious."""

from importlib.metadata import version, PackageNotFoundError

from .api.curious import get_curious_token

try:
    __version__ = version("curious-pyapi")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["get_curious_token", "__version__"]
