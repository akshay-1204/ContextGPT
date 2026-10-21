"""Webpage HTML content extractor with SSRF protections."""

from typing import Dict, Any, Tuple
import httpx
from bs4 import BeautifulSoup

from backend.app.loaders.base import BaseSourceLoader, LoaderError, validate_safe_url


class WebpageLoader(BaseSourceLoader):
    """Extracts article text and title from a webpage URL with SSRF protection."""

    def __init__(self, max_bytes: int = 5 * 1024 * 1024, timeout: float = 12.0):
        self.max_bytes = max_bytes
        self.timeout = timeout

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        url = source_reference.strip()

        # Enforce SSRF safety validation
        validate_safe_url(url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ContextGPT-Bot/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url, headers=headers)

                # Re-validate destination URL after redirects
                if str(response.url) != url:
                    validate_safe_url(str(response.url))

                if response.status_code == 401 or response.status_code == 403:
                    raise LoaderError("Access denied by target website (authentication or paywall required).")
                if response.status_code >= 400:
                    raise LoaderError(f"Failed to fetch webpage: HTTP {response.status_code} ({response.reason_phrase})")

                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise LoaderError(f"Unsupported content type: '{content_type}'. ContextGPT webpage loader requires HTML.")

                raw_html = response.text
                if len(raw_html) > self.max_bytes:
                    raw_html = raw_html[:self.max_bytes]

        except httpx.TimeoutException:
            raise LoaderError(f"Connection timed out while fetching '{url}'.")
        except httpx.RequestError as e:
            raise LoaderError(f"Network error while connecting to webpage: {str(e)}")

        # Parse HTML content
        soup = BeautifulSoup(raw_html, "html.parser")

        # Strip scripts, styles, navigations, footers, svg
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "svg", "noscript"]):
            element.extract()

        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Focus on main content if present
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup.body
        if not main_content:
            main_content = soup

        text = main_content.get_text(separator="\n", strip=True)
        # Normalize excessive newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n\n".join(lines)

        if not cleaned_text:
            raise LoaderError("Webpage does not contain any readable text.")

        metadata.update({
            "url": str(url),
            "title": title or "Webpage Document",
            "char_count": len(cleaned_text),
        })

        return cleaned_text, metadata
