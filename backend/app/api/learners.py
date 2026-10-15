from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
import hashlib
import secrets
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Learner, Session as SessionModel, SessionPhase, SessionStatus
from app.schemas import (
    LearnerCreate, LearnerOut, HealthOut, LevelsOut, LevelSummary, SkillStatus,
    SessionCreate, SessionOut, QuestionOut, AnswerIn, AnswerOut, FeedbackOut,
    OptionOut, ErrorOut, InsightsOut, ProgressOut, MisconceptionMapOut,
)
from app.engine.state_machine import DiagnosticEngine
from app.content.loader import get_content_loader
from app.engine.misconceptions import get_misconception, confidence_wording

router = APIRouter()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_current_learner(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> Learner:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization[7:]  # Remove "Bearer "
    token_hash = hash_token(token)
    learner = db.query(Learner).filter(Learner.token_hash == token_hash).first()
    if not learner:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    learner.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return learner


@router.post("/learners", response_model=LearnerOut, status_code=status.HTTP_201_CREATED)
async def create_learner(learner_in: Optional[LearnerCreate] = None, db: Session = Depends(get_db)):
    """Create an anonymous learner and return a token (only shown once)."""
    token = secrets.token_hex(32)  # 64 hex chars
    token_hash = hash_token(token)
    learner = Learner(token_hash=token_hash)
    db.add(learner)
    db.commit()
    db.refresh(learner)
    return LearnerOut(token=token, token_hash=token_hash)


@router.delete("/learners/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_learner(learner: Learner = Depends(get_current_learner), db: Session = Depends(get_db)):
    """Delete all data for the current learner."""
    db.delete(learner)
    db.commit()
    return None


@router.get("/me/summary")
async def get_summary(learner: Learner = Depends(get_current_learner), db: Session = Depends(get_db)):
    """Get dashboard summary for the current learner."""
    from app.db.models import Response, ResponseKind, Progress, XPEvent, Achievement

    total_xp = db.query(func.coalesce(func.sum(XPEvent.xp_amount), 0)).filter(XPEvent.learner_id == learner.id).scalar() or 0
    practice_count = db.query(func.count(Response.id)).filter(
        Response.learner_id == learner.id, Response.kind == ResponseKind.PRACTICE
    ).scalar() or 0

    # The latest retest is the most recent set of (up to) 3 retest answers
    latest_retest_responses = db.query(Response).filter(
        Response.learner_id == learner.id, Response.kind == ResponseKind.RETEST
    ).order_by(Response.created_at.desc()).limit(3).all()

    # Get active level (most recent session in progress)
    active_session = db.query(SessionModel).filter(
        SessionModel.learner_id == learner.id,
        SessionModel.status == SessionStatus.IN_PROGRESS
    ).order_by(SessionModel.started_at.desc()).first()

    active_level = active_session.level if active_session else 3

    return {
        "total_xp": total_xp,
        "practice_sets_completed": practice_count // 3,  # 3 questions per practice set
        "latest_retest": {
            "score": sum(1 for r in latest_retest_responses if r.is_correct),
            "total": len(latest_retest_responses),
            "date": latest_retest_responses[0].created_at.isoformat(),
        } if latest_retest_responses else None,
        "active_level": active_level,
    }