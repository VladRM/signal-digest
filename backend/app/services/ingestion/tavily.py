"""Tavily topic search ingestion."""
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from urllib.parse import urlparse

import requests
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.config import settings
from app.models.connector_query import ConnectorQuery
from app.models.content_item import ContentItem
from app.models.endpoint import ConnectorType
from app.models.topic import Topic
from app.models.topic_assignment import TopicAssignment
from app.schemas.run import TavilyRunOptions
from app.services.ingestion.constants import TAVILY_RESULTS_PER_TOPIC

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyTopicIngester:
    """Search Tavily for each enabled topic and store results."""

    def __init__(self, db: Session, options: TavilyRunOptions | None = None):
        self.db = db
        self.fetch_window_hours = 48
        self.options = options or TavilyRunOptions()
        self.fetch_window_hours = self.resolve_fetch_window_hours()

    def parse_rule_terms(self, rules: str | None) -> List[str]:
        """Parse include/exclude rules into a list of terms."""
        if not rules:
            return []
        return [term.strip() for term in re.split(r"[,\n]+", rules) if term.strip()]

    def extract_search_depth(self, terms: List[str]) -> Tuple[str | None, List[str]]:
        """Extract search depth override from terms."""
        depth = None
        filtered_terms: List[str] = []
        for term in terms:
            normalized = term.strip().lower().replace(" ", "")
            if normalized.startswith("search_depth=") or normalized.startswith("depth="):
                depth = normalized.split("=", 1)[1]
                continue
            if normalized.startswith("search_depth:") or normalized.startswith("depth:"):
                depth = normalized.split(":", 1)[1]
                continue
            filtered_terms.append(term)
        if depth:
            depth = depth.strip().lower()
        return depth, filtered_terms

    def resolve_search_depth(self, override: str | None) -> str:
        """Resolve final search depth."""
        depth = (
            override
            or self.options.search_depth
            or settings.tavily_search_depth
            or "advanced"
        ).strip().lower()
        return depth if depth in {"basic", "advanced", "fast", "ultra-fast"} else "advanced"

    def resolve_max_results(self) -> int:
        """Resolve final max results."""
        override = self.options.max_results
        if override is None:
            return TAVILY_RESULTS_PER_TOPIC
        try:
            value = int(override)
        except (TypeError, ValueError):
            return TAVILY_RESULTS_PER_TOPIC
        return max(0, min(value, 20))

    def resolve_topic(self) -> str | None:
        """Resolve Tavily topic."""
        if not self.options.topic:
            return None
        topic = self.options.topic.strip().lower()
        return topic if topic in {"general", "news", "finance"} else None

    def resolve_time_range(self) -> str | None:
        """Resolve Tavily time range."""
        if not self.options.time_range:
            return None
        time_range = self.options.time_range.strip().lower()
        return time_range if time_range in {"day", "week", "month", "year", "d", "w", "m", "y"} else None

    def resolve_date(self, value: str | None) -> str | None:
        """Validate and return date string (YYYY-MM-DD)."""
        if not value:
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
        return value

    def resolve_include_raw_content(self) -> bool:
        """Resolve whether to include raw content in markdown."""
        if self.options.include_raw_content is None:
            return True
        return bool(self.options.include_raw_content)

    def resolve_include_answer(self) -> bool:
        """Resolve whether to include Tavily answers."""
        if self.options.include_answer is None:
            return False
        return bool(self.options.include_answer)

    def resolve_fetch_window_hours(self) -> int:
        """Resolve how far back to keep results without published dates."""
        if self.options.fetch_window_hours is None:
            return 48
        try:
            value = int(self.options.fetch_window_hours)
        except (TypeError, ValueError):
            return 48
        return value if value >= 0 else 48

    def build_query(self, topic: Topic, include_terms: List[str]) -> str:
        """Build a Tavily query string for a topic."""
        parts: List[str] = [topic.name]
        if topic.description:
            parts.append(topic.description)
        parts.extend(include_terms)
        return " ".join(part.strip() for part in parts if part and part.strip())

    def create_connector_query(
        self,
        topic: Topic,
        query: str,
        search_depth: str,
        max_results: int,
        include_terms: List[str],
        exclude_terms: List[str],
    ) -> ConnectorQuery:
        """Persist a connector query for traceability."""
        options = {
            "search_depth": search_depth,
            "max_results": max_results,
            "topic": self.resolve_topic(),
            "time_range": self.resolve_time_range(),
            "start_date": self.resolve_date(self.options.start_date),
            "end_date": self.resolve_date(self.options.end_date),
            "include_raw_content": self.resolve_include_raw_content(),
            "include_answer": self.resolve_include_answer(),
            "fetch_window_hours": self.fetch_window_hours,
            "include_terms": include_terms,
            "exclude_terms": exclude_terms,
        }
        connector_query = ConnectorQuery(
            connector_type=ConnectorType.TAVILY,
            topic_id=topic.id,
            query=query,
            options_json=options,
        )
        self.db.add(connector_query)
        self.db.flush()
        return connector_query

    def filter_results(
        self,
        results: List[Dict[str, Any]],
        include_terms: List[str],
        exclude_terms: List[str],
    ) -> List[Dict[str, Any]]:
        """Filter Tavily results using include/exclude terms."""
        filtered: List[Dict[str, Any]] = []
        include_terms_lower = [term.lower() for term in include_terms]
        exclude_terms_lower = [term.lower() for term in exclude_terms]
        for item in results:
            haystack = " ".join(
                str(item.get(key, "") or "") for key in ("title", "content", "url")
            ).lower()
            if any(term in haystack for term in exclude_terms_lower):
                continue
            if include_terms_lower and not any(
                term in haystack for term in include_terms_lower
            ):
                continue
            filtered.append(item)
        return filtered

    def search(self, query: str, max_results: int, search_depth: str) -> Dict[str, Any]:
        """Run a Tavily search query."""
        if not settings.tavily_api_key:
            raise Exception("Tavily API key not configured")

        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": self.resolve_include_answer(),
        }
        if self.resolve_include_raw_content():
            payload["include_raw_content"] = "markdown"
        topic = self.resolve_topic()
        if topic:
            payload["topic"] = topic
        time_range = self.resolve_time_range()
        if time_range:
            payload["time_range"] = time_range
        start_date = self.resolve_date(self.options.start_date)
        if start_date:
            payload["start_date"] = start_date
        end_date = self.resolve_date(self.options.end_date)
        if end_date:
            payload["end_date"] = end_date

        response = requests.post(TAVILY_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def parse_published_at(self, item: Dict[str, Any]):
        """Parse published date if provided by Tavily results."""
        value = item.get("published_date") or item.get("published_at") or item.get("date")
        if not value:
            return None
        try:
            published_at = date_parser.parse(value)
            if published_at.tzinfo is not None:
                published_at = published_at.replace(tzinfo=None)
            return published_at
        except Exception:
            return None

    def is_within_window(self, published_at: datetime | None) -> bool:
        """Check if item is within fetch window."""
        if not published_at:
            return True
        cutoff = datetime.utcnow() - timedelta(hours=self.fetch_window_hours)
        return published_at >= cutoff

    def get_existing_item(self, url: str, content_hash: str):
        """Find an existing content item matching this result."""
        existing = self.db.query(ContentItem).filter(ContentItem.url == url).first()
        if existing:
            return existing
        if content_hash:
            cutoff = datetime.utcnow() - timedelta(hours=self.fetch_window_hours)
            existing = (
                self.db.query(ContentItem)
                .filter(
                    ContentItem.hash == content_hash,
                    ContentItem.fetched_at >= cutoff,
                )
                .first()
            )
            if existing:
                return existing
        return None

    def create_content_item(self, item: Dict[str, Any], connector_query_id: int):
        """Create a ContentItem from a Tavily result."""
        url = (item.get("url") or "").strip()
        if not url:
            return None, False, "missing_url"

        title = (item.get("title") or "").strip() or url
        raw_text = item.get("raw_content") or item.get("content")
        published_at = self.parse_published_at(item)

        if not self.is_within_window(published_at):
            return None, False, "outside_window"

        parsed = urlparse(url)
        author = parsed.netloc.lstrip("www.") if parsed.netloc else None

        external_id = (
            url
            if len(url) <= 512
            else hashlib.sha256(url.encode("utf-8")).hexdigest()
        )
        hash_str = f"{title}:{url}".encode("utf-8")
        content_hash = hashlib.sha256(hash_str).hexdigest()

        existing = self.get_existing_item(url, content_hash)
        if existing:
            return existing, False, None

        content_item = ContentItem(
            connector_query_id=connector_query_id,
            connector_type=ConnectorType.TAVILY,
            external_id=external_id,
            url=url,
            title=title,
            author=author,
            published_at=published_at,
            raw_text=raw_text,
            raw_json=item,
            hash=content_hash,
        )
        self.db.add(content_item)
        self.db.flush()
        return content_item, True, None

    def ensure_topic_assignment(
        self, content_item: ContentItem, topic: Topic, score: float | None
    ) -> bool:
        """Ensure the content item is assigned to the topic."""
        existing = (
            self.db.query(TopicAssignment)
            .filter(
                TopicAssignment.content_item_id == content_item.id,
                TopicAssignment.topic_id == topic.id,
            )
            .first()
        )
        if existing:
            return False

        assignment = TopicAssignment(
            content_item_id=content_item.id,
            topic_id=topic.id,
            score=float(score or 0.0),
            rationale_short="Tavily search match",
        )
        self.db.add(assignment)
        return True

    async def ingest_topics(self) -> Dict[str, Any]:
        """Run Tavily search for all enabled topics."""
        stats: Dict[str, Any] = {
            "topics_processed": 0,
            "topics_failed": 0,
            "total_results": 0,
            "items_new": 0,
            "items_existing": 0,
            "items_skipped": 0,
            "assignments_created": 0,
            "errors": [],
            "topic_details": [],
        }

        topics = self.db.query(Topic).filter(Topic.enabled == True).all()

        for topic in topics:
            topic_stats: Dict[str, Any] = {
                "topic_id": topic.id,
                "topic_name": topic.name,
                "status": "success",
                "items_new": 0,
                "items_existing": 0,
                "items_skipped": 0,
                "assignments_created": 0,
            }

            try:
                include_terms = self.parse_rule_terms(topic.include_rules)
                exclude_terms = self.parse_rule_terms(topic.exclude_rules)
                depth_override, include_terms = self.extract_search_depth(include_terms)
                exclude_depth, exclude_terms = self.extract_search_depth(exclude_terms)
                search_depth = self.resolve_search_depth(depth_override or exclude_depth)
                max_results = self.resolve_max_results()

                query = self.build_query(topic, include_terms)
                connector_query = self.create_connector_query(
                    topic=topic,
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results,
                    include_terms=include_terms,
                    exclude_terms=exclude_terms,
                )
                response = self.search(query, max_results, search_depth)
                results = response.get("results", [])
                filtered = self.filter_results(results, include_terms, exclude_terms)
                filtered = filtered[:max_results]

                for result in filtered:
                    content_item, created, skip_reason = self.create_content_item(
                        result, connector_query.id
                    )
                    if skip_reason:
                        topic_stats["items_skipped"] += 1
                        stats["items_skipped"] += 1
                        continue

                    if created:
                        topic_stats["items_new"] += 1
                        stats["items_new"] += 1
                    else:
                        topic_stats["items_existing"] += 1
                        stats["items_existing"] += 1

                    if content_item and self.ensure_topic_assignment(
                        content_item, topic, result.get("score")
                    ):
                        topic_stats["assignments_created"] += 1
                        stats["assignments_created"] += 1

                topic_stats["query"] = query
                topic_stats["search_depth"] = search_depth
                topic_stats["max_results"] = max_results
                topic_stats["topic"] = self.resolve_topic()
                topic_stats["time_range"] = self.resolve_time_range()
                topic_stats["include_raw_content"] = self.resolve_include_raw_content()
                topic_stats["include_answer"] = self.resolve_include_answer()
                topic_stats["fetch_window_hours"] = self.fetch_window_hours
                topic_stats["include_terms"] = include_terms
                topic_stats["exclude_terms"] = exclude_terms
                topic_stats["results_count"] = len(filtered)
                topic_stats["connector_query_id"] = connector_query.id

                stats["topics_processed"] += 1
                stats["total_results"] += len(filtered)
                self.db.commit()

            except Exception as e:
                self.db.rollback()
                error_msg = f"Error processing topic {topic.name}: {str(e)}"
                stats["topics_failed"] += 1
                stats["errors"].append(error_msg)
                topic_stats["status"] = "failed"
                topic_stats["error"] = str(e)

            stats["topic_details"].append(topic_stats)

        stats["tavily_options"] = {
            "search_depth": self.resolve_search_depth(None),
            "max_results": self.resolve_max_results(),
            "topic": self.resolve_topic(),
            "time_range": self.resolve_time_range(),
            "start_date": self.resolve_date(self.options.start_date),
            "end_date": self.resolve_date(self.options.end_date),
            "include_raw_content": self.resolve_include_raw_content(),
            "include_answer": self.resolve_include_answer(),
            "fetch_window_hours": self.fetch_window_hours,
        }
        return stats
