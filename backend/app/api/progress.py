from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from uuid import UUID

from app.db.session import get_db
from app.db.models import Learner, Response, ResponseKind, Progress, SkillStatus, XPEvent, Achievement, Session as SessionModel
from app.schemas import ProgressOut, ProgressSkill
from app.api.learners import get_current_learner

router = APIRouter()


SKILL_BY_LEVEL = {
    1: "arithmetic-integers",
    2: "expressions-like-terms",
    3: "distributive-inverse",
    4: "multi-step-equations",
    5: "transfer-inequalities",
}

LEVEL_INFO = [
    {"id": 1, "name": "Foundations"},
    {"id": 2, "name": "Expressions"},
    {"id": 3, "name": "Algebra Essentials"},
    {"id": 4, "name": "Equation Solver"},
    {"id": 5, "name": "Challenge Lab"},
]


@router.get("/progress", response_model=ProgressOut)
async def get_progress(learner: Learner = Depends(get_current_learner), db: Session = Depends(get_db)):
    """Get progress summary for the current learner."""
    # Total XP
    total_xp = db.query(func.coalesce(func.sum(XPEvent.xp_amount), 0)).filter(XPEvent.learner_id == learner.id).scalar() or 0

    # Practice sets completed (each practice phase has 3 questions)
    practice_responses = db.query(func.count(Response.id)).filter(
        Response.learner_id == learner.id,
        Response.kind == ResponseKind.PRACTICE
    ).scalar() or 0
    practice_sets = practice_responses // 3

    # Latest retest
    latest_retest_responses = db.query(Response).filter(
        Response.learner_id == learner.id,
        Response.kind == ResponseKind.RETEST
    ).order_by(Response.created_at.desc()).limit(3).all()

    latest_retest = None
    if latest_retest_responses:
        retest_correct = sum(1 for r in latest_retest_responses if r.is_correct)
        latest_retest = {
            "score": retest_correct,
            "total": len(latest_retest_responses),
            "date": latest_retest_responses[0].created_at.isoformat() if latest_retest_responses else None,
        }

    # Skills progress
    skills = []
    for level_id, skill in SKILL_BY_LEVEL.items():
        progress = db.query(Progress).filter(Progress.learner_id == learner.id, Progress.skill == skill).first()
        if progress:
            skills.append(ProgressSkill(
                skill=skill,
                level=level_id,
                status=progress.status,
                last_retest_score=progress.last_retest_score,
                last_retest_total=progress.last_retest_total,
                retest_count=progress.retest_count,
            ))
        else:
            skills.append(ProgressSkill(
                skill=skill,
                level=level_id,
                status=SkillStatus.NOT_ASSESSED,
                last_retest_score=None,
                last_retest_total=None,
                retest_count=0,
            ))

    # Achievements
    achievements_db = db.query(Achievement).filter(Achievement.learner_id == learner.id).all()
    achievement_labels = {
        "first-practice": "First practice completed",
        "first-retest": "First fresh retest completed",
    }
    achievements = [achievement_labels.get(a.achievement_id, a.achievement_id) for a in achievements_db]

    # History (recent sessions)
    sessions = db.query(SessionModel).filter(SessionModel.learner_id == learner.id).order_by(SessionModel.started_at.desc()).limit(12).all()
    history = []
    for s in sessions:
        responses = db.query(Response).filter(Response.session_id == s.id).all()
        if responses:
            score = sum(1 for r in responses if r.is_correct)
            total = len(responses)
            history.append({
                "type": s.phase.value,
                "level": s.level,
                "score": score,
                "total": total,
                "date": s.started_at.isoformat(),
            })

    return ProgressOut(
        total_xp=total_xp,
        practice_sets_completed=practice_sets,
        latest_retest=latest_retest,
        skills=skills,
        achievements=achievements,
        history=history,
    )