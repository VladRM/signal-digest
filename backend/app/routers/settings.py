"""Settings API router."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.app_settings import AppSettings as AppSettingsModel
from app.schemas.settings import AppSettings

router = APIRouter()


@router.get("/settings", response_model=AppSettings)
def get_settings(db: Session = Depends(get_db)):
    """Return persisted application settings or defaults."""
    record = db.query(AppSettingsModel).first()
    if not record:
        return AppSettings()
    try:
        return AppSettings.model_validate(record.settings_json or {})
    except ValidationError:
        return AppSettings()


@router.put("/settings", response_model=AppSettings)
def update_settings(payload: AppSettings, db: Session = Depends(get_db)):
    """Upsert application settings."""
    try:
        record = db.query(AppSettingsModel).first()
        if record is None:
            record = AppSettingsModel(id=1, settings_json=payload.model_dump())
            db.add(record)
        else:
            record.settings_json = payload.model_dump()
        record.updated_at = datetime.utcnow()
        db.commit()
        return payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {exc}")
