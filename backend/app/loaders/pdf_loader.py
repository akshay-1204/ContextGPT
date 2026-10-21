"""PDF document loader using LangChain Community PyPDFLoader with scanned-document detection."""

import os
from typing import Dict, Any, Tuple
from langchain_community.document_loaders import PyPDFLoader as CommunityPyPDFLoader

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class PDFLoader(BaseSourceLoader):
    """Extracts text and page metadata from PDF files using LangChain Community."""

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"PDF file not found: {source_reference}")

        if os.path.getsize(source_reference) == 0:
            raise LoaderError("Uploaded PDF file is empty (0 bytes).")

        try:
            # Use LangChain Community PyPDFLoader
            loader = CommunityPyPDFLoader(source_reference)
            docs = loader.load()
        except Exception as e:
            err_str = str(e).lower()
            if "encrypted" in err_str or "password" in err_str:
                raise LoaderError("PDF is encrypted and password-protected. Please provide an unencrypted PDF.")
            raise LoaderError(f"Malformed or invalid PDF file: {str(e)}")

        if not docs:
            raise LoaderError("PDF contains no readable pages.")

        extracted_pages = []
        for doc in docs:
            page_content = doc.page_content.strip()
            page_num = doc.metadata.get("page", 0) + 1
            if page_content:
                extracted_pages.append(f"--- Page {page_num} ---\n{page_content}")

        full_text = "\n\n".join(extracted_pages).strip()

        if not full_text:
            raise LoaderError(
                "No readable text found in this PDF. It appears to be a scanned image or rasterized document. "
                "Optical Character Recognition (OCR) is not currently enabled, so please provide a text-based PDF."
            )

        metadata.update({
            "total_pages": len(docs),
            "extracted_pages_count": len(extracted_pages),
            "char_count": len(full_text),
            "loader": "langchain_community.document_loaders.PyPDFLoader",
        })

        return full_text, metadata
