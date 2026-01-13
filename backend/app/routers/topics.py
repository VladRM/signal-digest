"""Topics API router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.topic import Topic
from app.schemas.topic import Topic as TopicSchema, TopicCreate, TopicUpdate

router = APIRouter()


@router.get("", response_model=list[TopicSchema])
def list_topics(db: Session = Depends(get_db)):
    """List all topics."""
    topics = db.query(Topic).all()
    return topics


@router.post("", response_model=TopicSchema)
def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    """Create a new topic."""
    db_topic = Topic(**topic.model_dump())
    db.add(db_topic)
    db.commit()
    db.refresh(db_topic)
    return db_topic


@router.get("/{topic_id}", response_model=TopicSchema)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    """Get a topic by ID."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.put("/{topic_id}", response_model=TopicSchema)
def update_topic(topic_id: int, topic_update: TopicUpdate, db: Session = Depends(get_db)):
    """Update a topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    update_data = topic_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(topic, field, value)

    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    """Delete a topic."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    db.delete(topic)
    db.commit()
    return {"message": "Topic deleted successfully"}
