"""Simple, beginner-friendly base loader using standard LangChain BaseLoader and Document."""

from typing import Dict, Any, Tuple, List
import ipaddress
import socket
from urllib.parse import urlparse

from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document


class LoaderError(Exception):
    """Custom exception raised when source extraction fails."""
    pass


def validate_safe_url(url: str) -> None:
    """
    Validate that a URL does not target localhost, private networks, or cloud metadata endpoints.
    Protects against Server-Side Request Forgery (SSRF).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise LoaderError(f"Unsupported URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise LoaderError("Invalid URL: hostname is missing.")

    # Block well-known unsafe names
    blocked_hosts = {"localhost", "metadata.google.internal", "instance-data"}
    if hostname.lower() in blocked_hosts:
        raise LoaderError(f"Access to host '{hostname}' is blocked for security reasons.")

    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        for addr_info in ip_addresses:
            ip_str = addr_info[4][0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_str.startswith("169.254.")
            ):
                raise LoaderError(f"Access to private/internal network destination ({ip_str}) is blocked.")
    except socket.gaierror:
        raise LoaderError(f"Could not resolve hostname '{hostname}'.")


class BaseSourceLoader(BaseLoader):
    """
    Simple, easy-to-understand base loader inheriting from LangChain's BaseLoader.
    No complicated @abstractmethod or metaclasses!
    """

    def load(self) -> List[Document]:
        """Standard LangChain load method returning Document objects."""
        return []

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Convenience method to extract plain text and metadata.
        Subclasses override this directly.
        """
        return "", dict(metadata or {})
