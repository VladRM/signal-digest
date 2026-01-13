"""Endpoint schemas."""
from pydantic import BaseModel, ConfigDict

from app.models.endpoint import ConnectorType


class EndpointBase(BaseModel):
    """Base endpoint schema."""

    connector_type: ConnectorType
    name: str
    target: str
    enabled: bool = True
    weight: int = 1
    notes: str | None = None


class EndpointCreate(EndpointBase):
    """Schema for creating an endpoint."""

    pass


class EndpointUpdate(BaseModel):
    """Schema for updating an endpoint."""

    connector_type: ConnectorType | None = None
    name: str | None = None
    target: str | None = None
    enabled: bool | None = None
    weight: int | None = None
    notes: str | None = None


class Endpoint(EndpointBase):
    """Schema for endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
