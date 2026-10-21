"""CSV file loader using LangChain Community CSVLoader."""

import os
from typing import Dict, Any, Tuple
from langchain_community.document_loaders import CSVLoader as CommunityCSVLoader

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class CSVLoader(BaseSourceLoader):
    """Parses CSV files into readable documents using LangChain Community."""

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"CSV file not found: {source_reference}")

        if os.path.getsize(source_reference) == 0:
            raise LoaderError("CSV file is empty (0 bytes).")

        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        docs = []
        used_encoding = None

        for enc in encodings:
            try:
                # Use LangChain Community CSVLoader
                loader = CommunityCSVLoader(
                    file_path=source_reference,
                    encoding=enc,
                )
                docs = loader.load()
                if docs:
                    used_encoding = enc
                    break
            except Exception:
                continue

        if not docs:
            raise LoaderError("Failed to parse CSV file content.")

        # Combine loaded CSV row documents
        row_texts = [d.page_content for d in docs]
        full_text = "\n\n".join(row_texts)

        metadata.update({
            "encoding": used_encoding,
            "row_count": len(docs),
            "char_count": len(full_text),
            "loader": "langchain_community.document_loaders.CSVLoader",
        })

        return full_text, metadata
