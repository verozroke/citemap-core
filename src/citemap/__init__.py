"""citemap-core: citation network analysis for the CiteMap research tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("citemap-core")
except PackageNotFoundError:  # pragma: no cover - only when run from an uninstalled tree
    __version__ = "0.0.0+local"

from citemap.dataset import DatasetError, load_dataset, save_dataset
from citemap.graph import build_citation_graph, filter_by_min_citations, filter_by_year
from citemap.models import Paper

__all__ = [
    "DatasetError",
    "Paper",
    "__version__",
    "build_citation_graph",
    "filter_by_min_citations",
    "filter_by_year",
    "load_dataset",
    "save_dataset",
]
