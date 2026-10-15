from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.db.session import get_db
from app.schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for Render and monitoring."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        timestamp=datetime.now(),
    )