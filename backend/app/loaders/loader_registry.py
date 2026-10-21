"""Simple registry of supported document and source loaders without complex @classmethod decorators."""

from backend.app.loaders.base import BaseSourceLoader, LoaderError
from backend.app.loaders.text_loader import TextLoader
from backend.app.loaders.pdf_loader import PDFLoader
from backend.app.loaders.webpage_loader import WebpageLoader
from backend.app.loaders.api_loader import APILoader
from backend.app.loaders.database_loader import DatabaseLoader
from backend.app.loaders.image_loader import ImageLoader
from backend.app.loaders.csv_loader import CSVLoader
from backend.app.loaders.office_loader import OfficeLoader
from backend.app.loaders.json_xml_loader import JsonXmlLoader
from backend.app.loaders.youtube_loader import YouTubeLoader
from backend.app.loaders.stock_loader import StockAPILoader
from backend.app.loaders.url_loader import UniversalURLLoader

# Simple dictionary mapping source types to loader classes
LOADERS = {
    "txt": TextLoader,
    "text": TextLoader,
    "md": TextLoader,
    "pdf": PDFLoader,
    "webpage": WebpageLoader,
    "api": APILoader,
    "url": UniversalURLLoader,
    "stock": StockAPILoader,
    "database": DatabaseLoader,
    "image": ImageLoader,
    "csv": CSVLoader,
    "docx": OfficeLoader,
    "xlsx": OfficeLoader,
    "office": OfficeLoader,
    "json": JsonXmlLoader,
    "xml": JsonXmlLoader,
    "json_xml": JsonXmlLoader,
    "youtube": YouTubeLoader,
}


def get_loader(source_type: str):
    """Simple function to get a loader instance for a given source type."""
    normalized_type = source_type.lower().strip()
    loader_cls = LOADERS.get(normalized_type)
    if not loader_cls:
        supported = ", ".join(sorted(LOADERS.keys()))
        raise LoaderError(f"Unsupported source type: '{source_type}'. Supported types: {supported}")
    return loader_cls()


def list_supported_types():
    """Simple function listing all supported source types."""
    return sorted(list(LOADERS.keys()))


# Alias class so any existing caller can still use LoaderRegistry.get_loader(...)
class LoaderRegistry:
    get_loader = staticmethod(get_loader)
    list_supported_types = staticmethod(list_supported_types)
