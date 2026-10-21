"""YouTube video transcript extractor using LangChain Community YoutubeLoader."""

import re
from typing import Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs
from langchain_community.document_loaders import YoutubeLoader as CommunityYoutubeLoader

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class YouTubeLoader(BaseSourceLoader):
    """Fetches official closed captions / transcripts using LangChain Community."""

    def _extract_video_id(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.hostname in ("www.youtube.com", "youtube.com"):
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
        elif parsed.hostname == "youtu.be":
            return parsed.path.lstrip("/")
        raise LoaderError("Invalid YouTube URL. Please provide a standard watch URL or youtu.be link.")

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        clean_url = source_reference.strip()
        video_id = self._extract_video_id(clean_url)

        try:
            # Use LangChain Community YoutubeLoader
            loader = CommunityYoutubeLoader.from_youtube_url(
                clean_url,
                add_video_info=False,
            )
            docs = loader.load()
            if not docs:
                raise LoaderError("Transcript for this YouTube video is empty or unavailable.")

            full_transcript = "\n\n".join(d.page_content for d in docs).strip()

            metadata.update({
                "video_id": video_id,
                "char_count": len(full_transcript),
                "loader": "langchain_community.document_loaders.YoutubeLoader",
            })
            return full_transcript, metadata
        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(f"Could not retrieve YouTube transcript via LangChain Community: {str(e)}")
