"""Universal URL loader — accepts any user-provided URL, auto-detects content type, and extracts data."""

import json
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse

import httpx
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from bs4 import BeautifulSoup

from backend.app.loaders.base import BaseSourceLoader, LoaderError, validate_safe_url


class UniversalURLLoader(BaseSourceLoader, BaseLoader):
    """
    Accepts any user-provided URL and intelligently extracts content.

    Supported content types:
      - JSON APIs: Pretty-prints JSON into structured Document objects.
      - HTML pages: Extracts readable article text using BeautifulSoup.
      - Plain text / CSV / XML: Returns raw text content directly.

    Usage:
        loader = UniversalURLLoader(url="https://api.example.com/data")
        documents = loader.load()
    """

    def __init__(
        self,
        url: str = "",
        headers: Dict[str, str] = None,
        max_bytes: int = 5 * 1024 * 1024,
        timeout: float = 15.0,
    ):
        self.url = url.strip()
        self.custom_headers = headers or {}
        self.max_bytes = max_bytes
        self.timeout = timeout

    def _build_request_headers(self) -> Dict[str, str]:
        """Build final request headers merging defaults with user-provided headers."""
        request_headers = {
            "Accept": "application/json, text/html, text/plain, */*",
            "User-Agent": "ContextGPT-UniversalURLLoader/1.0",
        }
        for k, v in self.custom_headers.items():
            request_headers[k] = str(v)
        return request_headers

    def _fetch_url(self, target_url: str) -> httpx.Response:
        """Fetch URL content with SSRF validation and size limits."""
        validate_safe_url(target_url)

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(target_url, headers=self._build_request_headers())

                # Re-validate destination URL after redirects
                final_url = str(response.url)
                if final_url != target_url:
                    validate_safe_url(final_url)

                if response.status_code == 401 or response.status_code == 403:
                    raise LoaderError(
                        f"Access denied by '{target_url}' (HTTP {response.status_code}). "
                        "Authentication may be required — pass custom headers if needed."
                    )
                if response.status_code >= 400:
                    raise LoaderError(
                        f"URL returned error: HTTP {response.status_code} ({response.reason_phrase})"
                    )

                if len(response.text) > self.max_bytes:
                    raise LoaderError(
                        f"Response from '{target_url}' exceeded maximum size limit "
                        f"({self.max_bytes // (1024 * 1024)} MB)."
                    )

                return response

        except httpx.TimeoutException:
            raise LoaderError(f"Connection timed out while fetching '{target_url}'.")
        except httpx.RequestError as e:
            raise LoaderError(f"Network error fetching URL: {str(e)}")

    def _detect_content_type(self, response: httpx.Response) -> str:
        """Detect whether the response is JSON, HTML, or plain text."""
        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            return "json"

        # Try to parse as JSON even if content-type doesn't say so
        try:
            response.json()
            return "json"
        except Exception:
            pass

        if "text/html" in content_type or "application/xhtml" in content_type:
            return "html"

        return "text"

    def _extract_json(self, response: httpx.Response) -> List[Document]:
        """Extract JSON response into Document objects."""
        data = response.json()
        url_str = str(response.url)

        # If the JSON is a list of objects, create one Document per item
        if isinstance(data, list):
            documents = []
            for i, item in enumerate(data):
                content = json.dumps(item, indent=2, ensure_ascii=False)
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": url_str,
                            "content_type": "json",
                            "item_index": i,
                        },
                    )
                )
            return documents if documents else [
                Document(page_content="[]", metadata={"source": url_str, "content_type": "json"})
            ]

        # If it's a dict with a recognizable data array, split into documents
        if isinstance(data, dict):
            # Try to find the main data array inside the response
            data_key = None
            for key in ("data", "results", "items", "records", "entries", "rows"):
                if key in data and isinstance(data[key], list) and len(data[key]) > 0:
                    data_key = key
                    break

            if data_key:
                documents = []
                for i, item in enumerate(data[data_key]):
                    content = json.dumps(item, indent=2, ensure_ascii=False)
                    documents.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": url_str,
                                "content_type": "json",
                                "data_key": data_key,
                                "item_index": i,
                            },
                        )
                    )
                return documents

            # Otherwise return the entire JSON as a single document
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            return [
                Document(
                    page_content=formatted,
                    metadata={"source": url_str, "content_type": "json"},
                )
            ]

        # Scalar or other
        return [
            Document(
                page_content=str(data),
                metadata={"source": url_str, "content_type": "json"},
            )
        ]

    def _extract_html(self, response: httpx.Response) -> List[Document]:
        """Extract readable text from HTML response using BeautifulSoup."""
        soup = BeautifulSoup(response.text, "html.parser")

        # Strip non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg", "noscript"]):
            tag.extract()

        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Focus on main content
        main = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup.body
        if not main:
            main = soup

        text = main.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n\n".join(lines)

        if not cleaned_text:
            raise LoaderError(f"The page at '{response.url}' does not contain any readable text.")

        return [
            Document(
                page_content=cleaned_text,
                metadata={
                    "source": str(response.url),
                    "content_type": "html",
                    "title": title or "Webpage",
                    "char_count": len(cleaned_text),
                },
            )
        ]

    def _extract_text(self, response: httpx.Response) -> List[Document]:
        """Extract plain text content directly."""
        text = response.text.strip()
        if not text:
            raise LoaderError(f"The URL '{response.url}' returned an empty response.")

        return [
            Document(
                page_content=text,
                metadata={
                    "source": str(response.url),
                    "content_type": "text",
                    "char_count": len(text),
                },
            )
        ]

    def load(self) -> List[Document]:
        """
        Fetch any user-provided URL, auto-detect its content type,
        and return a list of LangChain Document objects.
        """
        if not self.url:
            raise LoaderError("No URL provided. Please provide a valid HTTP or HTTPS URL.")

        response = self._fetch_url(self.url)
        content_type = self._detect_content_type(response)

        if content_type == "json":
            return self._extract_json(response)
        elif content_type == "html":
            return self._extract_html(response)
        else:
            return self._extract_text(response)

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        ContextGPT pipeline integration — accepts the URL from source_reference,
        fetches content, and returns (full_text, metadata).
        """
        metadata = dict(metadata or {})
        self.url = source_reference.strip()

        # Merge any headers passed via metadata
        extra_headers = metadata.pop("headers", None)
        if isinstance(extra_headers, dict):
            self.custom_headers.update(extra_headers)

        documents = self.load()
        full_text = "\n\n".join(d.page_content for d in documents)

        # Redact sensitive headers before storing in metadata
        safe_headers = {
            k: ("***REDACTED***" if any(s in k.lower() for s in ["auth", "key", "token", "secret"]) else v)
            for k, v in self.custom_headers.items()
        }

        parsed = urlparse(self.url)
        metadata.update({
            "url": self.url,
            "domain": parsed.netloc,
            "content_type": documents[0].metadata.get("content_type", "unknown") if documents else "unknown",
            "title": documents[0].metadata.get("title") if documents else None,
            "document_count": len(documents),
            "char_count": len(full_text),
            "headers_provided": safe_headers,
            "loader": "UniversalURLLoader",
        })

        return full_text, metadata
