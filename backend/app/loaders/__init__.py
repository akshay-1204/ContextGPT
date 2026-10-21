"""Loaders package for ContextGPT."""

from backend.app.loaders.base import BaseSourceLoader, LoaderError, validate_safe_url
from backend.app.loaders.loader_registry import LoaderRegistry, get_loader, list_supported_types
from backend.app.loaders.stock_loader import StockAPILoader
from backend.app.loaders.url_loader import UniversalURLLoader

__all__ = [
    "BaseSourceLoader",
    "LoaderError",
    "validate_safe_url",
    "LoaderRegistry",
    "StockAPILoader",
    "UniversalURLLoader",
    "get_loader",
    "list_supported_types",
]

