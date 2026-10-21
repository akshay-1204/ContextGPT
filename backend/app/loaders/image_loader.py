"""Image loader supporting vision-capable description via OpenAI."""

import base64
import os
from typing import Dict, Any, Tuple
from PIL import Image

from backend.app.core.config import settings
from backend.app.loaders.base import BaseSourceLoader, LoaderError


class ImageLoader(BaseSourceLoader):
    """Processes image files (PNG, JPEG, WEBP) using OpenAI Vision API when configured."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        if not os.path.exists(source_reference):
            raise LoaderError(f"Image file not found: {source_reference}")

        ext = os.path.splitext(source_reference)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise LoaderError(
                f"Unsupported image format '{ext}'. Supported formats: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}."
            )

        try:
            with Image.open(source_reference) as img:
                width, height = img.size
                format_name = img.format
        except Exception as e:
            raise LoaderError(f"Corrupt or invalid image file: {str(e)}")

        # Check if OpenAI API key is configured for vision extraction
        if not settings.OPENAI_API_KEY:
            raise LoaderError(
                "Image source understanding requires an active OpenAI API key with vision capabilities (e.g., gpt-4o). "
                "Text embeddings alone cannot read raw pixel data. Please configure OPENAI_API_KEY in .env."
            )

        # Call OpenAI Vision API
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL or None,
            )


            with open(source_reference, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

            mime_type = f"image/{ext.replace('.', '')}"
            if ext == ".jpg":
                mime_type = "image/jpeg"

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze this image comprehensively for retrieval and summarization. "
                                    "Extract all readable text, charts, diagrams, tables, and describe the key visual elements."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded_string}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1500,
            )
            extracted_text = response.choices[0].message.content or ""
        except Exception as e:
            raise LoaderError(f"OpenAI Vision extraction failed: {str(e)}")

        metadata.update({
            "image_width": width,
            "image_height": height,
            "image_format": format_name,
            "char_count": len(extracted_text),
        })

        return extracted_text, metadata
