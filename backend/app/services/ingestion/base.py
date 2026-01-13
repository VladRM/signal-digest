"""Base ingestion class."""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.content_item import ContentItem
from app.models.endpoint import Endpoint


class BaseIngester(ABC):
    """Base class for all content ingesters."""

    def __init__(self, db: Session, endpoint: Endpoint):
        self.db = db
        self.endpoint = endpoint
        self.fetch_window_hours = 48
        self.stats = {
            "items_fetched": 0,
            "items_new": 0,
            "items_skipped": 0,
            "errors": [],
        }

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch raw items from the endpoint."""
        pass

    @abstractmethod
    def normalize(self, raw_item: Dict[str, Any]) -> ContentItem:
        """Convert raw item to ContentItem model."""
        pass

    def is_within_window(self, published_at: datetime) -> bool:
        """Check if item is within fetch window."""
        if not published_at:
            return True

        # Remove timezone info for comparison
        if published_at.tzinfo is not None:
            published_at = published_at.replace(tzinfo=None)

        cutoff = datetime.utcnow() - timedelta(hours=self.fetch_window_hours)
        return published_at >= cutoff

    def deduplicate(self, item: ContentItem) -> bool:
        """Check if item already exists in database."""
        # Check by external_id
        if item.external_id:
            existing = (
                self.db.query(ContentItem)
                .filter(
                    ContentItem.endpoint_id == self.endpoint.id,
                    ContentItem.external_id == item.external_id,
                )
                .first()
            )
            if existing:
                return True

        # Check by URL
        if item.url:
            existing = self.db.query(ContentItem).filter(ContentItem.url == item.url).first()
            if existing:
                return True

        # Check by hash (if provided)
        if item.hash:
            cutoff = datetime.utcnow() - timedelta(hours=self.fetch_window_hours)
            existing = (
                self.db.query(ContentItem)
                .filter(
                    ContentItem.hash == item.hash,
                    ContentItem.fetched_at >= cutoff,
                )
                .first()
            )
            if existing:
                return True

        return False

    async def ingest(self) -> Dict[str, Any]:
        """Run the full ingestion process."""
        try:
            # Fetch raw items
            raw_items = await self.fetch()
            self.stats["items_fetched"] = len(raw_items)

            # Process each item
            for raw_item in raw_items:
                try:
                    # Normalize to ContentItem
                    item = self.normalize(raw_item)

                    # Check if within time window
                    if not self.is_within_window(item.published_at):
                        self.stats["items_skipped"] += 1
                        continue

                    # Check for duplicates
                    if self.deduplicate(item):
                        self.stats["items_skipped"] += 1
                        continue

                    # Save to database
                    self.db.add(item)
                    self.stats["items_new"] += 1

                except Exception as e:
                    error_msg = f"Error processing item: {str(e)}"
                    self.stats["errors"].append(error_msg)
                    print(f"[{self.endpoint.connector_type}] {error_msg}")

            # Commit all new items
            self.db.commit()

        except Exception as e:
            error_msg = f"Error fetching from endpoint: {str(e)}"
            self.stats["errors"].append(error_msg)
            print(f"[{self.endpoint.connector_type}] {error_msg}")
            self.db.rollback()

        return self.stats
