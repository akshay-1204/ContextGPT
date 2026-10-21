"""Text file loader using LangChain Community TextLoader with multi-encoding fallback."""

import os
from typing import Dict, Any, Tuple
from langchain_community.document_loaders import TextLoader as CommunityTextLoader

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class TextLoader(BaseSourceLoader):
    """Extracts text from plain text and markdown files using LangChain Community with encoding fallbacks."""

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"File not found: {source_reference}")

        file_size = os.path.getsize(source_reference)
        if file_size == 0:
            raise LoaderError("File is empty (0 bytes).")

        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        content_clean = None
        used_encoding = None

        for enc in encodings:
            try:
                # Use LangChain Community TextLoader
                loader = CommunityTextLoader(source_reference, encoding=enc)
                docs = loader.load()
                if docs:
                    text = docs[0].page_content.strip()
                    if text:
                        content_clean = text
                        used_encoding = enc
                        break
            except Exception:
                continue

        if content_clean is None:
            # Fallback direct read
            try:
                with open(source_reference, "rb") as f:
                    raw = f.read()
                for enc in encodings:
                    try:
                        content_clean = raw.decode(enc).strip()
                        used_encoding = enc
                        if content_clean:
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        if not content_clean:
            raise LoaderError("Failed to decode text file or file consists entirely of whitespace.")

        metadata.update({
            "encoding": used_encoding,
            "char_count": len(content_clean),
            "file_size_bytes": file_size,
            "loader": "langchain_community.document_loaders.TextLoader",
        })

        return content_clean, metadata
