"""YouTube video transcript extractor compatible with all youtube_transcript_api versions."""

import re
from typing import Dict, Any, Tuple, List
from urllib.parse import urlparse, parse_qs
from langchain_core.documents import Document

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class YouTubeLoader(BaseSourceLoader):
    """Fetches official closed captions / transcripts for YouTube videos."""

    def __init__(self, url: str = None):
        self.url = url

    def _extract_video_id(self, url: str) -> str:
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        if parsed.hostname in ("www.youtube.com", "youtube.com"):
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0]
        elif parsed.hostname in ("youtu.be", "www.youtu.be"):
            path = parsed.path.strip("/")
            if path:
                return path.split("/")[0]
        if "embed/" in parsed.path:
            return parsed.path.split("embed/")[1].split("/")[0].split("?")[0]

        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", clean_url)
        if match:
            return match.group(1)

        raise LoaderError(
            "Invalid YouTube URL. Please provide a standard watch URL (e.g. https://www.youtube.com/watch?v=...) or youtu.be link."
        )

    def _fetch_transcript_text(self, video_id: str) -> str:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError:
            raise LoaderError(
                "YouTube transcript extraction requires 'youtube-transcript-api'. "
                "Please run: pip install youtube-transcript-api"
            )

        # 1. Try modern youtube-transcript-api v1.0+ instance API
        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            try:
                transcript = transcript_list.find_transcript(["en", "en-US", "en-GB"])
            except Exception:
                # Fallback to whatever first available transcript exists (e.g. auto-generated or other language)
                transcript = next(iter(transcript_list))

            fetched = transcript.fetch()
            pieces = []
            if hasattr(fetched, "snippets"):
                pieces = [s.text.strip() for s in fetched.snippets if getattr(s, "text", None)]
            elif isinstance(fetched, list):
                for item in fetched:
                    if hasattr(item, "text"):
                        pieces.append(item.text.strip())
                    elif isinstance(item, dict) and "text" in item:
                        pieces.append(item["text"].strip())

            full_text = " ".join(pieces).strip()
            if full_text:
                return full_text
        except (AttributeError, TypeError):
            # Not v1.x or instance method failed, fall through to v0.6.x methods
            pass
        except Exception as e:
            err_msg = str(e)
            if "TranscriptsDisabled" in err_msg or "disabled" in err_msg.lower():
                raise LoaderError("Transcripts are disabled by the owner for this YouTube video.")
            if "NoTranscriptFound" in err_msg or "not found" in err_msg.lower():
                raise LoaderError("No transcript or subtitles could be found for this YouTube video.")
            if "VideoUnavailable" in err_msg or "unavailable" in err_msg.lower():
                raise LoaderError("This YouTube video is unavailable or private.")
            pass

        # 2. Try legacy youtube-transcript-api (<= v0.6.x) static API
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                items = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
                pieces = [i["text"].strip() for i in items if i.get("text")]
                full_text = " ".join(pieces).strip()
                if full_text:
                    return full_text
        except Exception as e:
            err_msg = str(e)
            if "TranscriptsDisabled" in err_msg or "disabled" in err_msg.lower():
                raise LoaderError("Transcripts are disabled by the owner for this YouTube video.")
            if "NoTranscriptFound" in err_msg or "not found" in err_msg.lower():
                raise LoaderError("No English transcript could be found for this YouTube video.")
            raise LoaderError(f"Could not retrieve YouTube transcript: {err_msg}")

        raise LoaderError("Transcript for this YouTube video is empty or unavailable.")

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        clean_url = source_reference.strip()
        video_id = self._extract_video_id(clean_url)

        full_transcript = self._fetch_transcript_text(video_id)

        metadata.update({
            "video_id": video_id,
            "char_count": len(full_transcript),
            "word_count": len(full_transcript.split()),
            "source": "YouTube Transcript",
        })
        return full_transcript, metadata

    def load(self) -> List[Document]:
        """LangChain standard load method returning Document objects."""
        if not self.url:
            return []
        text, meta = self.extract(self.url)
        return [Document(page_content=text, metadata=meta)]
