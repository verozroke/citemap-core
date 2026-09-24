"""citemap-core: citation network analysis for the CiteMap research tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("citemap-core")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled tree
    __version__ = "0.0.0+local"
