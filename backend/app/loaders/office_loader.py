"""Office document loader for Word (.docx) and Excel (.xlsx) files."""

import os
from typing import Dict, Any, Tuple
from backend.app.loaders.base import BaseSourceLoader, LoaderError


class OfficeLoader(BaseSourceLoader):
    """Extracts text from Word documents and Excel workbooks."""

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"Office document not found: {source_reference}")

        ext = os.path.splitext(source_reference)[1].lower()

        if ext == ".docx":
            try:
                import docx
                doc = docx.Document(source_reference)
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                tables_text = []
                for table in doc.tables:
                    for row in table.rows:
                        row_vals = [cell.text.strip() for cell in row.cells]
                        tables_text.append(" | ".join(row_vals))

                full_text = "\n\n".join(paragraphs + tables_text).strip()
                if not full_text:
                    raise LoaderError("Word document contains no readable text.")

                metadata.update({
                    "doc_type": "docx",
                    "paragraphs_count": len(paragraphs),
                    "char_count": len(full_text),
                })
                return full_text, metadata
            except LoaderError:
                raise
            except Exception as e:
                raise LoaderError(f"Error reading Word (.docx) document: {str(e)}")

        elif ext in (".xlsx", ".xls"):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(source_reference, data_only=True)
                sheets_text = []
                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    sheets_text.append(f"### Sheet: {sheet_name}")
                    for row in sheet.iter_rows(values_only=True):
                        # Filter out empty rows
                        if any(val is not None for val in row):
                            cleaned_vals = [str(val if val is not None else "") for val in row]
                            sheets_text.append("| " + " | ".join(cleaned_vals) + " |")

                full_text = "\n".join(sheets_text).strip()
                if not full_text:
                    raise LoaderError("Excel workbook contains no readable data.")

                metadata.update({
                    "doc_type": "xlsx",
                    "sheets_count": len(wb.sheetnames),
                    "char_count": len(full_text),
                })
                return full_text, metadata
            except LoaderError:
                raise
            except Exception as e:
                raise LoaderError(f"Error reading Excel workbook: {str(e)}")
        else:
            raise LoaderError(f"Unsupported office extension '{ext}'. Only .docx and .xlsx are supported.")
