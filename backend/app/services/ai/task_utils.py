"""Utilities for AI task logging."""

from urllib.parse import urlparse

from app.models.content_item import ContentItem


def _truncate(text: str, limit: int = 90) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: max(0, limit - 3)].rstrip()}..."


def format_item_label(item: ContentItem) -> str:
    """Build a short, readable label for a content item."""
    endpoint = item.endpoint
    connector_type = (
        item.connector_type.value if item.connector_type else "unknown"
    )
    endpoint_name = endpoint.name if endpoint and endpoint.name else ""
    query_topic = ""
    if item.connector_query and item.connector_query.topic:
        query_topic = item.connector_query.topic.name or ""
    title = item.title or ""
    label = connector_type
    if endpoint_name:
        label = f"{label}/{endpoint_name}"
    elif query_topic:
        label = f"{label}/{query_topic}"
    if title:
        return f"{label}: {_truncate(title)}"
    url = item.url or ""
    host = urlparse(url).netloc
    if host:
        return f"{label}: {host}"
    return label
