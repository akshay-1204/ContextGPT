"""JSON and XML file format loader."""

import json
import os
from typing import Dict, Any, Tuple
import xml.etree.ElementTree as ET

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class JsonXmlLoader(BaseSourceLoader):
    """Loads JSON and XML formatted files and converts them into structured representations."""

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"File not found: {source_reference}")

        ext = os.path.splitext(source_reference)[1].lower()

        if ext == ".json":
            try:
                with open(source_reference, "r", encoding="utf-8") as f:
                    data = json.load(f)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                metadata.update({"format": "json", "char_count": len(formatted)})
                return formatted, metadata
            except Exception as e:
                raise LoaderError(f"Failed to parse JSON file: {str(e)}")

        elif ext == ".xml":
            try:
                tree = ET.parse(source_reference)
                root = tree.getroot()

                # Flatten XML elements into readable representation
                lines = []
                for elem in root.iter():
                    text = (elem.text or "").strip()
                    if text:
                        lines.append(f"{elem.tag}: {text}")

                formatted = "\n".join(lines).strip()
                if not formatted:
                    raise LoaderError("XML file does not contain readable text elements.")

                metadata.update({"format": "xml", "char_count": len(formatted)})
                return formatted, metadata
            except LoaderError:
                raise
            except Exception as e:
                raise LoaderError(f"Failed to parse XML file: {str(e)}")
        else:
            raise LoaderError(f"Unsupported file format '{ext}'. Must be .json or .xml.")
