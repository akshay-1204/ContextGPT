"""API & JSON source loader with SSRF protection and secret redaction."""

import json
from typing import Dict, Any, Tuple
import httpx

from backend.app.loaders.base import BaseSourceLoader, LoaderError, validate_safe_url


class APILoader(BaseSourceLoader):
    """Extracts and formats data from external REST APIs returning JSON."""

    def __init__(self, max_bytes: int = 2 * 1024 * 1024, timeout: float = 10.0):
        self.max_bytes = max_bytes
        self.timeout = timeout

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        endpoint_url = source_reference.strip()

        # Validate URL against SSRF
        validate_safe_url(endpoint_url)

        custom_headers = metadata.get("headers") or {}
        # Ensure headers is a dictionary
        if not isinstance(custom_headers, dict):
            custom_headers = {}

        request_headers = {
            "Accept": "application/json, text/plain",
            "User-Agent": "ContextGPT-APILoader/1.0",
        }
        for k, v in custom_headers.items():
            request_headers[k] = str(v)

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(endpoint_url, headers=request_headers)

                # Re-validate destination URL after redirects
                if str(response.url) != endpoint_url:
                    validate_safe_url(str(response.url))

                if response.status_code >= 400:
                    raise LoaderError(f"API returned error: HTTP {response.status_code} ({response.reason_phrase})")

                raw_text = response.text
                if len(raw_text) > self.max_bytes:
                    raise LoaderError(f"API response exceeded maximum size limit ({self.max_bytes // 1024} KB).")

                try:
                    data = response.json()
                    formatted_text = json.dumps(data, indent=2, ensure_ascii=False)
                except Exception:
                    # Fallback to plain text if not strictly JSON
                    formatted_text = raw_text.strip()

        except httpx.TimeoutException:
            raise LoaderError(f"Connection timed out while querying API '{endpoint_url}'.")
        except httpx.RequestError as e:
            raise LoaderError(f"Network error querying API: {str(e)}")

        if not formatted_text:
            raise LoaderError("API returned an empty response body.")

        # Redact headers for safe storage
        safe_headers = {k: ("***REDACTED***" if any(s in k.lower() for s in ["auth", "key", "token", "secret"]) else v)
                        for k, v in custom_headers.items()}

        metadata.update({
            "endpoint_url": endpoint_url,
            "headers_provided": safe_headers,
            "char_count": len(formatted_text),
        })

        return formatted_text, metadata
