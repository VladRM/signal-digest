"""RSS feed ingestion."""
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import feedparser
import requests
from dateutil import parser as date_parser

from app.models.content_item import ContentItem
from app.services.ingestion.base import BaseIngester
from app.services.ingestion.constants import MAX_RSS_ITEMS


class RSSIngester(BaseIngester):
    """Ingest content from RSS/Atom feeds."""

    def __init__(self, db, endpoint, max_items: int | None = None):
        super().__init__(db, endpoint)
        self.max_items = self.resolve_max_items(max_items, MAX_RSS_ITEMS)  # Per-endpoint limit

    def resolve_max_items(self, override: int | None, default: int) -> int:
        """Resolve max items for this endpoint."""
        if override is None:
            return default
        try:
            value = int(override)
        except (TypeError, ValueError):
            return default
        return max(0, value)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch entries from RSS feed."""
        feed = feedparser.parse(self.endpoint.target)

        if feed.bozo and hasattr(feed, "bozo_exception") and not feed.entries:
            headers = {
                "User-Agent": "SignalDigest/1.0 (+https://github.com/)",
                "Accept": "application/rss+xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8",
            }
            try:
                response = requests.get(
                    self.endpoint.target, headers=headers, timeout=30
                )
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            except requests.RequestException as exc:
                raise Exception(f"Feed fetch error: {exc}")

        if feed.bozo and hasattr(feed, "bozo_exception") and not feed.entries:
            raise Exception(f"Feed parse error: {feed.bozo_exception}")

        # Return up to max_items entries
        return feed.entries[: self.max_items]

    def normalize(self, raw_item: Dict[str, Any]) -> ContentItem:
        """Convert RSS entry to ContentItem."""
        # Extract fields
        title = raw_item.get("title", "Untitled")
        url = raw_item.get("link", "")
        external_id = raw_item.get("id") or raw_item.get("guid") or url
        author = raw_item.get("author")

        # Get published date
        published_at = None
        for date_field in ["published", "updated", "created"]:
            if date_field in raw_item:
                try:
                    published_at = date_parser.parse(raw_item[date_field])
                    # Remove timezone info for database storage
                    if published_at and published_at.tzinfo is not None:
                        published_at = published_at.replace(tzinfo=None)
                    break
                except:
                    pass

        # Get content text
        raw_text = None
        if "content" in raw_item and raw_item.content:
            raw_text = raw_item.content[0].get("value", "")
        elif "summary" in raw_item:
            raw_text = raw_item.summary
        elif "description" in raw_item:
            raw_text = raw_item.description

        # Create hash for deduplication
        hash_str = f"{title}:{url}".encode("utf-8")
        content_hash = hashlib.sha256(hash_str).hexdigest()

        return ContentItem(
            endpoint_id=self.endpoint.id,
            connector_type=self.endpoint.connector_type,
            external_id=external_id[:512] if external_id else None,
            url=url,
            title=title,
            author=author,
            published_at=published_at,
            fetched_at=datetime.utcnow(),
            raw_text=raw_text,
            raw_json=dict(raw_item),
            hash=content_hash,
        )
