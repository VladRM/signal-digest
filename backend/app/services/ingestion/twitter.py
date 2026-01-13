"""X/Twitter ingestion via twitterapi.io."""
import hashlib
from datetime import datetime
from typing import List, Dict, Any
import requests
from dateutil import parser as date_parser

from app.models.content_item import ContentItem
from app.services.ingestion.base import BaseIngester
from app.services.ingestion.constants import MAX_TWITTER_ITEMS
from app.config import settings


class TwitterIngester(BaseIngester):
    """Ingest tweets from X/Twitter users via twitterapi.io."""

    def __init__(self, db, endpoint, max_items: int | None = None):
        super().__init__(db, endpoint)
        self.max_items = self.resolve_max_items(max_items, MAX_TWITTER_ITEMS)  # Per-user limit
        self.api_key = settings.twitter_api_key

    def resolve_max_items(self, override: int | None, default: int) -> int:
        """Resolve max items for this user."""
        if override is None:
            return default
        try:
            value = int(override)
        except (TypeError, ValueError):
            return default
        return max(0, value)

    def get_handle(self, identifier: str) -> str:
        """Extract handle from identifier (remove @ if present)."""
        return identifier.lstrip("@")

    def _extract_tweets(self, data: Any) -> List[Dict[str, Any]]:
        """Extract tweet list from varying API response shapes."""
        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for key in ("tweets", "data", "items", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    for nested_key in ("tweets", "data", "items", "results"):
                        nested_value = value.get(nested_key)
                        if isinstance(nested_value, list):
                            return nested_value

        return []

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch tweets from user timeline via twitterapi.io."""
        if not self.api_key:
            raise Exception("Twitter API key not configured")

        handle = self.get_handle(self.endpoint.target)

        # twitterapi.io endpoint (docs: /twitter/user/last_tweets)
        url = "https://api.twitterapi.io/twitter/user/last_tweets"
        headers = {"X-API-Key": self.api_key}
        params = {"userName": handle}

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        tweets = self._extract_tweets(data)

        # Return up to max_items
        return tweets[: self.max_items]

    def normalize(self, raw_item: Dict[str, Any]) -> ContentItem:
        """Convert tweet to ContentItem."""
        # Different APIs may have different field names
        tweet_id = raw_item.get("id_str") or raw_item.get("id")
        text = raw_item.get("full_text") or raw_item.get("text", "")
        author = raw_item.get("user", {}).get("screen_name") or self.get_handle(
            self.endpoint.target
        )

        # Create URL
        url = f"https://twitter.com/{author}/status/{tweet_id}"

        # Title is first 100 chars
        title = text[:100] + ("..." if len(text) > 100 else "")

        # Get published date
        published_at = None
        created_at = raw_item.get("created_at")
        if created_at:
            try:
                # Twitter date format: "Wed Oct 10 20:19:24 +0000 2018"
                published_at = date_parser.parse(created_at)
                # Remove timezone info for database storage
                if published_at and published_at.tzinfo is not None:
                    published_at = published_at.replace(tzinfo=None)
            except:
                pass

        # Create hash
        hash_str = f"{tweet_id}:{text[:100]}".encode("utf-8")
        content_hash = hashlib.sha256(hash_str).hexdigest()

        return ContentItem(
            endpoint_id=self.endpoint.id,
            connector_type=self.endpoint.connector_type,
            external_id=str(tweet_id),
            url=url,
            title=title,
            author=f"@{author}",
            published_at=published_at,
            fetched_at=datetime.utcnow(),
            raw_text=text,
            raw_json=raw_item,
            hash=content_hash,
        )
