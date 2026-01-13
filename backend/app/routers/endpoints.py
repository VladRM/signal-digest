"""Endpoints API router."""
from urllib.parse import urlparse
import feedparser
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.endpoint import Endpoint, ConnectorType
from app.schemas.endpoint import Endpoint as EndpointSchema, EndpointCreate, EndpointUpdate

router = APIRouter()


def validate_rss_target(target: str) -> None:
    """Basic RSS URL validation."""
    parsed = urlparse((target or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(
            status_code=400,
            detail="Invalid RSS URL. Use a full http(s) URL to an RSS/Atom feed.",
        )
    headers = {
        "User-Agent": "SignalDigest/1.0 (+https://github.com/)",
        "Accept": "application/rss+xml, application/atom+xml, text/xml;q=0.9, */*;q=0.8",
    }
    try:
        response = requests.get(parsed.geturl(), headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to fetch RSS URL: {exc}",
        )

    feed = feedparser.parse(response.content)
    has_feed = bool(feed.feed)
    has_entries = bool(feed.entries)
    if (feed.bozo and not has_entries and not has_feed) or (not has_entries and not has_feed):
        detail = "URL did not return a valid RSS/Atom feed."
        if feed.bozo and hasattr(feed, "bozo_exception"):
            detail = f"{detail} Parser error: {feed.bozo_exception}"
        raise HTTPException(status_code=400, detail=detail)


@router.get("", response_model=list[EndpointSchema])
def list_endpoints(
    connector_type: ConnectorType | None = Query(None, alias="connector_type"),
    db: Session = Depends(get_db),
):
    """List all endpoints, optionally filtered by connector."""
    query = db.query(Endpoint).filter(Endpoint.connector_type != ConnectorType.TAVILY)
    if connector_type:
        query = query.filter(Endpoint.connector_type == connector_type)
    endpoints = query.all()
    return endpoints


@router.post("", response_model=EndpointSchema)
def create_endpoint(endpoint: EndpointCreate, db: Session = Depends(get_db)):
    """Create a new endpoint."""
    if endpoint.connector_type == ConnectorType.TAVILY:
        raise HTTPException(
            status_code=400,
            detail="Tavily endpoints are generated at runtime from topics.",
        )
    if endpoint.connector_type == ConnectorType.RSS:
        validate_rss_target(endpoint.target)
    db_endpoint = Endpoint(**endpoint.model_dump())
    db.add(db_endpoint)
    db.commit()
    db.refresh(db_endpoint)
    return db_endpoint


@router.get("/{endpoint_id}", response_model=EndpointSchema)
def get_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    """Get an endpoint by ID."""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint


@router.put("/{endpoint_id}", response_model=EndpointSchema)
def update_endpoint(
    endpoint_id: int, endpoint_update: EndpointUpdate, db: Session = Depends(get_db)
):
    """Update an endpoint."""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    update_data = endpoint_update.model_dump(exclude_unset=True)
    effective_type = endpoint_update.connector_type or endpoint.connector_type
    effective_target = endpoint_update.target or endpoint.target
    if effective_type == ConnectorType.TAVILY:
        raise HTTPException(
            status_code=400,
            detail="Tavily endpoints are generated at runtime from topics.",
        )
    if effective_type == ConnectorType.RSS:
        validate_rss_target(effective_target)
    for field, value in update_data.items():
        setattr(endpoint, field, value)

    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/{endpoint_id}")
def delete_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    """Delete an endpoint."""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    db.delete(endpoint)
    db.commit()
    return {"message": "Endpoint deleted successfully"}
