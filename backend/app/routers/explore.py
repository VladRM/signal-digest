"""API routes for content exploration."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.connector_query import ConnectorQuery
from app.models.content_item import ContentItem
from app.models.topic_assignment import TopicAssignment
from app.models.ai_extraction import AIExtraction
from app.schemas.ai import ContentItemWithDetails

router = APIRouter()


@router.get("/explore", response_model=List[ContentItemWithDetails])
async def explore_content(
    topic_id: Optional[int] = Query(default=None),
    from_date: Optional[str] = Query(default=None),
    to_date: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0),
    db: Session = Depends(get_db)
):
    """Explore content items with filters.

    Args:
        topic_id: Filter by topic ID
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        limit: Maximum items to return (max 100)
        offset: Offset for pagination
        db: Database session

    Returns:
        List of content items with details
    """
    query = db.query(ContentItem).join(AIExtraction)

    # Apply filters
    if topic_id:
        query = query.join(TopicAssignment).filter(
            TopicAssignment.topic_id == topic_id
        )

    if from_date:
        query = query.filter(
            ContentItem.published_at >= datetime.strptime(from_date, "%Y-%m-%d")
        )

    if to_date:
        query = query.filter(
            ContentItem.published_at <= datetime.strptime(to_date, "%Y-%m-%d")
        )

    # Load relationships
    query = query.options(
        joinedload(ContentItem.endpoint),
        joinedload(ContentItem.connector_query).joinedload(ConnectorQuery.topic),
        joinedload(ContentItem.ai_extractions),
        joinedload(ContentItem.topic_assignments).joinedload(TopicAssignment.topic)
    )

    # Pagination
    items = query.order_by(
        ContentItem.published_at.desc()
    ).offset(offset).limit(limit).all()

    # Format response
    return [_format_content_item(item) for item in items]


def _format_content_item(item: ContentItem) -> dict:
    """Format content item with all nested data.

    Args:
        item: ContentItem object

    Returns:
        Formatted dict
    """
    extraction = item.ai_extractions[0] if item.ai_extractions else None

    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "author": item.author,
        "published_at": item.published_at,
        "raw_text": item.raw_text,
        "connector_type": item.connector_type.value,
        "endpoint": (
            {
                "id": item.endpoint.id,
                "name": item.endpoint.name,
                "connector_type": item.endpoint.connector_type.value,
                "target": item.endpoint.target,
            }
            if item.endpoint
            else None
        ),
        "connector_query": (
            {
                "id": item.connector_query.id,
                "connector_type": item.connector_query.connector_type.value,
                "query": item.connector_query.query,
                "topic_id": item.connector_query.topic_id,
                "topic_name": (
                    item.connector_query.topic.name
                    if item.connector_query.topic
                    else None
                ),
            }
            if item.connector_query
            else None
        ),
        "extraction": extraction.extracted_json if extraction else {},
        "topics": [
            {
                "topic_id": ta.topic_id,
                "topic_name": ta.topic.name,
                "score": ta.score,
                "rationale_short": ta.rationale_short
            }
            for ta in item.topic_assignments
        ]
    }
