"""Topic schemas."""
from pydantic import BaseModel, ConfigDict


class TopicBase(BaseModel):
    """Base topic schema."""

    name: str
    description: str | None = None
    include_rules: str | None = None
    exclude_rules: str | None = None
    priority: int = 0
    enabled: bool = True


class TopicCreate(TopicBase):
    """Schema for creating a topic."""

    pass


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""

    name: str | None = None
    description: str | None = None
    include_rules: str | None = None
    exclude_rules: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class Topic(TopicBase):
    """Schema for topic response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
