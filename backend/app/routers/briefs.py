"""API routes for briefs."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime

from app.database import get_db
from app.models.brief import Brief, BriefMode
from app.models.brief_item import BriefItem
from app.models.connector_query import ConnectorQuery
from app.models.content_item import ContentItem
from app.models.topic_assignment import TopicAssignment
from app.models.topic_brief import TopicBrief
from app.schemas.ai import BriefWithItems

router = APIRouter()


@router.get("/brief", response_model=BriefWithItems)
async def get_brief(
    date_str: str = Query(default=None, description="YYYY-MM-DD format", alias="date"),
    mode: str = Query(default="morning"),
    db: Session = Depends(get_db)
):
    """Get daily brief with full content details.

    Args:
        date_str: Date string in YYYY-MM-DD format (default: today)
        mode: Brief mode (default: "morning")
        db: Database session

    Returns:
        Brief with all items and details
    """
    # Parse date
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    # Get brief
    brief = db.query(Brief).filter(
        Brief.date == target_date,
        Brief.mode == BriefMode.MORNING
    ).first()

    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    # Load all relationships
    brief_items = db.query(BriefItem).filter(
        BriefItem.brief_id == brief.id
    ).options(
        joinedload(BriefItem.content_item).joinedload(ContentItem.endpoint),
        joinedload(BriefItem.content_item)
        .joinedload(ContentItem.connector_query)
        .joinedload(ConnectorQuery.topic),
        joinedload(BriefItem.content_item).joinedload(ContentItem.ai_extractions),
        joinedload(BriefItem.content_item).joinedload(ContentItem.topic_assignments).joinedload(TopicAssignment.topic)
    ).order_by(BriefItem.rank).all()

    # Load topic briefs
    topic_briefs = db.query(TopicBrief).filter(
        TopicBrief.brief_id == brief.id
    ).options(
        joinedload(TopicBrief.topic)
    ).all()

    # Format topic briefs
    topic_briefs_data = []
    for tb in topic_briefs:
        # Extract data from content_references JSONB
        content_refs_json = tb.content_references if isinstance(tb.content_references, dict) else {}

        topic_briefs_data.append({
            "id": tb.id,
            "topic_id": tb.topic_id,
            "topic_name": tb.topic.name,
            "summary_short": tb.summary_short,
            "summary_full": tb.summary_full,
            "content_references": content_refs_json.get("references", []),
            "key_themes": content_refs_json.get("key_themes", []),
            "significance": content_refs_json.get("significance", ""),
            "created_at": tb.created_at
        })

    # Format response
    return {
        "id": brief.id,
        "date": brief.date,
        "mode": brief.mode.value,
        "created_at": brief.created_at,
        "items": [_format_brief_item(item) for item in brief_items],
        "topic_briefs": topic_briefs_data
    }


def _format_brief_item(brief_item: BriefItem) -> dict:
    """Format brief item with all nested data.

    Args:
        brief_item: BriefItem object

    Returns:
        Formatted dict
    """
    item = brief_item.content_item
    extraction = item.ai_extractions[0] if item.ai_extractions else None

    return {
        "rank": brief_item.rank,
        "reason_included": brief_item.reason_included,
        "content_item": {
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "author": item.author,
            "published_at": item.published_at,
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
    }
