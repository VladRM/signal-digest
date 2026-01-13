"""YouTube channel ingestion."""
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any
import requests
from dateutil import parser as date_parser

from app.config import settings
from app.models.content_item import ContentItem
from app.services.ingestion.base import BaseIngester
from app.services.ingestion.constants import MAX_YOUTUBE_ITEMS

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeIngester(BaseIngester):
    """Ingest videos from YouTube channels via Data API."""

    def __init__(self, db, endpoint, max_items: int | None = None):
        super().__init__(db, endpoint)
        self.max_items = self.resolve_max_items(max_items, MAX_YOUTUBE_ITEMS)  # Per-channel limit
        self.api_key = settings.youtube_data_api_key

    def resolve_max_items(self, override: int | None, default: int) -> int:
        """Resolve max items for this channel."""
        if override is None:
            return default
        try:
            value = int(override)
        except (TypeError, ValueError):
            return default
        return max(0, value)

    def _api_get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call the YouTube Data API and return parsed JSON."""
        if not self.api_key:
            raise Exception("YouTube Data API key not configured")

        url = f"{YOUTUBE_API_BASE_URL}/{endpoint.lstrip('/')}"
        query = {"key": self.api_key, **params}
        response = requests.get(url, params=query, timeout=30)
        if not response.ok:
            error_message = response.text
            try:
                error_json = response.json()
                error_message = error_json.get("error", {}).get("message") or error_message
            except ValueError:
                pass
            raise Exception(f"YouTube API error ({response.status_code}): {error_message}")
        return response.json()

    def _build_channel_queries(self, identifier: str) -> List[Dict[str, str]]:
        """Build ordered channel lookup queries from identifier."""
        ident = (identifier or "").strip()
        if not ident:
            return []

        if ident.startswith("UC"):
            return [{"id": ident}]

        match = re.search(r"youtube\.com/channel/([^/?]+)", ident)
        if match:
            return [{"id": match.group(1)}]

        match = re.search(r"youtube\.com/@([^/?]+)", ident)
        if match:
            return [{"forHandle": match.group(1)}]

        match = re.search(r"youtube\.com/user/([^/?]+)", ident)
        if match:
            return [{"forUsername": match.group(1)}]

        match = re.search(r"youtube\.com/c/([^/?]+)", ident)
        if match:
            slug = match.group(1)
            return [{"forHandle": slug}, {"forUsername": slug}]

        if ident.startswith("@"):
            return [{"forHandle": ident.lstrip("@")}]

        cleaned = ident.lstrip("@")
        return [{"forHandle": cleaned}, {"forUsername": cleaned}]

    def _resolve_channel(self, identifier: str) -> Dict[str, Any]:
        """Resolve a channel using ID, @handle, or legacy username."""
        queries = self._build_channel_queries(identifier)
        if not queries:
            raise Exception("YouTube channel identifier is missing")

        for query in queries:
            data = self._api_get(
                "channels",
                {"part": "contentDetails,snippet", "maxResults": 1, **query},
            )
            items = data.get("items", [])
            if items:
                return items[0]

        raise Exception(
            "YouTube channel not found. Provide a channel ID (UC...) or @handle."
        )

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch latest videos from a YouTube channel."""
        channel = self._resolve_channel(self.endpoint.target)
        uploads_playlist_id = (
            channel.get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist_id:
            raise Exception("YouTube channel missing uploads playlist")

        data = self._api_get(
            "playlistItems",
            {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": self.max_items,
            },
        )
        items = data.get("items", [])
        return items[: self.max_items]

    def normalize(self, raw_item: Dict[str, Any]) -> ContentItem:
        """Convert YouTube API playlist item to ContentItem."""
        snippet = raw_item.get("snippet") or {}
        content_details = raw_item.get("contentDetails") or {}
        resource = snippet.get("resourceId") or {}

        video_id = content_details.get("videoId") or resource.get("videoId")
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

        title = snippet.get("title", "Untitled")
        author = snippet.get("channelTitle", "")

        published_at = None
        published_raw = content_details.get("videoPublishedAt") or snippet.get("publishedAt")
        if published_raw:
            try:
                published_at = date_parser.parse(published_raw)
                if published_at and published_at.tzinfo is not None:
                    published_at = published_at.replace(tzinfo=None)
            except:
                pass

        raw_text = snippet.get("description")

        hash_str = f"{video_id}:{title}".encode("utf-8")
        content_hash = hashlib.sha256(hash_str).hexdigest()

        return ContentItem(
            endpoint_id=self.endpoint.id,
            connector_type=self.endpoint.connector_type,
            external_id=str(video_id) if video_id else None,
            url=url,
            title=title,
            author=author,
            published_at=published_at,
            fetched_at=datetime.utcnow(),
            raw_text=raw_text,
            raw_json=raw_item,
            hash=content_hash,
        )
